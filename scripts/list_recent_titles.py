import sys
from pathlib import Path
import json

# Add project root to path
sys.path.append(str(Path("/home/kafka/2511youtuber")))

from src.utils.history import extract_title

def get_titles(limit=70):
    runs_dir = Path("/home/kafka/2511youtuber/runs")
    if not runs_dir.exists():
        print("Runs directory not found.")
        return

    # Sort runs by name (timestamp) descending
    runs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], reverse=True)
    
    count = 0
    results = []
    
    for run in runs:
        if count >= limit:
            break
            
        title = None
        # Try metadata.json first
        meta_path = run / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    title = extract_title(data)
            except Exception:
                pass
        
        # If no title, try youtube.json
        if not title:
            yt_path = run / "youtube.json"
            if yt_path.exists():
                try:
                    with open(yt_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        title = extract_title(data)
                except Exception:
                    pass
        
        if title:
            results.append(f"{run.name}: {title}")
            count += 1
        else:
            # Skip runs without titles (failed or in progress)
            pass

    for line in results:
        print(line)

if __name__ == "__main__":
    get_titles()
