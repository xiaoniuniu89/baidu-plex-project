import sqlite3
import subprocess
import os
import time

BAIDUPCS_BIN = os.path.expanduser("~/BaiduPCS-Go")
DB_FILE = "media_library.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files 
                 (id INTEGER PRIMARY KEY, name TEXT, path TEXT, is_dir INTEGER, size TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS queue 
                 (id INTEGER PRIMARY KEY, path TEXT, processed INTEGER DEFAULT 0, attempts INTEGER DEFAULT 0)''')
    conn.commit()
    return conn

def list_remote_dir(remote_path, retry_count=3):
    wait_time = 2.0
    for i in range(retry_count):
        try:
            time.sleep(wait_time)
            result = subprocess.run([BAIDUPCS_BIN, "ls", remote_path], capture_output=True, text=True, check=True, timeout=30)
            if "----" in result.stdout:
                return result.stdout
            else:
                print(f"Empty/Invalid output for {remote_path}, retry {i+1}...")
        except Exception as e:
            print(f"Error listing {remote_path} (Attempt {i+1}): {e}")
        
        wait_time *= 2 # Exponential backoff
        time.sleep(wait_time)
    return None

def parse_ls_output(output, parent_path):
    files = []
    lines = output.split('\n')
    start_index = -1
    for i, line in enumerate(lines):
        if "----" in line and i + 1 < len(lines) and "#" in lines[i+1]:
            start_index = i + 2
            break
    if start_index == -1: return files

    for line in lines[start_index:]:
        if "----" in line or not line.strip(): continue
        parts = line.split()
        if len(parts) < 4: continue
        is_dir = 1 if parts[1] == '-' else 0
        name = " ".join(parts[4:])
        if name.endswith('/'): 
            is_dir = 1
            name = name.rstrip('/')
        files.append((name, os.path.join(parent_path, name), is_dir, parts[1], f"{parts[2]} {parts[3]}"))
    return files

def index_all():
    conn = init_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM queue WHERE processed = 0")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO queue (path) VALUES (?)", ("/m",))
        c.execute("INSERT INTO queue (path) VALUES (?)", ("/我的资源",))
        conn.commit()

    while True:
        c.execute("SELECT id, path, attempts FROM queue WHERE processed = 0 AND attempts < 5 ORDER BY id ASC LIMIT 1")
        row = c.fetchone()
        if not row: break
        
        q_id, current_path, attempts = row
        print(f"Indexing: {current_path} (Attempt {attempts + 1})")
        
        output = list_remote_dir(current_path)
        if output:
            items = parse_ls_output(output, current_path)
            for name, path, is_dir, size, date in items:
                # Check if file already exists to avoid duplicates
                c.execute("SELECT id FROM files WHERE path = ?", (path,))
                if not c.fetchone():
                    c.execute("INSERT INTO files (name, path, is_dir, size, date) VALUES (?, ?, ?, ?, ?)", 
                              (name, path, is_dir, size, date))
                    if is_dir:
                        c.execute("INSERT INTO queue (path) VALUES (?)", (path,))
            
            c.execute("UPDATE queue SET processed = 1 WHERE id = ?", (q_id,))
        else:
            c.execute("UPDATE queue SET attempts = attempts + 1 WHERE id = ?", (q_id,))
        
        conn.commit()
        
        c.execute("SELECT COUNT(*) FROM files")
        total_files = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM queue WHERE processed = 0")
        remaining = c.fetchone()[0]
        print(f"Progress: {total_files} items indexed | Queue: {remaining} folders left.")

    conn.close()

if __name__ == "__main__":
    index_all()
