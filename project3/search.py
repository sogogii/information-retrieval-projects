import os
import json
import math
import re
import time
from nltk.stem import PorterStemmer

# CONFIGURATION
INDEX_DIR        = "index_output"
FINAL_INDEX      = os.path.join(INDEX_DIR, "final_index.txt")
URL_MAP_FILE     = os.path.join(INDEX_DIR, "url_map.json")
SEEK_INDEX_FILE  = os.path.join(INDEX_DIR, "seek_index.json")
DOC_LENGTHS_FILE = os.path.join(INDEX_DIR, "doc_lengths.json")

# GLOBALS
stemmer     = PorterStemmer()
url_map     = {}
seek_index  = {}
doc_lengths = {}
total_docs  = 0

# TOKENIZER
def tokenize(text: str) -> list[str]:
    tokens = re.findall(r'[a-zA-Z0-9]+', text.lower())
    return [stemmer.stem(t) for t in tokens]


def generate_bigrams(tokens: list[str]) -> list[str]:
    """Generate 2-gram tokens the same way the indexer does."""
    return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]

# SEEK INDEX
def build_seek_index() -> dict[str, int]:
    print("Building seek index (one-time setup, ~30s)...")
    seek = {}
    with open(FINAL_INDEX, 'rb') as f:
        while True:
            offset = f.tell()
            line = f.readline()
            if not line:
                break
            token = line.split(b'\t', 1)[0].decode('utf-8')
            seek[token] = offset
    with open(SEEK_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(seek, f)
    print(f"  Seek index built: {len(seek):,} tokens")
    return seek


def build_doc_lengths() -> dict[str, float]:
    """Compute L2 norm of each document's tf weights for cosine normalization."""
    print("Building doc lengths...")
    lengths: dict[int, float] = {}
    with open(FINAL_INDEX, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if '\t' not in line:
                continue
            _, postings_str = line.split('\t', 1)
            for entry in postings_str.split(','):
                try:
                    doc_id_str, tf_str = entry.split(':')
                    doc_id = int(doc_id_str)
                    tf = int(tf_str)
                    lengths[doc_id] = lengths.get(doc_id, 0.0) + (1 + math.log10(tf)) ** 2
                except ValueError:
                    continue
    lengths = {str(k): math.sqrt(v) for k, v in lengths.items()}
    with open(DOC_LENGTHS_FILE, 'w', encoding='utf-8') as f:
        json.dump(lengths, f)
    print(f"  Doc lengths built: {len(lengths):,} documents")
    return lengths

# POSTING LOOKUP
def get_postings(token: str, f) -> dict[int, int]:
    if token not in seek_index:
        return {}
    f.seek(seek_index[token])
    line = f.readline().decode('utf-8', errors='ignore').rstrip('\n')
    try:
        _, postings_str = line.split('\t', 1)
    except ValueError:
        return {}
    postings = {}
    for entry in postings_str.split(','):
        try:
            doc_id_str, tf_str = entry.split(':')
            postings[int(doc_id_str)] = int(tf_str)
        except ValueError:
            continue
    return postings

# SCORING
def tfidf(tf: int, df: int) -> float:
    if tf == 0 or df == 0:
        return 0.0
    return (1 + math.log10(tf)) * math.log10(total_docs / df)


def url_boost(doc_id: int, tokens: list[str]) -> float:
    url = url_map.get(str(doc_id), url_map.get(doc_id, "")).lower()
    return sum(3.0 for t in tokens if t in url)


def url_penalty(doc_id: int) -> float:
    """ Penalize URLs that tend to produce low-quality results"""
    url = url_map.get(str(doc_id), url_map.get(doc_id, "")).lower()
    penalty = 0.0

    if 'archive.ics.uci.edu/ml/machine-learning-databases' in url:
        penalty += 0.6  # raw ML dataset directories, not informative
    if url.endswith('.txt'):
        penalty += 0.4  # plain text files rarely the best result
    if '/tsld' in url or '/sld0' in url:
        penalty += 0.5  # auto-generated slide pages
    if 'presentations' in url and url.endswith('.htm'):
        penalty += 0.3  # old PowerPoint HTML exports
    if url.endswith('.ff') or url.endswith('.bib'):
        penalty += 0.3  # bibliography/data files

    return penalty


def cosine_normalize(score: float, doc_id: int) -> float:
    length = doc_lengths.get(str(doc_id), doc_lengths.get(doc_id, 1.0))
    return score / length if length else score

# SEARCH
def search(query: str, top_k: int = 10) -> list[tuple[float, str]]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    # Deduplicate tokens
    seen = set()
    unique_tokens = []
    for t in query_tokens:
        if t not in seen:
            seen.add(t)
            unique_tokens.append(t)

    # Generate bigrams from query tokens
    query_bigrams = generate_bigrams(query_tokens)

    with open(FINAL_INDEX, 'rb') as f:
        all_postings = []
        doc_freqs    = []
        for token in unique_tokens:
            postings = get_postings(token, f)
            all_postings.append(postings)
            doc_freqs.append(len(postings))

        bigram_postings = []
        for bigram in query_bigrams:
            bp = get_postings(bigram, f)
            if bp:
                bigram_postings.append((bp, len(bp)))

    # Sort by posting list size 
    paired = sorted(zip(all_postings, doc_freqs), key=lambda x: x[1])
    all_postings = [p for p, _ in paired]
    doc_freqs    = [d for _, d in paired]

    # Hard Boolean AND
    non_empty = [p for p in all_postings if p]
    if non_empty:
        candidate_docs = set(non_empty[0].keys())
        for postings in non_empty[1:]:
            candidate_docs &= set(postings.keys())
    else:
        candidate_docs = set()

    # Fallback: partial match using 2 rarest terms
    if not candidate_docs:
        rare = sorted(
            [(p, d) for p, d in zip(all_postings, doc_freqs) if p],
            key=lambda x: x[1]
        )[:2]
        for postings, _ in rare:
            candidate_docs |= set(postings.keys())

    if not candidate_docs:
        return []

    # Score candidates
    scores = {}
    for doc_id in candidate_docs:
        score = 0.0
        for postings, df in zip(all_postings, doc_freqs):
            tf = postings.get(doc_id, 0)
            if df > 0:
                score += tfidf(tf, df)
        

        for bp, df in bigram_postings:
            tf = bp.get(doc_id, 0)
            if tf > 0 and df > 0:
                score += tfidf(tf, df) * 1.5  # bigram match worth 1.5x
        score += url_boost(doc_id, unique_tokens)
        score -= url_penalty(doc_id)
        score  = cosine_normalize(score, doc_id)
        scores[doc_id] = score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [(score, url_map.get(str(doc_id), url_map.get(doc_id, "Unknown")))
            for doc_id, score in ranked]

# STARTUP
def load_resources():
    global url_map, seek_index, doc_lengths, total_docs

    if not os.path.exists(FINAL_INDEX):
        print(f"ERROR: Index not found at '{FINAL_INDEX}'. Run indexer.py first.")
        exit(1)

    print("Loading URL map...")
    with open(URL_MAP_FILE, 'r', encoding='utf-8') as f:
        url_map = json.load(f)
    total_docs = len(url_map)
    print(f"  {total_docs:,} documents")

    if os.path.exists(SEEK_INDEX_FILE):
        print("Loading seek index...")
        with open(SEEK_INDEX_FILE, 'r', encoding='utf-8') as f:
            seek_index = json.load(f)
        print(f"  {len(seek_index):,} tokens")
    else:
        seek_index = build_seek_index()

    if os.path.exists(DOC_LENGTHS_FILE):
        print("Loading doc lengths...")
        with open(DOC_LENGTHS_FILE, 'r', encoding='utf-8') as f:
            doc_lengths = json.load(f)
    else:
        doc_lengths = build_doc_lengths()

    print("\nSearch engine ready!\n")



# MAIN — console interface
def main():
    load_resources()

    print("=" * 55)
    print("  CS 121 Search Engine (M3)")
    print("  Type 'quit' to exit")
    print("=" * 55)

    while True:
        try:
            query = input("\nEnter query: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in ('quit', 'exit', 'q'):
            print("Goodbye!")
            break

        start = time.time()
        results = search(query, top_k=10)
        elapsed_ms = (time.time() - start) * 1000

        print(f"\nTop results for '{query}' ({elapsed_ms:.1f}ms):")
        print("-" * 55)

        if not results:
            print("  No results found.")
        else:
            for rank, (score, url) in enumerate(results, 1):
                print(f"  {rank}. {url}")
                print(f"     Score: {score:.4f}")


if __name__ == '__main__':
    main()