"""Utility functions for TOC Project: Web Content Analyzer.

Provides:
- offset_to_line_col: Maps 0-based character offsets to 1-based (line, column).
- timing helpers: Benchmarking and execution time measurement via time.perf_counter.
- LOC counter: Computes lines of code metrics across codebase.
"""

import bisect
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def build_line_starts(text: str) -> List[int]:
    """Precompute 0-based character offsets where each line begins.
    
    Line 1 always begins at offset 0. Subsequent lines begin immediately
    following each newline character ('\n').
    """
    starts = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            starts.append(idx + 1)
    return starts


def offset_to_line_col(
    offset: int,
    text: Optional[str] = None,
    line_starts: Optional[List[int]] = None
) -> Tuple[int, int]:
    """Convert a 0-based character offset into 1-based (line, column) numbers.

    Args:
        offset: 0-based character offset into text.
        text: Source text string (used if line_starts is not supplied).
        line_starts: Precomputed list of line start indices from build_line_starts.

    Returns:
        (line, column): Both 1-based integers.
    """
    if line_starts is None:
        if text is None:
            raise ValueError("Either 'text' or 'line_starts' must be provided.")
        line_starts = build_line_starts(text)

    if offset < 0:
        offset = 0

    # bisect_right returns index into line_starts where offset < line_starts[idx]
    # The line number (1-based) is simply that index.
    line_idx = bisect.bisect_right(line_starts, offset)
    line_number = max(1, line_idx)
    col_number = offset - line_starts[line_number - 1] + 1
    return line_number, col_number


def time_execution(func: Callable, *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    """Execute a function once and return (result, elapsed_seconds)."""
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start_time
    return result, elapsed


def benchmark(func: Callable, *args: Any, runs: int = 200, **kwargs: Any) -> float:
    """Benchmark a function over multiple runs and return average execution time in seconds.

    Args:
        func: Callable to benchmark.
        *args: Positional arguments for func.
        runs: Number of iterations (default 200).
        **kwargs: Keyword arguments for func.

    Returns:
        Average execution time in seconds.
    """
    if runs < 1:
        runs = 1

    # Warm-up run
    func(*args, **kwargs)

    start_time = time.perf_counter()
    for _ in range(runs):
        func(*args, **kwargs)
    total_time = time.perf_counter() - start_time

    return total_time / runs


def count_loc(root_dir: str | Path, extensions: Optional[List[str]] = None) -> Dict[str, Any]:
    """Count lines of code (total, code, comments, blank) for files in root_dir.

    Args:
        root_dir: Root directory path to inspect.
        extensions: List of file extensions to include (e.g. ['.py', '.js', '.html']).
                    Defaults to ['.py', '.js', '.html', '.css', '.json'].

    Returns:
        Dict containing per-file stats and summary totals.
    """
    if extensions is None:
        extensions = [".py", ".js", ".html", ".css", ".json"]

    root_path = Path(root_dir)
    files_stats = []
    totals = {"files": 0, "total_lines": 0, "code_lines": 0, "comment_lines": 0, "blank_lines": 0}

    # Directories to ignore
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", ".vercel"}

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                fpath = Path(dirpath) / fname
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except Exception:
                    continue

                total = len(lines)
                blank = 0
                comment = 0
                code = 0

                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        blank += 1
                    elif stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                        comment += 1
                    else:
                        code += 1

                rel_path = str(fpath.relative_to(root_path)).replace("\\", "/")
                file_info = {
                    "file": rel_path,
                    "total": total,
                    "code": code,
                    "comment": comment,
                    "blank": blank
                }
                files_stats.append(file_info)
                totals["files"] += 1
                totals["total_lines"] += total
                totals["code_lines"] += code
                totals["comment_lines"] += comment
                totals["blank_lines"] += blank

    return {"summary": totals, "files": files_stats}
