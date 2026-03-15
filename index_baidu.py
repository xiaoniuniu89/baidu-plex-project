import subprocess
import json
import os
import sys

# Path to the BaiduPCS-Go binary
BAIDUPCS_BIN = os.path.expanduser("~/BaiduPCS-Go")

def list_remote_dir(remote_path):
    """Lists files in a remote directory using BaiduPCS-Go."""
    try:
        result = subprocess.run([BAIDUPCS_BIN, "ls", remote_path], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error listing {remote_path}: {e.stderr}")
        return None

def parse_ls_output(output, parent_path):
    """Parses the output of 'BaiduPCS-Go ls' into a list of dictionaries."""
    files = []
    lines = output.split('\n')
    # Look for the start of the file list
    start_index = -1
    for i, line in enumerate(lines):
        if "----" in line and i + 1 < len(lines) and "#" in lines[i+1]:
            start_index = i + 2
            break
    
    if start_index == -1:
        return files

    for line in lines[start_index:]:
        if "----" in line or not line.strip():
            continue
        # Split by multiple spaces
        parts = line.split()
        if len(parts) < 4:
            continue
        
        # Determine if it's a directory (no size listed, usually '-')
        is_dir = parts[1] == '-'
        name = " ".join(parts[4:])
        
        # Clean up name (BaiduPCS-Go adds a trailing slash to directories)
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

def index_library(remote_path, max_depth=5):
    """Recursively indexes the library."""
    all_files = []
    queue = [(remote_path, 0)]
    
    while queue:
        current_path, depth = queue.pop(0)
        if depth > max_depth:
            continue
        
        print(f"Indexing: {current_path} (Depth: {depth})")
        output = list_remote_dir(current_path)
        if output:
            items = parse_ls_output(output, current_path)
            for item in items:
                all_files.append(item)
                if item["is_dir"]:
                    queue.append((item["path"], depth + 1))
    
    return all_files

if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else "/m"
    index_file = "baidu_library_index.json"
    
    print(f"Starting index of {target_path}...")
    index_data = index_library(target_path)
    
    with open(index_file, "w") as f:
        json.dump(index_data, f, indent=4, ensure_ascii=False)
    
    print(f"Index complete! Saved to {index_file}. Total items: {len(index_data)}")
