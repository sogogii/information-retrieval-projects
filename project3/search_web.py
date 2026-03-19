from flask import Flask, request, render_template_string
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import load_resources, search

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CS 121 Search Engine</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f1a;
            color: #cdd6f4;
            min-height: 100vh;
        }

        header {
            background: #7c6af7;
            padding: 18px 40px;
            display: flex;
            align-items: center;
            gap: 16px;
        }

        header h1 {
            font-size: 22px;
            font-weight: 700;
            color: white;
        }

        .search-bar {
            display: flex;
            gap: 10px;
            padding: 28px 40px 16px;
            max-width: 860px;
        }

        .search-bar input {
            flex: 1;
            padding: 12px 16px;
            border-radius: 8px;
            border: 2px solid #3d3d5c;
            background: #1e1e2e;
            color: #cdd6f4;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }

        .search-bar input:focus {
            border-color: #7c6af7;
        }

        .search-bar button {
            padding: 12px 24px;
            background: #7c6af7;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        .search-bar button:hover {
            background: #6a59e0;
        }

        .status {
            padding: 0 40px 12px;
            font-size: 13px;
            color: #6c7086;
        }

        .results {
            padding: 0 40px;
            max-width: 860px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .result-card {
            background: #1e1e2e;
            border: 1px solid #2a2a3e;
            border-radius: 10px;
            padding: 16px 20px;
            transition: border-color 0.2s;
        }

        .result-card:hover {
            border-color: #7c6af7;
        }

        .result-meta {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }

        .rank {
            color: #7c6af7;
            font-weight: 700;
            font-size: 14px;
        }

        .score {
            color: #6c7086;
            font-size: 12px;
        }

        .result-url {
            color: #89b4fa;
            font-size: 14px;
            text-decoration: none;
            word-break: break-all;
        }

        .result-url:hover {
            text-decoration: underline;
        }

        .no-results {
            padding: 40px;
            color: #6c7086;
            font-size: 15px;
        }
    </style>
</head>
<body>
    <header>
        <h1>CS 121 Search Engine</h1>
    </header>

    <form method="GET" action="/">
        <div class="search-bar">
            <input type="text" name="q" value="{{ query }}"
                   placeholder="Enter your search query..." autofocus>
            <button type="submit">Search</button>
        </div>
    </form>

    {% if query %}
        <div class="status">
            {% if results %}
                {{ results|length }} results for "{{ query }}" ({{ elapsed_ms }}ms)
            {% else %}
                No results found for "{{ query }}"
            {% endif %}
        </div>

        <div class="results">
            {% for rank, score, url in results %}
            <div class="result-card">
                <div class="result-meta">
                    <span class="rank">#{{ rank }}</span>
                    <span class="score">Score: {{ "%.4f"|format(score) }}</span>
                </div>
                <a class="result-url" href="{{ url }}" target="_blank">{{ url }}</a>
            </div>
            {% endfor %}

            {% if not results %}
            <div class="no-results">No results found. Try different keywords.</div>
            {% endif %}
        </div>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def index():
    query = request.args.get('q', '').strip()
    results = []
    elapsed_ms = 0

    if query:
        start = time.time()
        raw = search(query, top_k=10)
        elapsed_ms = round((time.time() - start) * 1000, 1)
        results = [(i+1, score, url) for i, (score, url) in enumerate(raw)]

    return render_template_string(HTML,
                                  query=query,
                                  results=results,
                                  elapsed_ms=elapsed_ms)


if __name__ == '__main__':
    print("Loading search engine...")
    load_resources()
    print("Starting web server at http://localhost:5000")
    print("Press Ctrl+C to stop.")
    app.run(debug=False, port=5000)