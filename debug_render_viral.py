
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))

from modules.render_gen import build_video, _create_slideshow
from modules.utils import log, get_ffmpeg_bin
from config import OUTPUT_DIR

# Ensure output dir
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mock Data
topic = "Viral_Debug_Test"
local_video = "cinema_source_clip.mp4"
if not Path(local_video).exists():
    # Use any mp4 found
    mp4s = list(Path(".").glob("*.mp4"))
    if mp4s:
        local_video = str(mp4s[0])
    else:
        print("No local video found for testing.")
        sys.exit(1)

log("TEST", f"Using video mock: {local_video}")

# Mock Assets
# mimic 3 SVD clips by using the same video 3 times
assets = {
    "topic": topic,
    "audio": local_video, # Use video as audio source (ffmpeg allows it)
    "words": [
        {"word": "This", "start": 0.0, "end": 0.5},
        {"word": "is", "start": 0.5, "end": 1.0},
        {"word": "a", "start": 1.0, "end": 1.5},
        {"word": "viral", "start": 1.5, "end": 2.0},
        {"word": "cut", "start": 2.0, "end": 2.5}
    ],
    "images": [local_video, local_video, local_video], # 3 clips
    "gameplay": local_video # placeholder
}

# Run Build (Visual Mode to trigger slideshow + flash cuts)
try:
    log("TEST", "Building Viral Video in VISUAL mode...")
    # This calls _create_slideshow internally with our list of videos
    output_path = build_video("VISUAL", assets)
    print(f"SUCCESS: {output_path}")
    
except Exception as e:
    print(f"TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
