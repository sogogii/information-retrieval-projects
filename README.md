# CS 121 / INF 141 — Information Retrieval Projects

UCI Computer Science · CS 121 / INF 141

A collection of three assignments building progressively toward a complete search engine: text processing, web crawling, and full-text search.

---

## Repository Structure

```
├── project1/       # Assignment 1 — Text Processing & Tokenization
├── project2/       # Assignment 2 — Multithreaded Web Crawler
└── project3/       # Assignment 3 — Inverted Index & Search Engine
```

---

## Assignment 1 — Text Processing

**Files:** `project1/PartA.py`, `project1/PartB.py`

Implements a tokenizer and word frequency counter from scratch.

- **Part A** — Tokenizes a text file and prints word frequencies in descending order
- **Part B** — Counts common tokens between two text files

### Usage

```bash
# Part A: word frequencies
python PartA.py <text_file>

# Part B: common token count between two files
python PartB.py <file1> <file2>
```

---

## Assignment 2 — Web Crawler

**Files:** `project2/`

A multithreaded web crawler targeting UCI academic domains (`*.ics.uci.edu`, `*.cs.uci.edu`, `*.informatics.uci.edu`, `*.stat.uci.edu`).

### Features

- **Multithreaded** — Up to 4 concurrent worker threads
- **Politeness** — 500ms minimum delay per domain, enforced across threads with `RLock`
- **Trap detection** — Blocks deep paths, calendar/date patterns, repeating path segments, DokuWiki traps, high pagination
- **Duplicate detection** — Exact hash + Jaccard shingling (near-duplicate detection)
- **Analytics report** — Unique pages, longest page, 50 most common words, subdomain breakdown

### Setup

```bash
cd project2
pip install -r packages/requirements.txt

# Edit config.ini and set your USERAGENT to your student IDs
# Then run:
python launch.py
```

The crawler automatically saves a report to `crawler_report.txt` after finishing.

### Configuration (`config.ini`)

| Setting       | Description                                          |
| ------------- | ---------------------------------------------------- |
| `USERAGENT`   | Student IDs separated by commas (required)           |
| `SEEDURL`     | Comma-separated seed URLs                            |
| `POLITENESS`  | Delay in seconds between requests to the same domain |
| `THREADCOUNT` | Number of parallel worker threads (max 4)            |

---

## Assignment 3 — Search Engine

**Files:** `project3/`

A full-text search engine with an inverted index, TF-IDF ranking, and multiple front-ends.

### Features

- **Inverted index** — Disk-based with partial index flushing and merge
- **Stemming** — Porter Stemmer via NLTK
- **Bigram indexing** — Indexes consecutive word pairs for phrase-like matching
- **Important tag boosting** — Extra weight for terms in `<title>`, `<h1>`–`<h3>`, `<b>`, `<strong>`
- **Duplicate detection** — MD5 exact hash + SimHash near-duplicate detection (Hamming distance ≤ 4)
- **Seek index** — Maps tokens to byte offsets for fast disk lookup (no full index loaded into memory)
- **TF-IDF scoring** — With cosine normalization, URL boosts, and URL penalties
- **Bigram query boosting** — Bigram matches scored at 1.5× weight
- **Multiple front-ends** — Console, Flask web app, and Tkinter GUI

### Setup

```bash
cd project3
pip install -r requirements.txt

# One-time NLTK setup
python setup.py

# Build the index (corpus must be in project3/developer/)
python indexer.py
```

### Running the Search Engine

```bash
# Console interface
python search.py

# Web interface (http://localhost:5000)
python search_web.py

# Desktop GUI
python search_gui.py
```

### Index Files (generated in `index_output/`)

| File               | Description                                   |
| ------------------ | --------------------------------------------- |
| `final_index.txt`  | Merged inverted index (`token\tpostings`)     |
| `url_map.json`     | Maps doc IDs to URLs                          |
| `seek_index.json`  | Token → byte offset for fast lookup           |
| `doc_lengths.json` | Per-document L2 norm for cosine normalization |
| `report_stats.txt` | Index statistics summary                      |

### Search Architecture

```
Query
  → tokenize + stem
  → generate bigrams
  → seek index lookup (per token/bigram)
  → Boolean AND intersection (with partial-match fallback)
  → TF-IDF + bigram boost + URL boost/penalty
  → cosine normalize
  → top-k results
```

---

## Notes

- The corpus directory must be at `project3/developer/` (relative path)
- The index delimiter between token and postings is `\t` (tab)
- Run `indexer.py` before any search interface
- The seek index and doc lengths are built automatically on first search if missing
