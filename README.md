# Web Content Analyzer: RE vs DFA

A full-stack Theory of Computation (TOC) case study application comparing **Python Regular Expressions (RE)** against a **Hand-Built Deterministic Finite Automaton (DFA)** for tokenizing and extracting structured patterns from real-world web pages.

Built in 3 development stages:
- **Stage 1 (Current):** Project skeleton, data snapshots, formal RE pattern registry & engine, secure REST API, test suite, and CI verification.
- **Stage 2 (Next):** Hand-built DFA engine, performance benchmark suite, and interactive frontend UI.
- **Stage 3 (Future):** Comprehensive TOC analytical report, comparative metrics, and cloud deployment on Vercel.

---

## 1. Project Overview & Target Patterns

The application scans web page content to recognize seven formal token languages:

| Key | Formal Token Language | Regular Expression Specification | Flags |
|---|---|---|---|
| `email` | Standard Email Address | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | None |
| `mobile` | Indian Mobile Number (10 digits) | `(?<!\d)(?:(?:\+91\|91\|0)[\s-]?)?[6-9]\d{9}(?!\d)` | None |
| `date` | Date (DD-MM-YYYY) | `\b(0[1-9]\|[12]\d\|3[01])-(0[1-9]\|1[0-2])-(19\|20)\d{2}\b` | None |
| `url` | Web URL (HTTP/HTTPS) | `https?://[^\s<>\x22\'\)]*[^\s<>\x22\'\).,;:?!]` | None |
| `hashtag` | Social Tag / Identifier | `(?<![\w#])#[A-Za-z][A-Za-z0-9_]*` | None |
| `time` | 24-Hour Clock Time (HH:MM) | `\b([01]\d\|2[0-3]):[0-5]\d\b` | None |
| `ing_word` | Words ending in '-ing' | `\b[A-Za-z]+ing\b` | `re.IGNORECASE` |

---

## 2. Directory Structure

```text
TOC_Project/
├── api/
│   └── index.py            # Flask REST API entry point for Vercel and local server
├── core/
│   ├── __init__.py         # Package initialization
│   ├── patterns.py         # Formal pattern registry, specs, and regex explanations
│   ├── re_engine.py        # RE extraction engine, timing, and CLI reporter
│   ├── dfa_engine.py       # DFA engine stub (to be implemented in Stage 2)
│   ├── scraper.py          # Web fetcher with SSRF protection and HTML cleaner
│   └── utils.py            # Line/col calculator, timing benchmark, and LOC counter
├── data/
│   └── pages/
│       ├── page1.txt       # Cleaned text snapshot: UGC (Educational)
│       ├── page2.txt       # Cleaned text snapshot: The Indian Express (News)
│       ├── page3.txt       # Cleaned text snapshot: DEV Community (Tech Blog)
│       └── sources.json    # Metadata, category, and stats for snapshots
├── docs/                   # Diagrams, benchmarks, and TOC reports (Stages 2 & 3)
├── public/                 # Static frontend HTML/CSS/JS (Stage 2)
├── scripts/
│   ├── collect_pages.py    # Fetches snapshots from public sources and saves metadata
│   └── generate_test_cases_md.py # Generates markdown verification table
├── tests/
│   ├── test_data.py        # Positives and negatives test dataset (70 cases)
│   ├── test_re_engine.py   # Comprehensive Pytest test suite (84 tests)
│   └── test_cases.md       # Auto-generated verification matrix
├── .gitignore              # Git ignore rules
├── README.md               # Project documentation
├── requirements.txt        # Pinned Python package dependencies
└── vercel.json             # Vercel serverless functions configuration
```

---

## 3. Data Collection Snapshots

Three publicly accessible web pages representing distinct domains were collected and cleaned:

| Snapshot ID | Category | Source Title | Characters | Lines | Key Patterns Detected |
|---|---|---|---|---|---|
| `page1` | Educational | University Grants Commission (UGC) | 27,264 | 968 | Email (5), Date (8), URL (133), -ing (92) |
| `page2` | News Portal | The Indian Express (Helpline Report) | 31,938 | 783 | Mobile (5), Email (4), URL (280), Time (2), -ing (97) |
| `page3` | Tech Blog | DEV Community (Python Tag) | 18,835 | 648 | Hashtag (63), URL (86), -ing (92) |

---

## 4. Local Installation & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Git

### Steps
1. Clone the repository and enter the directory:
   ```bash
   git clone https://github.com/SHREYAS-M986/TOC_Project.git
   cd TOC_Project
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 5. Running the Application

### Running the CLI Analyzer
Analyze any page snapshot with clean ASCII table output:
```bash
python -m core.re_engine --page 1
python -m core.re_engine --page 2
python -m core.re_engine --page 3
```
Add `--benchmark` to run a 200-iteration performance benchmark per pattern.

### Starting the Flask Backend Server
```bash
python api/index.py
```
Or with Flask CLI:
```bash
flask --app api/index.py run --port 5000
```
The server will listen at `http://127.0.0.1:5000`.

---

## 6. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health status and service timestamp |
| `GET` | `/api/pages` | List of page snapshot metadata from `sources.json` |
| `GET` | `/api/pages/<id>` | Full text snapshot and metadata (`page1`, `page2`, `page3`) |
| `GET` | `/api/patterns` | Formal regular expression registry and pattern metadata |
| `POST` | `/api/analyze/re` | Analyzes text/page/URL using RE engine (`body: {page_id, text, url, patterns}`) |
| `POST` | `/api/fetch` | Live URL fetch with SSRF protection (10s timeout, 2MB max, private IP blocking) |
| `GET` | `/api/summary` | Cross-page comparison summary counts for all 7 patterns |

---

## 7. Running Tests & Verifying Test Cases

Run the test suite with `pytest`:
```bash
pytest -v
```

Regenerate the automated verification table `tests/test_cases.md`:
```bash
python scripts/generate_test_cases_md.py
```

---

## 8. Roadmap & Later Stages

- [x] **Stage 1:** Project skeleton, data snapshots, RE engine, Flask API, SSRF protection, pytest suite, Git push.
- [ ] **Stage 2:** Hand-built DFA engine (`core/dfa_engine.py`), state transition matrices, equivalence testing, execution benchmark comparison, and interactive single-page web UI (`public/`).
- [ ] **Stage 3:** Vercel deployment, empirical time complexity analysis report, LOC metrics, and TOC theoretical study comparison.
