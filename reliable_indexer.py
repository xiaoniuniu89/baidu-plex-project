import subprocess
import json
import os
import time

BAIDUPCS_BIN = os.path.expanduser("~/BaiduPCS-Go")
QUEUE_FILE = "index_queue.json"
INDEX_FILE = "full_media_index.json"
LOG_FILE = "indexing_log.txt"

def list_remote_dir(remote_path):
    try:
        # 1-second delay to be extremely safe with Baidu API
        time.sleep(1.0)
        result = subprocess.run([BAIDUPCS_BIN, "ls", remote_path], capture_output=True, text=True, check=True)
        return result.stdout
    except Exception as e:
        with open(LOG_FILE, "a") as f:
            f.write(f"FAILED: {remote_path} - {str(e)}\n")
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
        is_dir = parts[1] == '-'
        name = " ".join(parts[4:])
        is_dir = is_dir or name.endswith('/')
        name = name.rstrip('/')
        files.append({
            "name": name,
            "path": os.path.join(parent_path, name),
            "is_dir": is_dir,
            "size": parts[1] if not is_dir else None,
            "date": f"{parts[2]} {parts[3]}"
        })
    return files

def run_indexer():
    # Load or initialize state
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r") as f:
            state = json.load(f)
            queue = state["queue"]
            indexed_items = state["indexed"]
    else:
        # Start from your main media roots
        queue = ["/m", "/我的资源"]
        indexed_items = []

    print(f"Starting/Resuming Indexer. Items in queue: {len(queue)}")

    while queue:
        current_path = queue.pop(0)
        
        # Log progress
        with open(LOG_FILE, "a") as f:
            f.write(f"PROCESSING: {current_path}\n")
        
        output = list_remote_dir(current_path)
        if output:
            items = parse_ls_output(output, current_path)
            for item in items:
                indexed_items.append(item)
                if item["is_dir"]:
                    queue.append(item["path"])
            
            # Save state every folder to be crash-proof
            with open(QUEUE_FILE, "w") as f:
                json.dump({"queue": queue, "indexed": indexed_items}, f, indent=4, ensure_ascii=False)
            
            # Print status update
            print(f"Indexed: {current_path} | Total Items: {len(indexed_items)} | Remaining Queue: {len(queue)}")

    # Final Save
    with open(INDEX_FILE, "w") as f:
        json.dump(indexed_items, f, indent=4, ensure_ascii=False)
    print("INDEXING COMPLETE.")

if __name__ == "__main__":
    run_indexer()
