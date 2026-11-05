"""Script to collect and snapshot 3 web pages for TOC Project.

Fetches 3 distinct web pages from public sources across 3 categories:
1. Educational (UGC - University Grants Commission)
2. News Portal (The Indian Express - Health & Crisis Helplines Article)
3. Tech Blog / Community (DEV Community - Python Tag & Articles)

Cleans HTML, preserves links and mailto targets, collapses excess whitespace
while preserving line breaks, and writes snapshots to data/pages/page[1-3].txt
and metadata to data/pages/sources.json.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.re_engine import extract
from core.scraper import fetch_and_clean_page

PAGE_SOURCES = [
    {
        "id": "page1",
        "category": "Educational",
        "url": "https://www.ugc.gov.in/",
        "target_title": "University Grants Commission (UGC) Portal",
        "reason": "Official apex higher education regulatory portal in India rich in circulars, official emails, DD-MM-YYYY dates, URLs, and academic terminology."
    },
    {
        "id": "page2",
        "category": "News Portal",
        "url": "https://indianexpress.com/article/health-wellness/mumbai-ict-student-death-mental-health-warning-signs-depression-help-10938783/",
        "target_title": "The Indian Express: Mental Health Helplines & Support News Article",
        "reason": "National news article featuring verified Indian crisis helpline mobile numbers (+91 / 98...), support emails, published timestamps, URLs, and reportage."
    },
    {
        "id": "page3",
        "category": "Tech Blog / Community",
        "url": "https://dev.to/t/python",
        "target_title": "DEV Community: Python Tag Articles & Discussions",
        "reason": "Developer community publishing platform rich in hashtags (#python, #webdev, etc.), external code links, author posts, and tech vocabulary."
    }
]


def collect() -> None:
    pages_dir = PROJECT_ROOT / "data" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    sources_metadata = []
    summary_rows = []

    print("=" * 80)
    print("Collecting Web Page Snapshots for TOC RE vs DFA Case Study")
    print("=" * 80)

    for idx, cfg in enumerate(PAGE_SOURCES, start=1):
        page_id = cfg["id"]
        url = cfg["url"]
        category = cfg["category"]
        print(f"\n[{idx}/3] Fetching Page {idx} ({category}): {url}")

        try:
            page_data = fetch_and_clean_page(url, timeout=15)
            text = page_data["text"]
            title = page_data["title"] or cfg["target_title"]

            # Save snapshot text
            snapshot_path = pages_dir / f"{page_id}.txt"
            snapshot_path.write_text(text, encoding="utf-8")

            # Extract patterns to verify qualification criteria
            analysis = extract(text)
            pattern_counts = {k: v["count"] for k, v in analysis["results"].items()}
            qualifying_patterns = sum(1 for c in pattern_counts.values() if c >= 5)

            meta = {
                "id": page_id,
                "title": title,
                "url": url,
                "category": category,
                "fetched_on": datetime.now(timezone.utc).isoformat(),
                "char_count": page_data["char_count"],
                "line_count": page_data["line_count"],
                "pattern_counts": pattern_counts,
                "qualifying_patterns": qualifying_patterns,
                "reason": cfg["reason"]
            }
            sources_metadata.append(meta)

            summary_rows.append({
                "Page": page_id,
                "Category": category,
                "Title": title[:38] + ("..." if len(title) > 38 else ""),
                "Chars": page_data["char_count"],
                "Lines": page_data["line_count"],
                "Qualifying (>=5)": f"{qualifying_patterns}/7",
                "Counts": pattern_counts
            })

            print(f"  -> Saved {snapshot_path.name} ({len(text)} chars, {len(text.splitlines())} lines)")
            print(f"  -> Counts: {pattern_counts}")
            print(f"  -> Qualifying patterns with >= 5 matches: {qualifying_patterns}/7")

            if qualifying_patterns < 3:
                print(f"  WARNING: Page {page_id} yielded fewer than 5 matches for 3+ patterns!", file=sys.stderr)

        except Exception as e:
            print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
            raise

    # Write sources.json
    sources_json_path = pages_dir / "sources.json"
    sources_json_path.write_text(json.dumps(sources_metadata, indent=2), encoding="utf-8")
    print(f"\nMetadata written to {sources_json_path}")

    # Print summary table
    print("\n" + "=" * 90)
    print("SNAPSHOT COLLECTION SUMMARY")
    print("=" * 90)
    headers = ["ID", "Category", "Chars", "Lines", "Qual (>=5)", "Email", "Mobile", "Date", "URL", "Hash", "Time", "-ing"]
    print(f"{headers[0]:<6} | {headers[1]:<14} | {headers[2]:<7} | {headers[3]:<6} | {headers[4]:<10} | {headers[5]:<5} | {headers[6]:<6} | {headers[7]:<5} | {headers[8]:<5} | {headers[9]:<5} | {headers[10]:<5} | {headers[11]:<5}")
    print("-" * 90)
    for row in summary_rows:
        cnt = row["Counts"]
        print(f"{row['Page']:<6} | {row['Category']:<14} | {row['Chars']:<7} | {row['Lines']:<6} | {row['Qualifying (>=5)']:<10} | {cnt.get('email', 0):<5} | {cnt.get('mobile', 0):<6} | {cnt.get('date', 0):<5} | {cnt.get('url', 0):<5} | {cnt.get('hashtag', 0):<5} | {cnt.get('time', 0):<5} | {cnt.get('ing_word', 0):<5}")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    collect()
