"""Pytest Test Suite for DFA Engine (Stage 2).

Verifies:
1. Exact bit-for-bit equivalence between DFA engine and RE engine across all 3 web snapshots.
2. Hand-written word acceptance and rejection on 35+ benchmark tokens.
3. Step-by-step trace simulation.
4. All new Flask REST API endpoints:
   - GET /api/dfa/definition
   - POST /api/analyze/dfa
   - POST /api/dfa/trace
   - POST /api/compare
   - GET /api/testcases
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.index import app
from core.dfa_engine import scan_text, trace
from core.re_engine import extract_single_pattern

HAND_WRITTEN_TEST_WORDS = [
    # (word, expected_accepted, description)
    # 1-21: Positives
    ("learning", True, "Standard 8-letter participle"),
    ("ring", True, "Minimal 4-letter word starting with r"),
    ("sing", True, "Minimal 4-letter word starting with s"),
    ("bring", True, "5-letter word"),
    ("king", True, "4-letter word"),
    ("singing", True, "Repeated 'ing' pattern"),
    ("thing", True, "5-letter noun"),
    ("inging", True, "Prefixed by 'ing', valid length 6"),
    ("string", True, "6-letter word"),
    ("spring", True, "6-letter word"),
    ("wing", True, "4-letter word"),
    ("running", True, "Doubled consonant before -ing"),
    ("testing", True, "Gerund"),
    ("programming", True, "Computing domain word"),
    ("debugging", True, "Computing domain word"),
    ("PARSING", True, "All uppercase case-insensitive"),
    ("Writing", True, "Titlecase capitalized"),
    ("skiing", True, "Consecutive 'i' letters"),
    ("iing", True, "Minimal length 4 with 'i' prefix"),
    ("winning", True, "Standard 7-letter word"),
    ("beginning", True, "Longer participle"),
    ("dinging", True, "Repeated ing syllables"),

    # 22-38: Negatives
    ("ing", False, "Length 3 alone without prefix letter"),
    ("Ing", False, "Length 3 capitalized without prefix"),
    ("ING", False, "Length 3 all caps without prefix"),
    ("in", False, "Length 2 missing 'g'"),
    ("INGest", False, "Suffix is 'est', not 'ing'"),
    ("finger", False, "Suffix is 'er'"),
    ("singer", False, "Suffix is 'er'"),
    ("ring123", False, "Digits attached directly"),
    ("123sing", False, "Digits preceding"),
    ("ding_dong", False, "Contains underscore"),
    ("", False, "Empty string"),
    ("a", False, "Single letter"),
    ("inn", False, "Ends in 'nn'"),
    ("signing1", False, "Ends in digit"),
    ("hello", False, "No 'ing'"),
    ("stringy", False, "Ends in 'y'"),
]


# ==============================================================================
# 1. BIT-FOR-BIT EQUALITY ACROSS ALL 3 PAGES
# ==============================================================================

@pytest.mark.parametrize("page_id", ["page1", "page2", "page3"])
def test_dfa_equals_re_on_snapshots(page_id: str):
    """Confirm DFA scanner matches RE engine exactly on positions, counts, and text."""
    page_path = PROJECT_ROOT / "data" / "pages" / f"{page_id}.txt"
    assert page_path.exists(), f"Snapshot {page_path} must exist"

    text = page_path.read_text(encoding="utf-8")

    # Extract via RE engine
    re_result = extract_single_pattern(text, "ing_word")
    re_matches = re_result["matches"]

    # Extract via DFA engine
    dfa_matches = scan_text(text)

    # Convert to comparable tuples (text, start, end, line, column)
    re_tuples = [(m["text"], m["start"], m["end"], m["line"], m["column"]) for m in re_matches]
    dfa_tuples = [(m["text"], m["start"], m["end"], m["line"], m["column"]) for m in dfa_matches]

    assert len(re_matches) > 0, f"Page {page_id} should have matches"
    assert len(re_matches) == len(dfa_matches), (
        f"Page {page_id} count mismatch: RE={len(re_matches)}, DFA={len(dfa_matches)}"
    )
    assert re_tuples == dfa_tuples, f"Page {page_id} matches are not identical!"


# ==============================================================================
# 2. HAND-WRITTEN BENCHMARK TOKENS (35+ test words)
# ==============================================================================

@pytest.mark.parametrize("word, expected, desc", HAND_WRITTEN_TEST_WORDS)
def test_hand_written_words(word: str, expected: bool, desc: str):
    tr = trace(word)
    assert tr["accepted"] == expected, (
        f"Failed on '{word}' ({desc}): expected accepted={expected}, got {tr['accepted']} (state={tr['final_state']})"
    )


# ==============================================================================
# 3. TOKEN BOUNDARY & PUNCTUATION TESTS
# ==============================================================================

def test_token_boundaries_in_prose():
    prose = "He was sing. They started sing-song, then re-sing for king's pleasure, but not 123sing or sing123."
    dfa_matches = scan_text(prose)
    re_matches = extract_single_pattern(prose, "ing_word")["matches"]

    dfa_words = [m["text"] for m in dfa_matches]
    re_words = [m["text"] for m in re_matches]

    assert dfa_words == re_words
    # Verify exact words captured
    assert dfa_words == ["sing", "sing", "sing", "king"]


# ==============================================================================
# 4. STEP-BY-STEP TRACE SIMULATOR
# ==============================================================================

def test_trace_simulation_details():
    res = trace("sing")
    assert res["accepted"] is True
    assert res["final_state"] == "q4"
    assert len(res["steps"]) == 4

    step_states = [(s["from_state"], s["to_state"]) for s in res["steps"]]
    assert step_states == [
        ("q0", "q1"), # 's'
        ("q1", "q2"), # 'i'
        ("q2", "q3"), # 'n'
        ("q3", "q4")  # 'g'
    ]


def test_trace_rejected_details():
    res = trace("ing")
    assert res["accepted"] is False
    assert res["final_state"] == "q1"
    assert len(res["steps"]) == 3

    step_states = [(s["from_state"], s["to_state"]) for s in res["steps"]]
    assert step_states == [
        ("q0", "q1"), # 'i'
        ("q1", "q1"), # 'n'
        ("q1", "q1")  # 'g'
    ]


# ==============================================================================
# 5. NEW API ENDPOINTS
# ==============================================================================

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_dfa_definition(client):
    res = client.get("/api/dfa/definition")
    assert res.status_code == 200
    data = res.get_json()
    assert "five_tuple" in data
    assert "states" in data
    assert "transition_table" in data
    assert data["five_tuple"]["q0"] == "q0"
    assert "q4" in data["five_tuple"]["F"]


def test_api_analyze_dfa_with_page(client):
    res = client.post("/api/analyze/dfa", json={"page_id": "page1"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_matches"] == 92
    assert "ing_word" in data["results"]


def test_api_analyze_dfa_with_text(client):
    res = client.post("/api/analyze/dfa", json={"text": "learning and string"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_matches"] == 2


def test_api_dfa_trace(client):
    res = client.post("/api/dfa/trace", json={"word": "learning"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["accepted"] is True
    assert data["final_state"] == "q4"
    assert len(data["steps"]) == 8


def test_api_compare_page1(client):
    res = client.post("/api/compare", json={"page_id": "page1"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["equal"] is True
    assert data["re"]["count"] == 92
    assert data["dfa"]["count"] == 92
    assert len(data["diff"]["only_in_re"]) == 0
    assert len(data["diff"]["only_in_dfa"]) == 0
    assert data["performance"]["re_time_us"] > 0
    assert data["performance"]["dfa_time_us"] > 0
    assert data["loc_comparison"]["re_code_lines"] > 0
    assert data["loc_comparison"]["dfa_code_lines"] > 0


def test_api_testcases(client):
    res = client.get("/api/testcases")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] >= 70
    assert len(data["cases"]) >= 70
