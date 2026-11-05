"""Automated Browser Verification and Screenshot Capture Script for Stage 2.

Exercises all 5 UI tabs using headless Microsoft Edge via Playwright,
runs extraction, cross-page analysis, DFA interactive simulation, and
RE vs DFA benchmarking. Captures screenshots into docs/screenshots/.
"""

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not Path(EDGE_PATH).exists():
    EDGE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"


def capture_cli_outputs():
    """Capture terminal output from both RE and DFA CLIs into text files."""
    print("Capturing CLI outputs...")
    py = sys.executable

    # RE CLI
    cmd_re = [py, "-m", "core.re_engine", "--page", "1"]
    res_re = subprocess.run(
        cmd_re, cwd=str(PROJECT_ROOT), capture_output=True, text=True
    )
    out_re = res_re.stdout + res_re.stderr
    (SCREENSHOTS_DIR / "cli_re_engine.txt").write_text(out_re, encoding="utf-8")
    print("  -> Saved cli_re_engine.txt")

    # DFA CLI
    cmd_dfa = [py, "-m", "core.dfa_engine", "--page", "1"]
    res_dfa = subprocess.run(
        cmd_dfa, cwd=str(PROJECT_ROOT), capture_output=True, text=True
    )
    out_dfa = res_dfa.stdout + res_dfa.stderr
    (SCREENSHOTS_DIR / "cli_dfa_engine.txt").write_text(out_dfa, encoding="utf-8")
    print("  -> Saved cli_dfa_engine.txt")


def run_browser_verification():
    """Launch headless browser, exercise all UI tabs, and capture screenshots."""
    # Ensure Flask server is running
    server_proc = None
    try:
        import urllib.request

        urllib.request.urlopen("http://127.0.0.1:5000/api/health", timeout=1)
        print("Existing Flask server detected on port 5000.")
    except Exception:
        print("Starting background Flask server on port 5000...")
        server_proc = subprocess.Popen(
            [sys.executable, "api/index.py"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)

    print(f"Launching browser from: {EDGE_PATH}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # Listen for console errors
        console_errors = []
        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        print("Navigating to http://127.0.0.1:5000/ ...")
        page.goto("http://127.0.0.1:5000/", wait_until="networkidle")
        time.sleep(1)

        # ------------------------------------------------------------------
        # 1. TAB 1: ANALYZER (PAGE 1)
        # ------------------------------------------------------------------
        print("1. Exercising Tab 1: Analyzer...")
        page.wait_for_selector("#analyzer-results", state="visible", timeout=10000)
        time.sleep(1)
        shot1 = SCREENSHOTS_DIR / "01_analyzer_page1.png"
        page.screenshot(path=str(shot1), full_page=False)
        print(f"  -> Captured: {shot1.name}")

        # Exercise Page 2 & Page 3 on Analyzer
        page.click('.snapshot-card-item[data-page-id="page2"]')
        page.click("#btn-run-analysis")
        time.sleep(1)
        shot1b = SCREENSHOTS_DIR / "01b_analyzer_page2.png"
        page.screenshot(path=str(shot1b), full_page=False)
        print(f"  -> Captured: {shot1b.name}")

        page.click('.snapshot-card-item[data-page-id="page3"]')
        page.click("#btn-run-analysis")
        time.sleep(1)
        shot1c = SCREENSHOTS_DIR / "01c_analyzer_page3.png"
        page.screenshot(path=str(shot1c), full_page=False)
        print(f"  -> Captured: {shot1c.name}")

        page.click('.snapshot-card-item[data-page-id="page1"]')
        page.click("#btn-run-analysis")
        time.sleep(1)

        # ------------------------------------------------------------------
        # 2. TAB 2: CROSS-PAGE COMPARISON
        # ------------------------------------------------------------------
        print("2. Exercising Tab 2: Cross-Page Comparison...")
        page.click("#tab-btn-comparison")
        page.wait_for_selector("#cross-page-chart", state="visible", timeout=10000)
        time.sleep(1.5)  # Allow Chart.js animation
        shot2 = SCREENSHOTS_DIR / "02_cross_page.png"
        page.screenshot(path=str(shot2), full_page=False)
        print(f"  -> Captured: {shot2.name}")

        # ------------------------------------------------------------------
        # 3. TAB 3: DFA MACHINE & SIMULATOR
        # ------------------------------------------------------------------
        print("3. Exercising Tab 3: DFA Machine & Diagram...")
        page.click("#tab-btn-dfa")
        page.wait_for_selector("#interactive-dfa-svg", state="visible", timeout=10000)
        time.sleep(1)
        shot3 = SCREENSHOTS_DIR / "03_dfa_diagram.png"
        page.screenshot(path=str(shot3), full_page=False)
        print(f"  -> Captured: {shot3.name}")

        # Run Simulator on "learning"
        print("   Running Simulator on 'learning'...")
        page.fill("#simulator-word-input", "learning")
        page.click("#btn-sim-play")
        time.sleep(5)  # Wait for animation to finish (8 steps @ 500ms = 4s)

        shot4 = SCREENSHOTS_DIR / "04_dfa_simulator.png"
        page.screenshot(path=str(shot4), full_page=False)
        print(f"  -> Captured: {shot4.name}")

        # Also test "string" and "ing"
        page.click('.chip-btn[data-word="string"]')
        page.click("#btn-sim-step")
        time.sleep(0.5)
        page.click('.chip-btn[data-word="ing"]')
        page.click("#btn-sim-play")
        time.sleep(2.5)

        # ------------------------------------------------------------------
        # 4. TAB 4: RE VS DFA COMPARISON
        # ------------------------------------------------------------------
        print("4. Exercising Tab 4: RE vs DFA Comparison...")
        page.click("#tab-btn-compare")
        page.click("#btn-run-compare")
        page.wait_for_selector(
            "#compare-equivalence-banner", state="visible", timeout=10000
        )
        time.sleep(2)  # Allow Chart.js charts to finish render
        shot5 = SCREENSHOTS_DIR / "05_compare.png"
        page.screenshot(path=str(shot5), full_page=False)
        print(f"  -> Captured: {shot5.name}")

        # ------------------------------------------------------------------
        # 5. TAB 5: ABOUT & TEST CASES
        # ------------------------------------------------------------------
        print("5. Exercising Tab 5: About & Test Cases...")
        page.click("#tab-btn-about")
        page.wait_for_selector(
            "#testcases-table-body tr", state="visible", timeout=10000
        )
        time.sleep(1)
        shot6 = SCREENSHOTS_DIR / "06_testcases.png"
        page.screenshot(path=str(shot6), full_page=False)
        print(f"  -> Captured: {shot6.name}")

        # ------------------------------------------------------------------
        # 6. MOBILE RESPONSIVE TEST (375px viewport)
        # ------------------------------------------------------------------
        print("6. Capturing Mobile Responsive (375px)...")
        mobile_page = context.new_page()
        mobile_page.set_viewport_size({"width": 375, "height": 667})
        mobile_page.goto("http://127.0.0.1:5000/", wait_until="networkidle")
        time.sleep(1)
        shot7 = SCREENSHOTS_DIR / "07_mobile_analyzer_375px.png"
        mobile_page.screenshot(path=str(shot7), full_page=False)
        print(f"  -> Captured: {shot7.name}")
        mobile_page.close()

        # Check console errors
        if console_errors:
            print(f"WARNING: Browser console reported errors: {console_errors}")
        else:
            print("Browser console clean (0 errors).")

        browser.close()
        print("Browser verification and screenshot capture completed successfully.")

    if server_proc:
        server_proc.terminate()


def main():
    capture_cli_outputs()
    run_browser_verification()


if __name__ == "__main__":
    main()
