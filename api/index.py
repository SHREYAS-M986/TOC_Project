"""Flask Application Entry for Web Content Analyzer (RE vs DFA).

Serves REST API endpoints for pattern extraction, web page scraping with SSRF
protection, snapshot access, and pattern summary comparison.
Designed to run locally or as a Vercel Serverless Function.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.patterns import PATTERNS, get_all_patterns
from core.re_engine import extract
from core.scraper import (
    MAX_FETCH_BYTES,
    MAX_RETURN_CHARS,
    ScraperFetchError,
    ScraperSecurityError,
    fetch_and_clean_page,
)

app = Flask(__name__, static_folder=str(PROJECT_ROOT / "public"), static_url_path="")
CORS(app)

DATA_PAGES_DIR = PROJECT_ROOT / "data" / "pages"
SOURCES_FILE = DATA_PAGES_DIR / "sources.json"


def load_sources_metadata() -> list:
    """Load metadata list from data/pages/sources.json."""
    if not SOURCES_FILE.exists():
        return []
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Error reading sources.json: {e}")
        return []


# ==============================================================================
# ERROR HANDLERS (Consistent JSON {error, detail})
# ==============================================================================

@app.errorhandler(400)
def handle_bad_request(e):
    return jsonify({"error": "Bad Request", "detail": str(e.description if hasattr(e, "description") else e)}), 400


@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": "Not Found", "detail": str(e.description if hasattr(e, "description") else e)}), 404


@app.errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({"error": "Method Not Allowed", "detail": "The HTTP method is not allowed for the requested URL."}), 405


@app.errorhandler(500)
def handle_internal_error(e):
    return jsonify({"error": "Internal Server Error", "detail": "An unexpected server error occurred."}), 500


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.route("/", methods=["GET"])
def root():
    """Root route: returns API status or static index if present."""
    index_file = PROJECT_ROOT / "public" / "index.html"
    if index_file.exists():
        return app.send_static_file("index.html")
    return jsonify({
        "project": "Web Content Analyzer: RE vs DFA",
        "stage": 1,
        "api_docs": "/api/health",
        "status": "running"
    })


@app.route("/api/health", methods=["GET"])
def health():
    """GET /api/health -> Service health status."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "service": "Web Content Analyzer Backend"
    }), 200


@app.route("/api/pages", methods=["GET"])
def get_pages():
    """GET /api/pages -> List of snapshot page sources."""
    sources = load_sources_metadata()
    return jsonify(sources), 200


@app.route("/api/pages/<page_id>", methods=["GET"])
def get_page_detail(page_id: str):
    """GET /api/pages/<id> -> Snapshot metadata + full cleaned text."""
    sources = load_sources_metadata()
    match_meta = next((item for item in sources if item.get("id") == page_id), None)

    page_file = DATA_PAGES_DIR / f"{page_id}.txt"
    if not page_file.exists():
        return jsonify({
            "error": "Not Found",
            "detail": f"Snapshot text file for page ID '{page_id}' not found."
        }), 404

    try:
        text_content = page_file.read_text(encoding="utf-8")
    except Exception as e:
        return jsonify({
            "error": "Read Error",
            "detail": f"Failed reading snapshot file: {e}"
        }), 500

    response_data = dict(match_meta) if match_meta else {"id": page_id}
    response_data["text"] = text_content
    response_data["char_count"] = len(text_content)
    response_data["line_count"] = len(text_content.splitlines())

    return jsonify(response_data), 200


@app.route("/api/patterns", methods=["GET"])
def get_patterns():
    """GET /api/patterns -> Pattern registry metadata."""
    patterns = get_all_patterns()
    return jsonify(patterns), 200


@app.route("/api/analyze/re", methods=["POST"])
def analyze_re():
    """POST /api/analyze/re -> Analyze text using Python RE engine.

    Request Body (JSON):
        {
            "page_id": "page1" (optional),
            "text": "..." (optional),
            "url": "https://..." (optional),
            "patterns": ["email", "mobile", ...] (optional)
        }
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "detail": "Request body must be valid JSON."
        }), 400

    payload = request.get_json() or {}
    page_id = payload.get("page_id")
    raw_text = payload.get("text")
    url = payload.get("url")
    pattern_keys = payload.get("patterns")

    target_text = ""
    source_info = {}

    if page_id:
        page_file = DATA_PAGES_DIR / f"{page_id}.txt"
        if not page_file.exists():
            return jsonify({
                "error": "Not Found",
                "detail": f"Snapshot page '{page_id}' does not exist."
            }), 404
        target_text = page_file.read_text(encoding="utf-8")
        source_info = {"type": "snapshot", "page_id": page_id}

    elif raw_text is not None:
        target_text = str(raw_text)
        source_info = {"type": "direct_text", "char_count": len(target_text)}

    elif url:
        try:
            fetch_res = fetch_and_clean_page(
                url,
                timeout=10,
                max_bytes=MAX_FETCH_BYTES,
                max_return_chars=MAX_RETURN_CHARS
            )
            target_text = fetch_res["text"]
            source_info = {
                "type": "live_fetch",
                "url": url,
                "title": fetch_res["title"]
            }
        except ScraperSecurityError as se:
            return jsonify({"error": "Security Error", "detail": str(se)}), 400
        except ScraperFetchError as fe:
            return jsonify({"error": "Fetch Error", "detail": str(fe)}), 502
        except Exception as e:
            return jsonify({"error": "Fetch Error", "detail": str(e)}), 500

    else:
        return jsonify({
            "error": "Bad Request",
            "detail": "At least one of 'page_id', 'text', or 'url' must be provided."
        }), 400

    # Execute RE Extraction
    try:
        extraction_result = extract(target_text, pattern_keys=pattern_keys)
    except Exception as e:
        return jsonify({
            "error": "Extraction Error",
            "detail": f"RE engine extraction failed: {e}"
        }), 500

    return jsonify({
        "source": source_info,
        "char_count": len(target_text),
        "line_count": len(target_text.splitlines()),
        "results": extraction_result["results"],
        "patterns": extraction_result["patterns"],
        "total_matches": extraction_result["total_matches"],
        "elapsed_seconds": extraction_result["elapsed_seconds"],
        "elapsed_ms": extraction_result["elapsed_ms"]
    }), 200


@app.route("/api/fetch", methods=["POST"])
def live_fetch():
    """POST /api/fetch -> Live fetch of user URL with SSRF protection."""
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "detail": "Request body must be valid JSON."
        }), 400

    payload = request.get_json() or {}
    url = payload.get("url")

    if not url or not isinstance(url, str):
        return jsonify({
            "error": "Bad Request",
            "detail": "A valid 'url' string is required in the JSON payload."
        }), 400

    try:
        fetched = fetch_and_clean_page(
            url.strip(),
            timeout=10,
            max_bytes=MAX_FETCH_BYTES,
            max_return_chars=MAX_RETURN_CHARS
        )
        return jsonify(fetched), 200

    except ScraperSecurityError as se:
        return jsonify({"error": "Security Error", "detail": str(se)}), 400
    except ScraperFetchError as fe:
        return jsonify({"error": "Fetch Error", "detail": str(fe)}), 502
    except Exception as e:
        return jsonify({"error": "Internal Error", "detail": str(e)}), 500


@app.route("/api/summary", methods=["GET"])
def get_summary():
    """GET /api/summary -> Pattern counts across all 3 snapshots for cross-page comparison."""
    sources = load_sources_metadata()
    page_ids = ["page1", "page2", "page3"]

    pages_summary = {}
    pattern_keys = list(PATTERNS.keys())
    totals = {k: 0 for k in pattern_keys}

    for pid in page_ids:
        page_file = DATA_PAGES_DIR / f"{pid}.txt"
        meta = next((s for s in sources if s.get("id") == pid), {})
        if page_file.exists():
            text = page_file.read_text(encoding="utf-8")
            res = extract(text)
            counts = {k: v["count"] for k, v in res["results"].items()}
        else:
            counts = {k: 0 for k in pattern_keys}

        pages_summary[pid] = {
            "id": pid,
            "title": meta.get("title", f"Page {pid}"),
            "category": meta.get("category", "Unknown"),
            "url": meta.get("url", ""),
            "counts": counts,
            "total_matches": sum(counts.values())
        }

        for k, v in counts.items():
            totals[k] += v

    # Build comparison rows suitable for chart rendering
    comparison_table = []
    for k in pattern_keys:
        p_meta = PATTERNS[k]
        row = {
            "key": k,
            "label": p_meta["label"],
            "page1": pages_summary.get("page1", {}).get("counts", {}).get(k, 0),
            "page2": pages_summary.get("page2", {}).get("counts", {}).get(k, 0),
            "page3": pages_summary.get("page3", {}).get("counts", {}).get(k, 0),
            "total": totals[k]
        }
        comparison_table.append(row)

    return jsonify({
        "pages": pages_summary,
        "totals": totals,
        "patterns": comparison_table,
        "grand_total": sum(totals.values())
    }), 200


if __name__ == "__main__":
    # Local development server on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
