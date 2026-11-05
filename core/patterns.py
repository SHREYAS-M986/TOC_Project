"""Pattern Registry for Web Content Analyzer (RE vs DFA).

Defines regular expressions for tokenizing and extracting structured patterns
from web text: Email, Indian Mobile Numbers, Dates, URLs, Hashtags, 24-hr Time,
and '-ing' words.
"""

import re
from typing import Any

# ==============================================================================
# PATTERN SPECIFICATIONS AND REGULAR EXPRESSIONS
# ==============================================================================

# 1. EMAIL PATTERN
# Regex: [A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}
# Explanation:
# - [A-Za-z0-9._%+-]+ : Matches the local part (username) composed of alphanumeric
#   characters or standard email special characters (. _ % + -).
# - @                 : Literal '@' separator between local part and domain.
# - [A-Za-z0-9.-]+    : Matches domain name labels separated by dots or hyphens.
# - \.                : Literal dot separating domain and top-level domain (TLD).
# - [A-Za-z]{2,}      : Matches the TLD consisting of at least 2 alphabetic characters.
EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

# 2. INDIAN MOBILE NUMBER PATTERN
# Regex: (?<!\d)(?:(?:\+91|91|0)[\s-]?)?[6-9]\d{9}(?!\d)
# Explanation:
# - (?<!\d)           : Negative lookbehind asserting the preceding character is not
#                       a digit (prevents partial match in longer number sequences).
# - (?:(?:\+91|91|0)[\s-]?)? : Optional country/trunk code: '+91', '91', or '0',
#                       optionally followed by a single whitespace or hyphen.
# - [6-9]             : Indian mobile numbers mandate starting with digit 6, 7, 8, or 9.
# - \d{9}             : Followed by exactly 9 more decimal digits (total 10 digits).
# - (?!\d)            : Negative lookahead asserting the following character is not
#                       a digit (rejects 11+ digit numbers).
MOBILE_REGEX = r"(?<!\d)(?:(?:\+91|91|0)[\s-]?)?[6-9]\d{9}(?!\d)"

# 3. DATE PATTERN (DD-MM-YYYY)
# Regex: \b(0[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-(19|20)\d{2}\b
# Explanation:
# - \b                : Word boundary ensuring the date stands alone.
# - (0[1-9]|[12]\d|3[01]) : Day group strictly matching 01-09, 10-29, 30, or 31.
# - -                 : Literal hyphen separator.
# - (0[1-9]|1[0-2])   : Month group strictly matching 01-09, 10, 11, or 12.
# - -                 : Literal hyphen separator.
# - (19|20)\d{2}      : Year group restricted to centuries 1900-2099.
# - \b                : Word boundary.
DATE_REGEX = r"\b(0[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-(19|20)\d{2}\b"

# 4. URL PATTERN
# Regex: https?://[^\s<>\x22\'\)]*[^\s<>\x22\'\).,;:?!]
# Refinement from base https?://[^\s<>"')]+:
# Uses [^\s<>\x22\'\)]* followed by terminal [^\s<>\x22\'\).,;:?!] to cleanly exclude
# sentence-ending trailing punctuation (such as '.', ',', ';', ':', '?', '!') and enclosing brackets,
# ensuring valid, clean URLs when embedded in prose or parenthetical links " (href)".
# Explanation:
# - https?://                  : Protocol 'http://' or 'https://'.
# - [^\s<>\x22\'\)]*           : Zero or more valid URL characters (excluding whitespace and delimiters).
# - [^\s<>\x22\'\).,;:?!]      : Terminal URL character excluding sentence punctuation.
URL_REGEX = r"https?://[^\s<>\x22\'\)]*[^\s<>\x22\'\).,;:?!]"

# 5. HASHTAG PATTERN
# Regex: (?<![\w#])#[A-Za-z][A-Za-z0-9_]*
# Refinement from base (?<!\w)#[A-Za-z][A-Za-z0-9_]*:
# Uses negative lookbehind (?<![\w#]) to prevent matching consecutive hashes
# such as Markdown headings (e.g. ## Heading) or double hashes (##tag).
# Explanation:
# - (?<![\w#])       : Negative lookbehind asserting not preceded by a word char or another '#'.
# - #                 : Literal hash symbol '#'.
# - [A-Za-z]          : Initial tag character must be an alphabetic letter (rules out #123).
# - [A-Za-z0-9_]*     : Subsequent characters can be alphanumeric or underscores.
HASHTAG_REGEX = r"(?<![\w#])#[A-Za-z][A-Za-z0-9_]*"

# 6. TIME PATTERN (HH:MM 24-HOUR)
# Regex: \b([01]\d|2[0-3]):[0-5]\d\b
# Explanation:
# - \b                : Word boundary.
# - ([01]\d|2[0-3])   : Hours group matching 00-19 or 20-23 (valid 24-hour range).
# - :                 : Literal colon delimiter.
# - [0-5]\d           : Minutes group matching 00-59.
# - \b                : Word boundary.
TIME_REGEX = r"\b([01]\d|2[0-3]):[0-5]\d\b"

# 7. ING-WORD PATTERN
# Regex: \b[A-Za-z]+ing\b
# Explanation:
# - \b                : Word boundary.
# - [A-Za-z]+         : At least one alphabetic character before 'ing' (ensures 'ing' alone
#                       with 0 preceding letters does not match, minimum 4 letters).
# - ing               : Literal suffix 'ing'.
# - \b                : Word boundary.
ING_WORD_REGEX = r"\b[A-Za-z]+ing\b"


# ==============================================================================
# PATTERN REGISTRY DICTIONARY
# ==============================================================================

PATTERNS: dict[str, dict[str, Any]] = {
    "email": {
        "key": "email",
        "label": "Email Address",
        "regex": EMAIL_REGEX,
        "flags": 0,
        "description": "Standard email address matching local username, '@', domain, and a 2+ letter TLD.",
        "example": "student.support@university.edu",
    },
    "mobile": {
        "key": "mobile",
        "label": "Indian Mobile Number",
        "regex": MOBILE_REGEX,
        "flags": 0,
        "description": "Indian 10-digit mobile number starting with 6-9, optional +91/91/0 prefix, space/hyphen separator.",
        "example": "+91 9876543210",
    },
    "date": {
        "key": "date",
        "label": "Date (DD-MM-YYYY)",
        "regex": DATE_REGEX,
        "flags": 0,
        "description": "Date in DD-MM-YYYY format with valid ranges (DD: 01-31, MM: 01-12, YYYY: 1900-2099).",
        "example": "15-08-1947",
    },
    "url": {
        "key": "url",
        "label": "Web URL",
        "regex": URL_REGEX,
        "flags": 0,
        "description": "HTTP or HTTPS web link with trailing punctuation stripped cleanly.",
        "example": "https://www.example.org/admissions/index.html",
    },
    "hashtag": {
        "key": "hashtag",
        "label": "Hashtag",
        "regex": HASHTAG_REGEX,
        "flags": 0,
        "description": "Social/topic hashtag starting with '#' and a letter, followed by letters, digits, or underscores.",
        "example": "#TheoryOfComputation",
    },
    "time": {
        "key": "time",
        "label": "24-Hour Time (HH:MM)",
        "regex": TIME_REGEX,
        "flags": 0,
        "description": "24-hour clock time in HH:MM format (HH: 00-23, MM: 00-59).",
        "example": "14:30",
    },
    "ing_word": {
        "key": "ing_word",
        "label": "Words ending in 'ing'",
        "regex": ING_WORD_REGEX,
        "flags": re.IGNORECASE,
        "description": "English words ending in suffix 'ing' with at least 1 preceding letter (case-insensitive).",
        "example": "engineering",
    },
}


def get_pattern(key: str) -> dict[str, Any]:
    """Retrieve pattern metadata by key."""
    if key not in PATTERNS:
        raise KeyError(f"Pattern '{key}' not found in registry.")
    return PATTERNS[key]


def get_all_patterns() -> dict[str, dict[str, Any]]:
    """Return dictionary of all registered patterns suitable for JSON API response."""
    result = {}
    for key, p in PATTERNS.items():
        result[key] = {
            "key": p["key"],
            "label": p["label"],
            "regex": p["regex"],
            "flags": int(p["flags"]),
            "description": p["description"],
            "example": p["example"],
        }
    return result


def get_compiled_pattern(key: str) -> re.Pattern:
    """Return compiled re.Pattern instance for a given key."""
    p = get_pattern(key)
    return re.compile(p["regex"], p["flags"])
