"""Pytest Test Suite for Web Content Analyzer (RE vs DFA).

Verifies pattern matching for all 7 regexes, offset calculation,
RE engine extraction, and Flask REST API endpoints including SSRF protection.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.index import app
from core.patterns import get_compiled_pattern
from core.re_engine import extract
from core.scraper import ScraperSecurityError, validate_url_security
from core.utils import build_line_starts, offset_to_line_col
from tests.test_data import TEST_CASES

# ==============================================================================
# 1. PARAMETRIZED REGEX TESTS (Positives & Negatives for all 7 patterns)
# ==============================================================================

@pytest.mark.parametrize(
    "pattern_key, case",
    [
        (key, case)
        for key, cases in TEST_CASES.items()
        for case in cases
    ],
    ids=[
        f"{key}_{'pos' if case['expected'] else 'neg'}_{idx}"
        for key, cases in TEST_CASES.items()
        for idx, case in enumerate(cases)
    ]
)
def test_pattern_matching(pattern_key: str, case: dict):
    compiled_re = get_compiled_pattern(pattern_key)
    input_text = case["input"]
    expected = case["expected"]

    # Check if there is an exact or enclosed full-token match
    matches = list(compiled_re.finditer(input_text))

    if expected:
        assert len(matches) > 0, f"Expected match for pattern '{pattern_key}' on input: '{input_text}'"
        # The match should cover the token
        matched_str = matches[0].group(0)
        assert len(matched_str) > 0
    else:
        # Negative test cases should not find a valid matching token
        # (or if preceded/followed by illegal characters, should not match the full target)
        if matches:
            # If a match was found, verify whether it's an illegal partial match
            # Negatives like '98765432101' should not match as valid 10-digit mobile
            # Negatives like '24:00' should not match
            # Negatives like 'word#inline' should not match '#inline'
            assert False, f"Unexpected match for negative case '{input_text}' under '{pattern_key}': got '{matches[0].group(0)}'"


# ==============================================================================
# 2. UTILITY TESTS (offset_to_line_col)
# ==============================================================================

def test_offset_to_line_col():
    sample = "Line 1\nLine 2 with words\nLine 3"
    line_starts = build_line_starts(sample)

    # Offset 0 -> Line 1, Col 1 ('L')
    line, col = offset_to_line_col(0, line_starts=line_starts)
    assert line == 1 and col == 1

    # Offset 5 -> Line 1, Col 6 ('1')
    line, col = offset_to_line_col(5, line_starts=line_starts)
    assert line == 1 and col == 6

    # Offset 7 -> Line 2, Col 1 ('L' of Line 2)
    line, col = offset_to_line_col(7, line_starts=line_starts)
    assert line == 2 and col == 1

    # Offset 14 -> Line 2, Col 8 ('w' of with)
    line, col = offset_to_line_col(14, line_starts=line_starts)
    assert line == 2 and col == 8


# ==============================================================================
# 3. RE ENGINE EXTRACTION TESTS
# ==============================================================================

def test_extract_engine():
    text = (
        "Welcome to https://example.com/portal\n"
        "Contact: user@example.edu and phone 9876543210\n"
        "Meeting on 15-08-2024 at 14:30. #TOC #computing\n"
        "We are enjoying functional programming."
    )
    result = extract(text)

    assert "results" in result
    assert result["total_matches"] >= 7
    assert result["elapsed_ms"] >= 0

    res = result["results"]
    assert res["email"]["count"] == 1
    assert res["email"]["matches"][0]["text"] == "user@example.edu"
    assert res["email"]["matches"][0]["line"] == 2

    assert res["mobile"]["count"] == 1
    assert res["mobile"]["matches"][0]["text"] == "9876543210"

    assert res["date"]["count"] == 1
    assert res["date"]["matches"][0]["text"] == "15-08-2024"

    assert res["time"]["count"] == 1
    assert res["time"]["matches"][0]["text"] == "14:30"

    assert res["url"]["count"] >= 1
    assert "https://example.com/portal" in [m["text"] for m in res["url"]["matches"]]

    assert res["hashtag"]["count"] == 2
    assert {"#TOC", "#computing"}.issubset({m["text"] for m in res["hashtag"]["matches"]})

    assert res["ing_word"]["count"] >= 3
    ing_words = {m["text"].lower() for m in res["ing_word"]["matches"]}
    assert {"computing", "enjoying", "programming"}.issubset(ing_words)


def test_extract_pattern_filter():
    text = "Contact 9876543210 or dev@toc.org at 10:00"
    result = extract(text, pattern_keys=["email", "mobile"])

    assert "email" in result["results"]
    assert "mobile" in result["results"]
    assert "time" not in result["results"]
    assert result["results"]["email"]["count"] == 1
    assert result["results"]["mobile"]["count"] == 1


# ==============================================================================
# 4. SSRF SECURITY TESTS
# ==============================================================================

def test_ssrf_protection():
    # Loopback / Localhost
    with pytest.raises(ScraperSecurityError):
        validate_url_security("http://localhost:5000/api")

    with pytest.raises(ScraperSecurityError):
        validate_url_security("http://127.0.0.1:8080")

    with pytest.raises(ScraperSecurityError):
        validate_url_security("http://[::1]/secret")

    # Non-http/https
    with pytest.raises(ScraperSecurityError):
        validate_url_security("ftp://ftp.example.com/file")

    with pytest.raises(ScraperSecurityError):
        validate_url_security("file:///etc/passwd")


# ==============================================================================
# 5. FLASK API ENDPOINT TESTS
# ==============================================================================

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_api_pages_list(client):
    res = client.get("/api/pages")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) == 3
    ids = {item["id"] for item in data}
    assert ids == {"page1", "page2", "page3"}


def test_api_page_detail_success(client):
    res = client.get("/api/pages/page1")
    assert res.status_code == 200
    data = res.get_json()
    assert data["id"] == "page1"
    assert "text" in data
    assert len(data["text"]) > 0
    assert data["char_count"] > 0


def test_api_page_detail_404(client):
    res = client.get("/api/pages/non_existent_page")
    assert res.status_code == 404
    data = res.get_json()
    assert "error" in data


def test_api_patterns(client):
    res = client.get("/api/patterns")
    assert res.status_code == 200
    data = res.get_json()
    for key in ["email", "mobile", "date", "url", "hashtag", "time", "ing_word"]:
        assert key in data
        assert "regex" in data[key]
        assert "label" in data[key]


def test_api_analyze_re_with_text(client):
    payload = {
        "text": "Send inquiry to info@test.com before 31-12-2025 #deadline.",
        "patterns": ["email", "date", "hashtag"]
    }
    res = client.post("/api/analyze/re", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["results"]["email"]["count"] == 1
    assert data["results"]["date"]["count"] == 1
    assert data["results"]["hashtag"]["count"] == 1


def test_api_analyze_re_with_page_id(client):
    payload = {"page_id": "page1"}
    res = client.post("/api/analyze/re", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["source"]["type"] == "snapshot"
    assert data["total_matches"] > 0


def test_api_analyze_re_bad_request(client):
    res = client.post("/api/analyze/re", json={})
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


def test_api_summary(client):
    res = client.get("/api/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert "pages" in data
    assert "totals" in data
    assert "patterns" in data
    # Confirm every pattern is reported in totals
    for k in ["email", "mobile", "date", "url", "hashtag", "time", "ing_word"]:
        assert k in data["totals"]
        assert data["totals"][k] > 0  # All 7 patterns have non-zero total matches!


def test_api_fetch_ssrf_blocked(client):
    res = client.post("/api/fetch", json={"url": "http://127.0.0.1:8000/admin"})
    assert res.status_code == 400
    data = res.get_json()
    assert data["error"] == "Security Error"
