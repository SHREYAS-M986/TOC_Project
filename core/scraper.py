"""Web page fetching, SSRF protection, and HTML text cleaning module."""

import ipaddress
import re
import socket
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

MAX_FETCH_BYTES = 2 * 1024 * 1024  # 2 MB limit
MAX_RETURN_CHARS = 100_000         # 100k char limit for text extraction


class ScraperSecurityError(Exception):
    """Raised when URL fails SSRF or protocol security checks."""
    pass


class ScraperFetchError(Exception):
    """Raised when HTTP request fails, times out, or exceeds size."""
    pass


def is_ip_allowed(ip_str: str) -> bool:
    """Check if an IP address is public and safe to fetch (blocks SSRF targets)."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
        return True
    except ValueError:
        return False


def validate_url_security(url: str) -> str:
    """Validate URL scheme and resolve DNS to ensure no private/internal IPs are accessed."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ScraperSecurityError(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ScraperSecurityError("Invalid URL: missing hostname.")

    # Reject known local identifiers directly
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise ScraperSecurityError("Access to localhost / loopback addresses is forbidden.")

    # Resolve hostname to all associated IPs and verify each
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ScraperSecurityError(f"Failed to resolve hostname '{hostname}': {e}")

    for addr in addr_infos:
        ip_str = addr[4][0]
        if not is_ip_allowed(ip_str):
            raise ScraperSecurityError(
                f"Hostname '{hostname}' resolves to disallowed/internal IP address '{ip_str}'."
            )

    return url


def clean_html(html_content: str) -> Tuple[str, str]:
    """Clean HTML content, preserving links, mailto targets, and structural line breaks.

    Returns:
        (cleaned_text, page_title)
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract page title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Remove non-content elements
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "header_nav", "canvas"]):
        tag.decompose()

    # Preserve link targets and mailto targets in text
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        if href.lower().startswith("mailto:"):
            # mailto:user@domain.com?subject=... -> plain email
            email_part = href[7:].split("?")[0].strip()
            if email_part:
                a.append(f" ({email_part})")
        else:
            a.append(f" ({href})")

    # Add line breaks around block elements
    block_tags = ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "section", "article", "br"]
    for tag_name in block_tags:
        for tag in soup.find_all(tag_name):
            tag.insert_before("\n")
            tag.insert_after("\n")

    # Extract text with newline separator
    raw_text = soup.get_text()

    # Clean whitespace while preserving line breaks
    cleaned_lines = []
    for line in raw_text.splitlines():
        # Collapse multiple spaces/tabs into a single space
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        cleaned_lines.append(cleaned_line)

    # Reassemble and collapse 3+ consecutive newlines to 2
    full_text = "\n".join(cleaned_lines)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()

    return full_text, title


def fetch_and_clean_page(
    url: str,
    timeout: int = 15,
    max_bytes: int = MAX_FETCH_BYTES,
    max_return_chars: int = MAX_RETURN_CHARS
) -> Dict[str, Any]:
    """Securely fetch a web page and clean its text.

    Args:
        url: Web URL to fetch.
        timeout: Network timeout in seconds.
        max_bytes: Maximum allowed response payload size in bytes.
        max_return_chars: Maximum characters to return in cleaned text.

    Returns:
        Dict with keys: url, title, text, char_count, line_count.
    """
    validate_url_security(url)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        with requests.get(url, headers=headers, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()

            # Check Content-Type if present
            content_type = resp.headers.get("Content-Type", "")
            if content_type and "text" not in content_type and "html" not in content_type and "xml" not in content_type:
                raise ScraperFetchError(f"Unsupported content type: {content_type}")

            # Read up to max_bytes
            content_chunks = []
            bytes_read = 0
            for chunk in resp.iter_content(chunk_size=8192, decode_unicode=False):
                bytes_read += len(chunk)
                if bytes_read > max_bytes:
                    raise ScraperFetchError(f"Page response exceeds maximum size of {max_bytes} bytes.")
                content_chunks.append(chunk)

            raw_bytes = b"".join(content_chunks)
            encoding = resp.encoding or "utf-8"
            html_content = raw_bytes.decode(encoding, errors="replace")

    except requests.Timeout:
        raise ScraperFetchError(f"Request to '{url}' timed out after {timeout} seconds.")
    except requests.RequestException as e:
        raise ScraperFetchError(f"Failed to fetch '{url}': {e}")

    cleaned_text, title = clean_html(html_content)

    if len(cleaned_text) > max_return_chars:
        cleaned_text = cleaned_text[:max_return_chars]

    lines = cleaned_text.splitlines()

    return {
        "url": url,
        "title": title or url,
        "text": cleaned_text,
        "char_count": len(cleaned_text),
        "line_count": len(lines)
    }
