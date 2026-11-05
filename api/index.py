"""Flask Application Entry for Web Content Analyzer (RE vs DFA).

Serves REST API endpoints for pattern extraction, web page scraping with SSRF
protection, snapshot access, and pattern summary comparison.
Designed to run locally or as a Vercel Serverless Function.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.dfa_definition import get_dfa_definition
from core.dfa_engine import (
    benchmark_dfa,
    scan_text,
    trace,
)
from core.dfa_engine import (
    extract as dfa_extract,
)
from core.patterns import PATTERNS, get_all_patterns
from core.re_engine import benchmark as re_benchmark
from core.re_engine import extract, extract_single_pattern
from core.scraper import (
    MAX_FETCH_BYTES,
    MAX_RETURN_CHARS,
    ScraperFetchError,
    ScraperSecurityError,
    fetch_and_clean_page,
)
from core.utils import count_single_file_loc
from tests.test_data import TEST_CASES

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

@app.route("/favicon.ico", methods=["GET"])
def favicon():
    return "", 204


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
        "timestamp": datetime.now(UTC).isoformat(),
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


# ==============================================================================
# DFA & COMPARISON ENDPOINTS (Stage 2)
# ==============================================================================

@app.route("/api/dfa/definition", methods=["GET"])
def get_dfa_machine():
    """GET /api/dfa/definition -> DFA definition, alphabet classes, states, and transition table."""
    definition = get_dfa_definition()
    return jsonify(definition), 200


@app.route("/api/analyze/dfa", methods=["POST"])
def analyze_dfa():
    """POST /api/analyze/dfa -> Extract '-ing' words using hand-built DFA.

    Accepts: {page_id | text | url}
    Returns results in the same shape as RE engine.
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

    try:
        extraction_result = dfa_extract(target_text)
    except Exception as e:
        return jsonify({
            "error": "Extraction Error",
            "detail": f"DFA extraction failed: {e}"
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


@app.route("/api/dfa/trace", methods=["POST"])
def dfa_word_trace():
    """POST /api/dfa/trace -> Trace step-by-step state transitions for a single word."""
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "detail": "Request body must be valid JSON."
        }), 400

    payload = request.get_json() or {}
    word = payload.get("word")

    if word is None or not isinstance(word, str):
        return jsonify({
            "error": "Bad Request",
            "detail": "Field 'word' (string) is required in the request body."
        }), 400

    trace_result = trace(word)
    return jsonify(trace_result), 200


@app.route("/api/compare", methods=["POST"])
def compare_re_vs_dfa():
    """POST /api/compare -> Detailed comparison of RE vs DFA on '-ing' word pattern.

    Body: {page_id | text}
    Returns:
      - Match lists from both engines
      - Set diffs (only_in_re, only_in_dfa)
      - Equal flag (boolean)
      - Benchmark timing in microseconds (200-run average via perf_counter)
      - Lines of code (LOC) metrics for both implementations
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "detail": "Request body must be valid JSON."
        }), 400

    payload = request.get_json() or {}
    page_id = payload.get("page_id")
    raw_text = payload.get("text")

    target_text = ""
    source_name = ""

    if page_id:
        page_file = DATA_PAGES_DIR / f"{page_id}.txt"
        if not page_file.exists():
            return jsonify({
                "error": "Not Found",
                "detail": f"Snapshot page '{page_id}' does not exist."
            }), 404
        target_text = page_file.read_text(encoding="utf-8")
        source_name = f"Snapshot: {page_id}"
    elif raw_text is not None:
        target_text = str(raw_text)
        source_name = f"Direct text ({len(target_text)} chars)"
    else:
        return jsonify({
            "error": "Bad Request",
            "detail": "Either 'page_id' or 'text' must be provided."
        }), 400

    # 1. Extraction from RE
    re_result = extract_single_pattern(target_text, "ing_word")
    re_matches = re_result["matches"]

    # 2. Extraction from DFA
    dfa_matches = scan_text(target_text)

    # 3. Diff Analysis
    # Compare by identity (text, start, end, line, col)
    re_tuples = [(m["text"], m["start"], m["end"], m["line"], m["column"]) for m in re_matches]
    dfa_tuples = [(m["text"], m["start"], m["end"], m["line"], m["column"]) for m in dfa_matches]

    re_set = set(re_tuples)
    dfa_set = set(dfa_tuples)

    only_in_re = [m for m in re_matches if (m["text"], m["start"], m["end"], m["line"], m["column"]) not in dfa_set]
    only_in_dfa = [m for m in dfa_matches if (m["text"], m["start"], m["end"], m["line"], m["column"]) not in re_set]

    is_equal = (len(only_in_re) == 0 and len(only_in_dfa) == 0)

    # 4. Timing Benchmark (average of 200 runs in microseconds via perf_counter)
    re_sec_avg = re_benchmark(target_text, "ing_word", runs=200)
    dfa_sec_avg = benchmark_dfa(target_text, runs=200)

    re_us = round(re_sec_avg * 1_000_000, 2)
    dfa_us = round(dfa_sec_avg * 1_000_000, 2)

    # 5. Lines of Code (non-blank, non-comment lines)
    re_file_loc = count_single_file_loc(PROJECT_ROOT / "core" / "re_engine.py")
    dfa_file_loc = count_single_file_loc(PROJECT_ROOT / "core" / "dfa_engine.py")
    dfa_def_loc = count_single_file_loc(PROJECT_ROOT / "core" / "dfa_definition.py")

    re_loc = re_file_loc["code"]
    dfa_loc = dfa_file_loc["code"] + dfa_def_loc["code"]

    speedup = round(re_us / dfa_us, 2) if dfa_us > 0 else 1.0
    faster_engine = "DFA" if dfa_us < re_us else "RE"

    return jsonify({
        "source": source_name,
        "char_count": len(target_text),
        "line_count": len(target_text.splitlines()),
        "equal": is_equal,
        "re": {
            "name": "Python Regular Expression (re module)",
            "pattern": r"\b[A-Za-z]+ing\b",
            "count": len(re_matches),
            "unique_count": len({m["text"] for m in re_matches}),
            "matches": re_matches,
            "time_us": re_us,
            "loc": re_loc
        },
        "dfa": {
            "name": "Hand-Built Deterministic Finite Automaton (DFA)",
            "pattern": "[A-Za-z]+ing (length >= 4)",
            "count": len(dfa_matches),
            "unique_count": len({m["text"] for m in dfa_matches}),
            "matches": dfa_matches,
            "time_us": dfa_us,
            "loc": dfa_loc
        },
        "diff": {
            "only_in_re": only_in_re,
            "only_in_dfa": only_in_dfa,
            "discrepancies": len(only_in_re) + len(only_in_dfa)
        },
        "performance": {
            "re_time_us": re_us,
            "dfa_time_us": dfa_us,
            "faster": faster_engine,
            "speedup_ratio": speedup,
            "runs": 200
        },
        "loc_comparison": {
            "re_code_lines": re_loc,
            "dfa_code_lines": dfa_loc,
            "diff_lines": dfa_loc - re_loc
        }
    }), 200


@app.route("/api/testcases", methods=["GET"])
def get_test_cases():
    """GET /api/testcases -> Full test case suite for UI verification tab."""
    flat_cases = []
    for pattern_key, cases in TEST_CASES.items():
        pattern_meta = PATTERNS.get(pattern_key, {})
        for idx, c in enumerate(cases):
            flat_cases.append({
                "id": f"{pattern_key}_{idx + 1}",
                "pattern": pattern_key,
                "label": pattern_meta.get("label", pattern_key),
                "regex": pattern_meta.get("regex", ""),
                "input": c["input"],
                "expected": c["expected"],
                "description": c.get("desc", "")
            })
    return jsonify({
        "total": len(flat_cases),
        "cases": flat_cases
    }), 200


if __name__ == "__main__":
    # Local development server on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
