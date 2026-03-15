# Baidu Wangpan Query & Management Guide

This guide explains how to interact with the Baidu Netdisk library using the tools provided in this project.

## 1. Local Database Queries (Fastest)
The `media_library.db` is a SQLite database containing over 6,000 indexed items. Use this for instant searches without hitting API rate limits.

### Database Schema
- **Table:** `files`
  - `id`: Primary Key
  - `name`: The filename (often in Chinese)
  - `path`: The full remote path on Baidu Netdisk
  - `is_dir`: Boolean (1 for folder, 0 for file)
  - `size`: Human-readable size
  - `date`: Modification date

### Example Query (Python)
```python
import sqlite3

def search_library(keyword):
    conn = sqlite3.connect('media_library.db')
    c = conn.cursor()
    # Search for titles containing the keyword (case-insensitive)
    c.execute("SELECT name, path FROM files WHERE name LIKE ?", (f'%{keyword}%',))
    results = c.fetchall()
    conn.close()
    return results

# Find all movies with '2024' in the title
movies = search_library('2024')
for name, path in movies:
    print(f"{name} -> {path}")
```

## 2. Direct Remote Queries (`BaiduPCS-Go`)
Use the `BaiduPCS-Go` binary for real-time operations like searching for items not yet indexed or downloading files.

### Common Commands
- **Search:** `~/BaiduPCS-Go search -r "Keyword"`
- **List Directory:** `~/BaiduPCS-Go ls "/remote/path"`
- **Download:** `~/BaiduPCS-Go download "/remote/path" --saveto "/local/path"`
- **Meta Info:** `~/BaiduPCS-Go meta "/remote/path"`

## 3. Workflow for Semantic Search Integration
To build a semantic search tool, follow this pipeline:

1.  **Extract:** Export the `name` and `path` columns from `media_library.db`.
2.  **Translate:** Use an LLM to batch-translate the Chinese names to English `display_names`.
3.  **Embed:** Pass the `display_names` through an embedding model (e.g., OpenAI `text-embedding-3-small`).
4.  **Vector Store:** Save the embeddings in a Vector DB (Chroma, Pinecone, etc.) linked to the original `path`.
5.  **Query:** When a user asks "Find me a noir sci-fi," embed the query and perform a similarity search.

## 4. Authentication (Maintenance)
If the tool stops working, the `BDUSS` cookie may have expired.
1. Log in to `pan.baidu.com` in a browser.
2. Extract the `BDUSS` cookie from Developer Tools (F12 -> Application -> Cookies).
3. Run: `~/BaiduPCS-Go login -bduss="YOUR_NEW_BDUSS"`
