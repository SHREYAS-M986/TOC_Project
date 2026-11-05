"""Deterministic Finite Automaton (DFA) Extraction Engine.

STRICTLY IMPLEMENTED WITHOUT REGEX (no 're' module, no str.endswith shortcuts).
Executes pattern matching via a pure table-driven transition loop:
    state = DELTA[state][classify_char(char)]

Extracts English words ending in 'ing' with at least 1 prefix letter (length >= 4).
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from core.dfa_definition import (
    ACCEPTING_STATES,
    DELTA,
    START_STATE,
    classify_char,
    is_alphanumeric_or_underscore,
)


def trace(word: str) -> dict[str, Any]:
    """Execute DFA state transitions step-by-step on a single word token.

    Args:
        word: Target string to validate (e.g. "learning", "string", "ing").

    Returns:
        Dict with evaluation details, steps array for UI simulation,
        and boolean accepted flag.
    """
    state = START_STATE
    steps = []

    for idx, ch in enumerate(word):
        cls = classify_char(ch)
        next_state = DELTA[state][cls]
        steps.append(
            {
                "step": idx + 1,
                "char": ch,
                "class": cls,
                "from_state": state,
                "to_state": next_state,
            }
        )
        state = next_state

    # Machine accepts if in accepting state (q4)
    accepted = state in ACCEPTING_STATES

    return {
        "word": word,
        "accepted": accepted,
        "final_state": state,
        "length": len(word),
        "steps": steps,
    }


def scan_text(text: str) -> list[dict[str, Any]]:
    """Scan full text in a single pass, computing line/column incrementally.

    Recognizes words ending in 'ing' (case-insensitive) strictly via DFA.
    Delimited by natural word boundaries.

    Returns:
        List of match dicts: {text, start, end, line, column}
    """
    matches = []
    line = 1
    col = 1
    word_start: int | None = None
    word_line = 1
    word_col = 1
    state = START_STATE
    valid_start_boundary = True

    n = len(text)
    for idx, ch in enumerate(text):
        cls = classify_char(ch)

        if cls != "NON_LETTER":
            # Entering or continuing an alphabetic sequence
            if word_start is None:
                word_start = idx
                word_line = line
                word_col = col
                state = START_STATE
                # Check preceding character for token boundary:
                # Must not be preceded by alphanumeric or underscore (e.g. 123sing, _Violating)
                valid_start_boundary = idx == 0 or not is_alphanumeric_or_underscore(
                    text[idx - 1]
                )

            # Core DFA table transition
            state = DELTA[state][cls]

        else:
            # Reached a non-letter delimiter
            if word_start is not None:
                # Token ended. Check boundary validity at the end:
                # Must not be immediately followed by digit/underscore (e.g. sing123, backing25)
                valid_end_boundary = not is_alphanumeric_or_underscore(ch)

                if (
                    state in ACCEPTING_STATES
                    and valid_start_boundary
                    and valid_end_boundary
                ):
                    matched_str = text[word_start:idx]
                    matches.append(
                        {
                            "text": matched_str,
                            "start": word_start,
                            "end": idx,
                            "line": word_line,
                            "column": word_col,
                        }
                    )

                word_start = None
                state = START_STATE

        # Incremental line and column counter
        if ch == "\n":
            line += 1
            col = 1
        else:
            col += 1

    # End of string boundary check
    if word_start is not None and state in ACCEPTING_STATES and valid_start_boundary:
        matches.append(
            {
                "text": text[word_start:n],
                "start": word_start,
                "end": n,
                "line": word_line,
                "column": word_col,
            }
        )

    return matches


def extract(text: str, pattern_keys: list[str] | None = None) -> dict[str, Any]:
    """Execute DFA pattern matching, formatted in the same shape as RE engine.

    Args:
        text: Input string to scan.
        pattern_keys: Optional filter list (DFA handles 'ing_word').

    Returns:
        Dict matching RE extraction results structure for seamless comparison.
    """
    start_time = time.perf_counter()
    matches = scan_text(text)
    elapsed_seconds = time.perf_counter() - start_time
    elapsed_ms = round(elapsed_seconds * 1000, 3)

    unique_items = {m["text"] for m in matches}

    pattern_result = {
        "key": "ing_word",
        "label": "Words ending in 'ing' (DFA)",
        "regex": r"\b[A-Za-z]+ing\b",
        "count": len(matches),
        "unique_count": len(unique_items),
        "matches": matches,
    }

    results = {"ing_word": pattern_result}

    return {
        "results": results,
        "patterns": results,
        "total_matches": len(matches),
        "elapsed_seconds": elapsed_seconds,
        "elapsed_ms": elapsed_ms,
    }


def benchmark_dfa(text: str, runs: int = 200) -> float:
    """Benchmark DFA extraction average execution time in seconds over multiple runs."""
    runs = max(runs, 1)

    # Warm-up
    scan_text(text)

    start = time.perf_counter()
    for _ in range(runs):
        scan_text(text)
    total = time.perf_counter() - start

    return total / runs


# ==============================================================================
# CLI INTERFACE: python -m core.dfa_engine --page 1
# ==============================================================================


def format_cli_table(results: dict[str, Any]) -> str:
    """Format ASCII table of DFA extraction matches."""
    headers = ["Pattern", "Count", "Extracted items", "Positions (L:C)"]
    col_widths = [26, 7, 36, 26]

    def truncate(s: str, max_len: int) -> str:
        s = s.replace("\n", " ")
        return s if len(s) <= max_len else s[: max_len - 3] + "..."

    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_row = (
        "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    )
    lines = [sep, header_row, sep]

    data = results["results"]["ing_word"]
    label = data["label"]
    count_str = str(data["count"])
    matches = data["matches"]

    if not matches:
        lines.append(
            f"| {truncate(label, col_widths[0]).ljust(col_widths[0])} "
            f"| {count_str.rjust(col_widths[1])} "
            f"| {'(none)'.ljust(col_widths[2])} "
            f"| {'-'.ljust(col_widths[3])} |"
        )
    else:
        first_m = matches[0]
        first_pos = f"{first_m['line']}:{first_m['column']}"
        lines.append(
            f"| {truncate(label, col_widths[0]).ljust(col_widths[0])} "
            f"| {count_str.rjust(col_widths[1])} "
            f"| {truncate(first_m['text'], col_widths[2]).ljust(col_widths[2])} "
            f"| {first_pos.ljust(col_widths[3])} |"
        )

        max_extra = min(6, len(matches) - 1)
        for m in matches[1 : 1 + max_extra]:
            m_pos = f"{m['line']}:{m['column']}"
            lines.append(
                f"| {' '.ljust(col_widths[0])} "
                f"| {' '.rjust(col_widths[1])} "
                f"| {truncate(m['text'], col_widths[2]).ljust(col_widths[2])} "
                f"| {m_pos.ljust(col_widths[3])} |"
            )
        if len(matches) > 7:
            lines.append(
                f"| {' '.ljust(col_widths[0])} "
                f"| {' '.rjust(col_widths[1])} "
                f"| {f'(+{len(matches) - 7} more items)'.ljust(col_widths[2])} "
                f"| {'...'.ljust(col_widths[3])} |"
            )

    lines.append(sep)
    summary_line = (
        f"Total DFA Matches: {results['total_matches']} | "
        f"Scan Time: {results['elapsed_ms']} ms"
    )
    return "\n".join(lines) + "\n" + summary_line


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DFA Engine: Extract '-ing' words without regex."
    )
    parser.add_argument(
        "--page", type=int, choices=[1, 2, 3], help="Page snapshot number (1, 2, or 3)"
    )
    parser.add_argument("--file", type=str, help="Path to text file to analyze")
    parser.add_argument(
        "--word", type=str, help="Single word to trace step-by-step through DFA"
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Run 200-run timing benchmark"
    )

    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent

    if args.word:
        tr = trace(args.word)
        print(f"\n=== DFA Trace for: '{args.word}' ===")
        print(f"Accepted: {tr['accepted']} (Final State: {tr['final_state']})")
        print("-" * 55)
        print(f"{'Step':<6} | {'Char':<6} | {'Class':<14} | {'Transition':<16}")
        print("-" * 55)
        for s in tr["steps"]:
            trans = f"{s['from_state']} -> {s['to_state']}"
            print(f"{s['step']:<6} | {s['char']!r:<6} | {s['class']:<14} | {trans:<16}")
        print("-" * 55)
        return

    if args.page:
        page_file = project_root / "data" / "pages" / f"page{args.page}.txt"
        if not page_file.exists():
            print(f"Error: Page snapshot not found: {page_file}", file=sys.stderr)
            sys.exit(1)
        text = page_file.read_text(encoding="utf-8")
        target_name = f"Page {args.page} ({page_file.name})"
    elif args.file:
        fpath = Path(args.file)
        if not fpath.exists():
            print(f"Error: File not found: {fpath}", file=sys.stderr)
            sys.exit(1)
        text = fpath.read_text(encoding="utf-8")
        target_name = fpath.name
    else:
        print("Reading text from STDIN...")
        text = sys.stdin.read()
        target_name = "STDIN"

    results = extract(text)
    print(f"\n=== DFA Engine Pattern Extraction Report: {target_name} ===")
    print(format_cli_table(results))

    if args.benchmark:
        print("\n--- Benchmark (Average over 200 runs) ---")
        avg_sec = benchmark_dfa(text, runs=200)
        print(
            f"  DFA Scan Time: {avg_sec * 1_000_000:8.2f} µs ({avg_sec * 1000:8.4f} ms)"
        )


if __name__ == "__main__":
    main()
