"""Deterministic Finite Automaton (DFA) Definition for '[A-Za-z]+ing'.

Single source of truth for the formal 5-tuple (Q, Sigma, delta, q0, F),
used by the DFA engine, derivation documents, diagram generator, and frontend API.
"""

from typing import Any

# ==============================================================================
# ALPHABET AND CHARACTER CLASSES
# ==============================================================================
# Sigma is partitioned into 5 mutually exclusive character classes:
# 1. 'I'           : { 'i', 'I' }
# 2. 'N'           : { 'n', 'N' }
# 3. 'G'           : { 'g', 'G' }
# 4. 'OTHER_LETTER': [A-Za-z] \ { 'i','I','n','N','g','G' }
# 5. 'NON_LETTER'  : Any character outside [A-Za-z]

ALPHABET_CLASSES: dict[str, str] = {
    "I": "Letter 'i' or 'I'",
    "N": "Letter 'n' or 'N'",
    "G": "Letter 'g' or 'G'",
    "OTHER_LETTER": "Any alphabetic letter except i, n, g (case-insensitive)",
    "NON_LETTER": "Any non-alphabetic character (digits, whitespace, punctuation)"
}

# ==============================================================================
# STATE DEFINITIONS
# ==============================================================================
# Minimal 5 states + 1 explicit dead/trap state

STATES: dict[str, dict[str, Any]] = {
    "q0": {
        "id": "q0",
        "label": "q0: Start",
        "meaning": "Initial state; 0 letters seen in current token (no progress).",
        "is_start": True,
        "is_accepting": False
    },
    "q1": {
        "id": "q1",
        "label": "q1: Prefix >= 1 letter",
        "meaning": "At least 1 letter seen; current suffix does not end in 'i', 'in', or 'ing'.",
        "is_start": False,
        "is_accepting": False
    },
    "q2": {
        "id": "q2",
        "label": "q2: Suffix 'i'",
        "meaning": "At least 2 letters seen; current suffix ends in 'i'.",
        "is_start": False,
        "is_accepting": False
    },
    "q3": {
        "id": "q3",
        "label": "q3: Suffix 'in'",
        "meaning": "At least 3 letters seen; current suffix ends in 'in'.",
        "is_start": False,
        "is_accepting": False
    },
    "q4": {
        "id": "q4",
        "label": "q4: Suffix 'ing' (Accept)",
        "meaning": "At least 4 letters seen; current suffix ends in 'ing'. ACCEPTING STATE.",
        "is_start": False,
        "is_accepting": True
    },
    "q_trap": {
        "id": "q_trap",
        "label": "q_trap: Trap / Dead",
        "meaning": "Dead state entered when an invalid non-letter is encountered inside a word.",
        "is_start": False,
        "is_accepting": False
    }
}

START_STATE: str = "q0"
ACCEPTING_STATES: set[str] = {"q4"}

# ==============================================================================
# STATE TRANSITION FUNCTION delta: Q x Sigma -> Q
# ==============================================================================
# delta[state][char_class] -> next_state

DELTA: dict[str, dict[str, str]] = {
    "q0": {
        "I": "q1",
        "N": "q1",
        "G": "q1",
        "OTHER_LETTER": "q1",
        "NON_LETTER": "q_trap"
    },
    "q1": {
        "I": "q2",
        "N": "q1",
        "G": "q1",
        "OTHER_LETTER": "q1",
        "NON_LETTER": "q_trap"
    },
    "q2": {
        "I": "q2",
        "N": "q3",
        "G": "q1",
        "OTHER_LETTER": "q1",
        "NON_LETTER": "q_trap"
    },
    "q3": {
        "I": "q2",
        "N": "q1",
        "G": "q4",
        "OTHER_LETTER": "q1",
        "NON_LETTER": "q_trap"
    },
    "q4": {
        "I": "q2",
        "N": "q1",
        "G": "q1",
        "OTHER_LETTER": "q1",
        "NON_LETTER": "q_trap"
    },
    "q_trap": {
        "I": "q_trap",
        "N": "q_trap",
        "G": "q_trap",
        "OTHER_LETTER": "q_trap",
        "NON_LETTER": "q_trap"
    }
}


# ==============================================================================
# CHARACTER CLASSIFICATION (STRICTLY NO REGEX, PURE ORD/COMPUTE)
# ==============================================================================

def classify_char(ch: str) -> str:
    """Classify a single character into one of the 5 alphabet classes.
    
    Uses only ord() and explicit character checks (no regex, no str methods).
    """
    if not ch:
        return "NON_LETTER"

    o = ord(ch)

    # Check ASCII uppercase (65-90) and lowercase (97-122)
    is_letter = (65 <= o <= 90) or (97 <= o <= 122)

    if not is_letter:
        return "NON_LETTER"

    # Explicit case check for i, n, g
    if ch == "i" or ch == "I":
        return "I"
    if ch == "n" or ch == "N":
        return "N"
    if ch == "g" or ch == "G":
        return "G"

    return "OTHER_LETTER"


def is_alphanumeric_or_underscore(ch: str) -> bool:
    """Check if character is [A-Za-z0-9_] for token boundary detection."""
    if not ch:
        return False
    o = ord(ch)
    return (
        (65 <= o <= 90)     # A-Z
        or (97 <= o <= 122) # a-z
        or (48 <= o <= 57)  # 0-9
        or (ch == "_")
    )


def get_dfa_definition() -> dict[str, Any]:
    """Return complete serializable DFA definition for API and frontend."""
    # Build transition table rows for markdown and UI
    class_order = ["I", "N", "G", "OTHER_LETTER", "NON_LETTER"]
    state_order = ["q0", "q1", "q2", "q3", "q4", "q_trap"]

    table = []
    for s in state_order:
        row = {
            "state": s,
            "label": STATES[s]["label"],
            "meaning": STATES[s]["meaning"],
            "is_start": STATES[s]["is_start"],
            "is_accepting": STATES[s]["is_accepting"],
            "transitions": {cls: DELTA[s][cls] for cls in class_order}
        }
        table.append(row)

    return {
        "formal_name": "Minimal DFA for English '-ing' Words",
        "pattern": "[A-Za-z]+ing",
        "description": "Recognizes one or more letters followed by 'ing' (case-insensitive, length >= 4)",
        "five_tuple": {
            "Q": state_order,
            "Sigma": class_order,
            "delta": DELTA,
            "q0": START_STATE,
            "F": list(ACCEPTING_STATES)
        },
        "states": STATES,
        "alphabet_classes": ALPHABET_CLASSES,
        "transition_table": table
    }
