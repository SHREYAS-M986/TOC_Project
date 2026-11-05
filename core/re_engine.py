"""Regular Expression Pattern Extraction Engine.

Executes pattern matching against input text using Python's 're' module,
computes 0-based offsets and 1-based (line, column) positions, and collects
metrics (count, unique_count, execution time).
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from core.patterns import PATTERNS, get_compiled_pattern, get_pattern
from core.utils import build_line_starts, offset_to_line_col


def extract_single_pattern(
    text: str, pattern_key: str, line_starts: list[int] | None = None
) -> dict[str, Any]:
    """Extract matches for a single pattern key from text.

    Args:
        text: Target text string.
        pattern_key: Key in PATTERNS registry.
        line_starts: Optional precomputed line start offsets.

    Returns:
        Dict with pattern metadata, count, unique_count, and list of matches.
    """
    if line_starts is None:
        line_starts = build_line_starts(text)

    pattern_meta = get_pattern(pattern_key)
    compiled_re = get_compiled_pattern(pattern_key)

    matches = []
    for match in compiled_re.finditer(text):
        m_text = match.group(0)
        start = match.start()
        end = match.end()
        line, col = offset_to_line_col(start, line_starts=line_starts)
        matches.append(
            {"text": m_text, "start": start, "end": end, "line": line, "column": col}
        )

    unique_items = {m["text"] for m in matches}

    return {
        "key": pattern_key,
        "label": pattern_meta["label"],
        "regex": pattern_meta["regex"],
        "count": len(matches),
        "unique_count": len(unique_items),
        "matches": matches,
    }


def extract(text: str, pattern_keys: list[str] | None = None) -> dict[str, Any]:
    """Extract all or selected patterns from text using Python regular expressions.

    Args:
        text: Input text string to analyze.
        pattern_keys: Optional list of pattern keys to run (defaults to all 7).

    Returns:
        Dict mapping pattern keys to their match results, plus aggregate stats
        and execution timing.
    """
    if pattern_keys is None:
        keys_to_run = list(PATTERNS.keys())
    else:
        keys_to_run = [k for k in pattern_keys if k in PATTERNS]

    start_time = time.perf_counter()
    line_starts = build_line_starts(text)

    results: dict[str, dict[str, Any]] = {}
    total_matches = 0

    for key in keys_to_run:
        pattern_result = extract_single_pattern(text, key, line_starts=line_starts)
        results[key] = pattern_result
        total_matches += pattern_result["count"]

    elapsed_seconds = time.perf_counter() - start_time
    elapsed_ms = round(elapsed_seconds * 1000, 3)

    return {
        "results": results,
        "patterns": results,  # Alias for flexibility
        "total_matches": total_matches,
        "elapsed_seconds": elapsed_seconds,
        "elapsed_ms": elapsed_ms,
    }


def benchmark(text: str, pattern_key: str, runs: int = 200) -> float:
    """Benchmark extraction time for a specific pattern over a number of runs.

    Args:
        text: Input text string.
        pattern_key: Key in PATTERNS registry.
        runs: Number of iterations (default 200).

    Returns:
        Average execution time per run in seconds.
    """
    runs = max(runs, 1)

    compiled_re = get_compiled_pattern(pattern_key)

    # Warm-up
    list(compiled_re.finditer(text))

    start_time = time.perf_counter()
    for _ in range(runs):
        list(compiled_re.finditer(text))
    total_duration = time.perf_counter() - start_time

    return total_duration / runs


def benchmark_all(text: str, runs: int = 200) -> dict[str, float]:
    """Benchmark all registered patterns and return average seconds per run."""
    timings = {}
    for key in PATTERNS.keys():
        timings[key] = benchmark(text, key, runs=runs)
    return timings


# ==============================================================================
# CLI INTERFACE: python -m core.re_engine --page 1
# ==============================================================================


def format_cli_table(results: dict[str, Any]) -> str:
    """Render a clean ASCII table of extraction results for terminal/screenshots."""
    headers = ["Pattern", "Count", "Extracted items", "Positions (L:C)"]
    col_widths = [24, 7, 36, 26]

    def truncate(s: str, max_len: int) -> str:
        s = s.replace("\n", " ")
        return s if len(s) <= max_len else s[: max_len - 3] + "..."

    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_row = (
        "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    )

    lines = [sep, header_row, sep]

    for key, data in results["results"].items():
        label = data["label"]
        count_str = str(data["count"])
        matches = data["matches"]

        if not matches:
            items_str = "(none)"
            pos_str = "-"
            lines.append(
                f"| {truncate(label, col_widths[0]).ljust(col_widths[0])} "
                f"| {count_str.rjust(col_widths[1])} "
                f"| {truncate(items_str, col_widths[2]).ljust(col_widths[2])} "
                f"| {truncate(pos_str, col_widths[3]).ljust(col_widths[3])} |"
            )
        else:
            # First row with count and first item
            first_m = matches[0]
            first_item = first_m["text"]
            first_pos = f"{first_m['line']}:{first_m['column']}"
            lines.append(
                f"| {truncate(label, col_widths[0]).ljust(col_widths[0])} "
                f"| {count_str.rjust(col_widths[1])} "
                f"| {truncate(first_item, col_widths[2]).ljust(col_widths[2])} "
                f"| {truncate(first_pos, col_widths[3]).ljust(col_widths[3])} |"
            )

            # Subsequent rows for up to 4 more items to keep table clean and informative
            max_extra = min(4, len(matches) - 1)
            for m in matches[1 : 1 + max_extra]:
                m_item = m["text"]
                m_pos = f"{m['line']}:{m['column']}"
                lines.append(
                    f"| {' '.ljust(col_widths[0])} "
                    f"| {' '.rjust(col_widths[1])} "
                    f"| {truncate(m_item, col_widths[2]).ljust(col_widths[2])} "
                    f"| {truncate(m_pos, col_widths[3]).ljust(col_widths[3])} |"
                )
            if len(matches) > 5:
                extra_cnt = len(matches) - 5
                lines.append(
                    f"| {' '.ljust(col_widths[0])} "
                    f"| {' '.rjust(col_widths[1])} "
                    f"| {f'(+{extra_cnt} more items)'.ljust(col_widths[2])} "
                    f"| {'...'.ljust(col_widths[3])} |"
                )

        lines.append(sep)

    summary_line = (
        f"Total Matches: {results['total_matches']} | "
        f"Extraction Time: {results['elapsed_ms']} ms"
    )
    return "\n".join(lines) + "\n" + summary_line


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RE Engine: Extract TOC patterns from text."
    )
    parser.add_argument(
        "--page", type=int, choices=[1, 2, 3], help="Page snapshot number (1, 2, or 3)"
    )
    parser.add_argument("--file", type=str, help="Path to custom text file to analyze")
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run 200-iteration benchmark per pattern",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    if args.page:
        page_file = project_root / "data" / "pages" / f"page{args.page}.txt"
        if not page_file.exists():
            print(f"Error: Page file not found: {page_file}", file=sys.stderr)
            sys.exit(1)
        text = page_file.read_text(encoding="utf-8")
        target_name = f"Page {args.page} ({page_file.name})"
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        text = file_path.read_text(encoding="utf-8")
        target_name = file_path.name
    else:
        print("Reading text from STDIN (Ctrl+D / Ctrl+Z to end)...")
        text = sys.stdin.read()
        target_name = "STDIN"

    results = extract(text)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print(f"\n=== RE Engine Pattern Extraction Report: {target_name} ===")
    print(format_cli_table(results))

    if args.benchmark:
        print("\n--- Benchmark (Average over 200 runs) ---")
        bench = benchmark_all(text, runs=200)
        for k, avg_sec in bench.items():
            print(f"  {k:12s}: {avg_sec * 1000:8.4f} ms")


if __name__ == "__main__":
    main()
