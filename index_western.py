import subprocess
import json
import os
import sys
import time

BAIDUPCS_BIN = os.path.expanduser("~/BaiduPCS-Go")

def list_remote_dir(remote_path):
    try:
        # Adding a small delay to avoid rate limiting
        time.sleep(0.5)
        result = subprocess.run([BAIDUPCS_BIN, "ls", remote_path], capture_output=True, text=True, check=True)
        return result.stdout
    except Exception as e:
        print(f"Error listing {remote_path}: {e}")
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

def index_targeted(targets, max_depth=4):
    all_files = []
    queue = [(t, 0) for t in targets]
    
    while queue:
        current_path, depth = queue.pop(0)
        if depth > max_depth: continue
        
        print(f"Indexing: {current_path} (Depth: {depth})")
        output = list_remote_dir(current_path)
        if output:
            items = parse_ls_output(output, current_path)
            for item in items:
                all_files.append(item)
                # Only recurse into directories
                if item["is_dir"]:
                    queue.append((item["path"], depth + 1))
            
            # Periodically save progress
            with open("western_index_partial.json", "w") as f:
                json.dump(all_files, f, indent=4, ensure_ascii=False)
    
    return all_files

if __name__ == "__main__":
    # Specific western-focused targets found earlier
    western_targets = [
        "/m/风花雪月/4 国外",
        "/m/风花雪月/欧美爱情电影-男人必看",
        "/m/风花雪月/最经典的同性恋电影-R级",
        "/我的资源" # This contains many English-named series like GOT, Dexter, etc.
    ]
    
    print("Starting targeted Western index...")
    final_index = index_targeted(western_targets)
    
    with open("western_media_index.json", "w") as f:
        json.dump(final_index, f, indent=4, ensure_ascii=False)
    
    print(f"Done! Total items indexed: {len(final_index)}")
