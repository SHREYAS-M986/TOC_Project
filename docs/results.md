# Experimental Benchmark & Comparative Analysis Results

*Auto-generated on 2026-11-05 22:34:02*

## 1. Execution Performance (RE vs DFA across 500 Iterations)

| Target Corpus | Size (Chars) | RE Count | DFA Count | Match Sets Identical | RE Mean (μs) | RE Median (μs) | DFA Mean (μs) | DFA Median (μs) | DFA/RE Ratio |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `page1` | 27,264 | 92 | 92 | ✅ Yes | 1,747.8 | 1,685.5 | 10,433.5 | 7,323.4 | 5.97x |
| `page2` | 31,938 | 97 | 97 | ✅ Yes | 5,103.2 | 5,067.6 | 17,925.1 | 17,661.2 | 3.51x |
| `page3` | 18,835 | 92 | 92 | ✅ Yes | 2,955.8 | 2,696.3 | 10,610.8 | 10,512.5 | 3.59x |
| `synthetic_1mb` | 1,014,507 | 3653 | 3653 | ✅ Yes | 166,324.6 | 166,837.6 | 337,513.5 | 259,135.6 | 2.03x |

### Detailed Timing Statistics (μs):

| Target | RE Min | RE Max | RE StdDev | DFA Min | DFA Max | DFA StdDev |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `page1` | 1594.0 | 3281.8 | 201.9 | 6276.5 | 27285.7 | 4250.1 |
| `page2` | 3215.6 | 7424.6 | 752.8 | 13744.1 | 23590.8 | 1593.2 |
| `page3` | 1796.8 | 5589.4 | 610.5 | 7628.6 | 18392.7 | 1060.5 |
| `synthetic_1mb` | 135914.3 | 258512.4 | 11696.1 | 245207.0 | 622110.7 | 131527.9 |

---

## 2. Implementation Complexity & Lines of Code (LOC)

| Paradigm | Implementation Component | Files Involved | Non-Blank Non-Comment LOC | Implementation Notes |
|---|---|---|:---:|---|
| **Python Regular Expression (RE)** | Pattern Spec + Scanner Hook | `core/patterns.py`, `core/re_engine.py` | **28** | Concise, declarative expression leveraging Python's internal C-based PCRE engine. |
| **Hand-Built DFA Engine** | State Matrix + Char Classifier + Scanner | `core/dfa_definition.py`, `core/dfa_engine.py` | **400** | Pure table-driven algorithmic simulation without external or standard regex dependencies. |

---

## 3. Accuracy Evaluation on Hand-Labelled Ground Truth (48 Test Cases)

| Engine | Total Test Cases | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | F1-Score |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **RE Engine** | 48 | 37 | 0 | 0 | **100.00%** | **100.00%** | **1.0000** |
| **DFA Engine** | 48 | 37 | 0 | 0 | **100.00%** | **100.00%** | **1.0000** |

---

## 4. Cross-Page Pattern Frequency & Density Distribution

| Page ID | Category | Pattern Name | Count | Unique | Density (per 1,000 Chars) |
|---|---|---|:---:|:---:|:---:|
| `page1` | Educational | Email Address | 5 | 5 | 0.183 |
| `page1` | Educational | Indian Mobile Number | 0 | 0 | 0.000 |
| `page1` | Educational | Date (DD-MM-YYYY) | 8 | 7 | 0.293 |
| `page1` | Educational | Web URL | 133 | 127 | 4.878 |
| `page1` | Educational | Hashtag | 0 | 0 | 0.000 |
| `page1` | Educational | 24-Hour Time (HH:MM) | 0 | 0 | 0.000 |
| `page1` | Educational | Words ending in 'ing' | 92 | 31 | 3.374 |
| `page2` | News Portal | Email Address | 4 | 4 | 0.125 |
| `page2` | News Portal | Indian Mobile Number | 5 | 5 | 0.157 |
| `page2` | News Portal | Date (DD-MM-YYYY) | 0 | 0 | 0.000 |
| `page2` | News Portal | Web URL | 280 | 190 | 8.767 |
| `page2` | News Portal | Hashtag | 0 | 0 | 0.000 |
| `page2` | News Portal | 24-Hour Time (HH:MM) | 2 | 2 | 0.063 |
| `page2` | News Portal | Words ending in 'ing' | 97 | 65 | 3.037 |
| `page3` | Tech Blog / Community | Email Address | 0 | 0 | 0.000 |
| `page3` | Tech Blog / Community | Indian Mobile Number | 0 | 0 | 0.000 |
| `page3` | Tech Blog / Community | Date (DD-MM-YYYY) | 0 | 0 | 0.000 |
| `page3` | Tech Blog / Community | Web URL | 86 | 50 | 4.566 |
| `page3` | Tech Blog / Community | Hashtag | 63 | 19 | 3.345 |
| `page3` | Tech Blog / Community | 24-Hour Time (HH:MM) | 0 | 0 | 0.000 |
| `page3` | Tech Blog / Community | Words ending in 'ing' | 92 | 38 | 4.885 |

### Domain Category Justifications:

- **Educational (page1)**: Characterized by high URL density (4.88 per 1k) and formal communication notices (Email: 5). Dates (8) reflect administrative notifications and circular issuance schedules. Has zero mobile numbers and zero hashtags due to institutional publication guidelines.
- **News Portal (page2)**: Dominated by contact directory details (Mobile: 5, Email: 4) and navigation links (URLs: 280, density 8.77 per 1k). Contains timestamped publishing records (Time: 2) capturing editorial timestamps. High frequency of '-ing' words (97) due to narrative journalistic reporting of ongoing events.
- **Tech Blog (page3)**: Exhibits overwhelming hashtag density (63 tags, 3.34 per 1k) representing folksonomy tagging systems (#python, #webdev, #ai). Features low date/time counts, with high URL references (86) to open-source GitHub repositories and technical documentation.
