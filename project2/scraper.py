import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup

# Helper function from Assignment 1 tokenizer 
def _is_ascii_alnum(ch: str) -> bool:
    """
    Check if a character is ASCII alphanumeric.
    From Assignment 1 PartA.py
    Time: O(1). Space: O(1).
    """
    o = ord(ch)
    return (48 <= o <= 57) or (65 <= o <= 90) or (97 <= o <= 122)


def normalize_text(text):
    """
    Lowercase and split text into words
    """
    return text.lower().split()


def exact_hash(text):
    """
    Exact duplicate detection using hashing
    """
    return hash(text)


def get_shingles(words, k=5):
    """
    Generate k-word shingles
    """
    shingles = set()
    if len(words) < k:
        return shingles

    for i in range(len(words) - k + 1):
        shingles.add(tuple(words[i:i+k]))
    return shingles


def jaccard_similarity(s1, s2):
    """
    Jaccard similarity between two shingle sets
    """
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


# Global data structures
unique_pages = set()  # Store unique URLs (without fragments)
word_counts = {}  # Store word count for each page
all_words = {}  # Store frequency of all words across pages
subdomains = {}  # Store count of pages per subdomain
longest_page = {"url": "", "word_count": 0}  # Track the longest page

SEEN_HASHES = set()
SEEN_SHINGLES = []   # list of sets

STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are',
    "aren't", 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both',
    'but', 'by', "can't", 'cannot', 'could', "couldn't", 'did', "didn't", 'do', 'does', "doesn't",
    'doing', "don't", 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', "hadn't",
    'has', "hasn't", 'have', "haven't", 'having', 'he', "he'd", "he'll", "he's", 'her', 'here',
    "here's", 'hers', 'herself', 'him', 'himself', 'his', 'how', "how's", 'i', "i'd", "i'll",
    "i'm", "i've", 'if', 'in', 'into', 'is', "isn't", 'it', "it's", 'its', 'itself', "let's", 'me',
    'more', 'most', "mustn't", 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once',
    'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same',
    "shan't", 'she', "she'd", "she'll", "she's", 'should', "shouldn't", 'so', 'some', 'such',
    'than', 'that', "that's", 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there',
    "there's", 'these', 'they', "they'd", "they'll", "they're", "they've", 'this', 'those',
    'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', "wasn't", 'we', "we'd",
    "we'll", "we're", "we've", 'were', "weren't", 'what', "what's", 'when', "when's", 'where',
    "where's", 'which', 'while', 'who', "who's", 'whom', 'why', "why's", 'with', "won't", 'would',
    "wouldn't", 'you', "you'd", "you'll", "you're", "you've", 'your', 'yours', 'yourself', 'yourselves'
}

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    links = []
    
    # Check if the response is valid (status 200 = OK)
    if resp.status != 200:
        print(f"Skipping {url} - Status: {resp.status}")
        return links
    
    # Check if response has content
    if not resp.raw_response or not resp.raw_response.content:
        print(f"Skipping {url} - No content")
        return links
    
    try:
        # Get the HTML content
        html_content = resp.raw_response.content
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text content for analytics
        text = soup.get_text()

        normalized_words = normalize_text(text)

        page_hash = exact_hash(text)
        if page_hash in SEEN_HASHES:
            return []   # exact duplicate → skip page
        SEEN_HASHES.add(page_hash)

        page_shingles = get_shingles(normalized_words, k=5)
        for old_shingles in SEEN_SHINGLES:
            if jaccard_similarity(page_shingles, old_shingles) > 0.9:
                print(f"[SIMILARITY] Near-duplicate skipped: {url}")
                return []   # near duplicate → skip page

        SEEN_SHINGLES.append(page_shingles)
        
        words = []
        token_chars = []
        for ch in text:
            if _is_ascii_alnum(ch):
                token_chars.append(ch.lower())
            else:
                if token_chars:
                    words.append("".join(token_chars))
                    token_chars = []
        if token_chars:
            words.append("".join(token_chars))
        
        # Filter out stop words
        total_word_count = len(words)  # For Q2 (longest page)
        filtered_words = [word for word in words if word not in STOP_WORDS]
        
        # Skip pages with very low word count
        if total_word_count < 50:
            print(f"Low word count {url}: {total_word_count} words (still extracting {len(links)} links)")
            return links  # Return links but skip analytics
                
        # Defragment the URL for uniqueness check
        defrag_url, _ = urldefrag(url)
        
        # Track analytics for the report
        if defrag_url not in unique_pages:
            unique_pages.add(defrag_url)
            
            # Track word count for this page
            word_counts[defrag_url] = total_word_count
            
            # Update longest page if this one is longer
            if total_word_count > longest_page["word_count"]:  # Use total_word_count
                longest_page["url"] = defrag_url
                longest_page["word_count"] = total_word_count  # Use total_word_count
            
            # Count word frequencies for common words report
            for word in filtered_words:
                all_words[word] = all_words.get(word, 0) + 1
            
            # Track subdomains
            parsed = urlparse(defrag_url)
            if parsed.netloc:
                netloc_lower = parsed.netloc.lower()
                if netloc_lower.endswith(".uci.edu") or netloc_lower == "uci.edu":
                    subdomains[netloc_lower] = subdomains.get(netloc_lower, 0) + 1
        
        # Extract all links from the page
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(url, href)
            
            # Defragment the URL (remove #fragments)
            absolute_url, _ = urldefrag(absolute_url)
            
            # Add to links list (will be filtered by is_valid later)
            links.append(absolute_url)
        
        print(f"Scraped {url} - Found {len(links)} links, {total_word_count} words")
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    
    return links

def is_valid(url):
    """
    Decide whether to crawl this url or not. 
    If you decide to crawl it, return True; otherwise return False.
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme is http or https
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        # DOMAIN VALIDATION
        allowed_domains = [
            ".ics.uci.edu",
            ".cs.uci.edu",
            ".informatics.uci.edu",
            ".stat.uci.edu"
        ]
        
        netloc_lower = parsed.netloc.lower()
        
        # Check if the domain matches any of the allowed domains
        domain_match = any(
            netloc_lower.endswith(domain) or netloc_lower == domain[1:]
            for domain in allowed_domains
        )
        
        if not domain_match:
            return False

        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            return False

        # TRAP DETECTION - Avoid infinite crawling loops
        
        # 1. Avoid very deep paths
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) > 10:
            return False
        
        # 2. Avoid calendar/date traps in query parameters
        if parsed.query:
            query_lower = parsed.query.lower()
            # Common trap patterns in query strings
            trap_patterns = [
                'calendar', 'date=', 'year=', 'month=', 'day=',
                'share=', 'replytocom=', 'filter=date'
            ]
            if any(pattern in query_lower for pattern in trap_patterns):
                return False

        # 2b. Avoid calendar/date traps in URL PATH
        path_lower = parsed.path.lower()
        if any(p in path_lower for p in ['/day/', '/month/', '/year/', '/calendar/']):
            return False

        if '/day/' in path_lower:
            return False

        if re.search(r'/\d{4}[-/]\d{2}([-/]\d{2})?', path_lower):
            return False

        query_lower = parsed.query.lower()
        if 'ical' in query_lower or 'outlook-ical' in query_lower:
            return False
  
        # 3. Avoid repeating path segments
        if len(path_parts) > 2:
            unique_parts = len(set(path_parts))
            total_parts = len(path_parts)
            if unique_parts < total_parts / 2:
                return False

        # Block high pagination numbers in PATH
        if '/page/' in parsed.path.lower():
            page_match = re.search(r'/page/(\d+)', parsed.path.lower())
            if page_match and int(page_match.group(1)) > 20:
                return False

        # Block DokuWiki storage/media traps
        if "wiki.ics.uci.edu" in parsed.netloc and "doku.php" in parsed.path:
            return False
            
        # Block WordPress login redirects
        if "wp-login.php" in parsed.path.lower():
            return False

        if "redirect_to=" in parsed.query.lower():
            return False
        
        return True

    except TypeError:
        print("TypeError for", parsed)
        raise

def save_report():
    """
    Save the analytics report to a file.
    Call this function after crawling is complete to generate the report.
    
    Usage:
    >>> from scraper import save_report
    >>> save_report()
    """
    with open('crawler_report.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("WEB CRAWLER ANALYTICS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        # Question 1: Number of unique pages
        f.write(f"1. Number of unique pages found: {len(unique_pages)}\n\n")
        
        # Question 2: Longest page (using total word count including stop words)
        f.write(f"2. Longest page (by word count):\n")
        f.write(f"   URL: {longest_page['url']}\n")
        f.write(f"   Word count: {longest_page['word_count']}\n\n")
        
        # Question 3: 50 most common words (with alphabetical tie-break)
        f.write("3. 50 Most common words (excluding stop words):\n")
        # Sort by frequency (descending), then alphabetically for ties
        sorted_words = sorted(all_words.items(), key=lambda kv: (-kv[1], kv[0]))
        for i, (word, count) in enumerate(sorted_words[:50], 1):
            f.write(f"   {word}, {count}\n")
        f.write("\n")
        
        # Question 4: Subdomains
        f.write("4. Subdomains in uci.edu domain:\n")
        f.write(f"   Total subdomains found: {len(subdomains)}\n\n")
        sorted_subdomains = sorted(subdomains.items())
        for subdomain, count in sorted_subdomains:
            f.write(f"   {subdomain}, {count}\n")
    
    print(f"\n{'='*80}")
    print("REPORT SAVED!")
    print(f"{'='*80}")
    print(f"Report saved to: crawler_report.txt")
    print(f"Total unique pages: {len(unique_pages)}")
    print(f"Total subdomains: {len(subdomains)}")
    print(f"Longest page: {longest_page['url']} ({longest_page['word_count']} words)")
    print(f"{'='*80}\n")