# Baidu-Plex Media Management Project

This project contains tools and data for managing a massive Baidu Wangpan media library and integrating it with a Plex server.

## Folder Structure

- **`media_library.db`**: A SQLite database containing 6,235 indexed items from the Baidu Netdisk.
- **`REPORT.md`**: A detailed report of the indexing process, results, and next steps.
- **`BAIDU_QUERY_GUIDE.md`**: Instructions on how to query the database and the remote disk.
- **`sqlite_indexer.py`**: The robust, SQLite-powered indexing script used to build the database.
- **`reliable_indexer.py`**, **`index_western.py`**, **`index_baidu.py`**: Earlier iterations and specialized versions of the indexer.
- **`baidu-plex-manager-skill/`**: A Gemini CLI skill containing domain-specific knowledge for this project.
- **`plex-mcp-server/`**: A TypeScript-based Model Context Protocol (MCP) server for Plex management.

## Key Findings
- **Total Indexed:** 6,235 items.
- **Major Libraries:** `/m/风花雪月` and `/我的资源`.
- **Successful Downloads:** `Eyes Wide Shut (1999)`, `Dear Ex (2018)`, `About Time (2013)`.

## Usage
Use `media_library.db` as the source for building a Semantic Search tool. The `BAIDU_QUERY_GUIDE.md` provides code snippets to get started.
