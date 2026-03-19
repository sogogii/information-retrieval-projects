import os
import json
import heapq
import re
import time
import hashlib
import warnings
from pathlib import Path
from collections import defaultdict

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning, MarkupResemblesLocatorWarning
from nltk.stem import PorterStemmer

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# CONFIGURATION
CORPUS_DIR  = "developer"
INDEX_DIR   = "index_output"
FLUSH_THRESHOLD = 10000

FINAL_INDEX_FILE = os.path.join(INDEX_DIR, "final_index.txt")
URL_MAP_FILE     = os.path.join(INDEX_DIR, "url_map.json")
STATS_FILE       = os.path.join(INDEX_DIR, "report_stats.txt")
DUPES_FILE       = os.path.join(INDEX_DIR, "duplicates.json")

# GLOBALS
stemmer = PorterStemmer()
partial_index: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
url_map: dict[int, str] = {}
doc_id_counter    = 0
partial_index_count = 0
partial_index_files: list[str] = []

# Duplicate detection
content_hashes: dict[str, str] = {}        # md5 -> url (exact duplicates)
simhash_store: list[tuple[int, str]] = []  # (simhash, url) (near duplicates)
duplicate_count = 0

IMPORTANT_TAGS   = {'b', 'strong', 'h1', 'h2', 'h3', 'title'}
IMPORTANT_WEIGHT = 5


# TOKENIZER
def tokenize(text: str) -> list[str]:
    tokens = re.findall(r'[a-zA-Z0-9]+', text.lower())
    return [stemmer.stem(t) for t in tokens]


def generate_bigrams(tokens: list[str]) -> list[str]:
    # Generate 2-gram tokens from a list of stemmed tokens.
    return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]


# HTML PARSER
def parse_document(html_content: str) -> dict[str, int]:
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except Exception:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
        except Exception:
            return {}

    tf: dict[str, int] = defaultdict(int)

    important_text = []
    for tag in soup.find_all(IMPORTANT_TAGS):
        important_text.append(tag.get_text(separator=' '))

    all_text = soup.get_text(separator=' ')
    all_tokens = tokenize(all_text)
    for token in all_tokens:
        tf[token] += 1

    # Index 2-grams from all text
    for bigram in generate_bigrams(all_tokens):
        tf[bigram] += 1

    for text in important_text:
        imp_tokens = tokenize(text)
        for token in imp_tokens:
            tf[token] += (IMPORTANT_WEIGHT - 1)
        # Also boost bigrams in important text
        for bigram in generate_bigrams(imp_tokens):
            tf[bigram] += (IMPORTANT_WEIGHT - 1)

    return dict(tf)


# DUPLICATE DETECTION (exact + near)
def simhash(text: str) -> int:
    """
    Compute a 64-bit SimHash fingerprint of text.
    Near-duplicate pages will have very similar fingerprints
    (small Hamming distance between their bits).
    """
    tokens = re.findall(r'[a-zA-Z0-9]+', text.lower())
    v = [0] * 64
    for token in tokens:
        h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def hamming_distance(a: int, b: int) -> int:
    """Count differing bits between two SimHash fingerprints."""
    return bin(a ^ b).count('1')


# Store md5 hash -> url (exact), simhash -> url (near)
content_hashes: dict[str, str] = {}  
simhash_store: list[tuple[int, str]] = []  
NEAR_DUP_THRESHOLD = 4 


def is_duplicate(content: str, url: str) -> bool:

    global duplicate_count

    # Exact duplicate check
    content_hash = hashlib.md5(content.encode('utf-8', errors='replace')).hexdigest()
    if content_hash in content_hashes:
        duplicate_count += 1
        return True
    content_hashes[content_hash] = url

    # Near duplicate check via SimHash
    sh = simhash(content)
    for stored_sh, stored_url in simhash_store:
        if hamming_distance(sh, stored_sh) <= NEAR_DUP_THRESHOLD:
            duplicate_count += 1
            return True
    simhash_store.append((sh, url))

    return False

# PARTIAL INDEX
def flush_partial_index():
    global partial_index, partial_index_count

    if not partial_index:
        return

    partial_index_count += 1
    filepath = os.path.join(INDEX_DIR, f"partial_{partial_index_count:03d}.txt")

    with open(filepath, 'w', encoding='utf-8') as f:
        for token in sorted(partial_index.keys()):
            postings = ','.join(
                f"{doc_id}:{tf}"
                for doc_id, tf in sorted(partial_index[token].items())
            )
            f.write(f"{token}\t{postings}\n")

    partial_index_files.append(filepath)
    partial_index.clear()
    print(f"  [flush] Partial index #{partial_index_count} written → {filepath}")


# MERGE
def parse_postings_line(line: str) -> tuple[str, dict[int, int]]:
    token, postings_str = line.rstrip('\n').split('\t', 1)
    postings = {}
    for entry in postings_str.split(','):
        doc_id_str, tf_str = entry.split(':')
        postings[int(doc_id_str)] = int(tf_str)
    return token, postings


def merge_partial_indexes():
    print(f"\nMerging {len(partial_index_files)} partial indexes...")
    file_handles = [open(fp, 'r', encoding='utf-8') for fp in partial_index_files]

    heap = []
    counter = 0
    for i, fh in enumerate(file_handles):
        line = fh.readline()
        if line:
            token, postings = parse_postings_line(line)
            heapq.heappush(heap, (token, counter, postings, i))
            counter += 1

    with open(FINAL_INDEX_FILE, 'w', encoding='utf-8') as out:
        current_token   = None
        current_postings: dict[int, int] = {}

        while heap:
            token, _, postings, file_idx = heapq.heappop(heap)

            if token == current_token:
                for doc_id, tf in postings.items():
                    current_postings[doc_id] = current_postings.get(doc_id, 0) + tf
            else:
                if current_token is not None:
                    postings_str = ','.join(
                        f"{doc_id}:{tf}"
                        for doc_id, tf in sorted(current_postings.items())
                    )
                    out.write(f"{current_token}\t{postings_str}\n")
                current_token    = token
                current_postings = dict(postings)

            line = file_handles[file_idx].readline()
            if line:
                next_token, next_postings = parse_postings_line(line)
                heapq.heappush(heap, (next_token, counter, next_postings, file_idx))
                counter += 1

        if current_token is not None:
            postings_str = ','.join(
                f"{doc_id}:{tf}"
                for doc_id, tf in sorted(current_postings.items())
            )
            out.write(f"{current_token}\t{postings_str}\n")

    for fh in file_handles:
        fh.close()

    print(f"  Merge complete → {FINAL_INDEX_FILE}")


# STATS
def compute_stats():
    num_docs = len(url_map)
    unique_tokens = sum(1 for _ in open(FINAL_INDEX_FILE, 'r', encoding='utf-8'))
    index_size_kb = os.path.getsize(FINAL_INDEX_FILE) / 1024
    return num_docs, unique_tokens, index_size_kb


# MAIN INDEXING LOOP
def index_corpus():
    global doc_id_counter

    corpus_path = Path(CORPUS_DIR)
    if not corpus_path.exists():
        print(f"ERROR: Corpus directory '{CORPUS_DIR}' not found.")
        return

    os.makedirs(INDEX_DIR, exist_ok=True)

    print(f"Starting indexer on corpus: {CORPUS_DIR}")
    print(f"Flush threshold: every {FLUSH_THRESHOLD} documents\n")

    start_time = time.time()
    seen_urls  = set()

    all_json_files = list(corpus_path.rglob("*.json"))
    print(f"Found {len(all_json_files)} JSON files to index.\n")

    for json_file in all_json_files:
        try:
            with open(json_file, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
        except Exception:
            continue

        url = data.get('url', '')
        if not url:
            continue

        base_url = url.split('#')[0]
        if base_url in seen_urls:
            continue
        seen_urls.add(base_url)

        content = data.get('content', '')
        if not content:
            continue

        # Skip exact duplicates
        if is_duplicate(content, base_url):
            continue

        tf = parse_document(content)
        if not tf:
            continue

        doc_id = doc_id_counter
        url_map[doc_id] = base_url
        doc_id_counter += 1

        for token, freq in tf.items():
            partial_index[token][doc_id] += freq

        if doc_id_counter % FLUSH_THRESHOLD == 0:
            print(f"Processed {doc_id_counter} documents...")
            flush_partial_index()

    if partial_index:
        print(f"Processed {doc_id_counter} documents (final flush)...")
        flush_partial_index()

    elapsed = time.time() - start_time
    print(f"\nIndexing done in {elapsed:.1f}s — {doc_id_counter} documents processed.")
    print(f"Duplicates skipped: {duplicate_count}")
    print(f"Total partial index files: {len(partial_index_files)}")

    with open(URL_MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(url_map, f)
    print(f"URL map saved → {URL_MAP_FILE}")

    with open(DUPES_FILE, 'w', encoding='utf-8') as f:
        json.dump({"duplicates_skipped": duplicate_count}, f)

    merge_partial_indexes()

    num_docs, unique_tokens, index_size_kb = compute_stats()

    stats_text = (
        f"=== M3 Report Stats ===\n"
        f"Number of indexed documents : {num_docs:,}\n"
        f"Number of unique tokens     : {unique_tokens:,}\n"
        f"Total index size on disk    : {index_size_kb:,.1f} KB\n"
        f"Duplicate pages skipped     : {duplicate_count:,}\n"
        f"Number of partial indexes   : {len(partial_index_files)}\n"
        f"Indexing time               : {elapsed:.1f} seconds\n"
    )

    print(f"\n{stats_text}")
    with open(STATS_FILE, 'w') as f:
        f.write(stats_text)

    for fp in partial_index_files:
        os.remove(fp)
    print("Partial index files cleaned up.")


if __name__ == '__main__':
    index_corpus()