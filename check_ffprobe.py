
import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from utils.ffmpeg_utils import FFMPEG_BIN
import subprocess
import os

print(f"FFMPEG_BIN: {FFMPEG_BIN}")

# Derive ffprobe path
ffprobe_bin = FFMPEG_BIN.replace("ffmpeg.exe", "ffprobe.exe")
if not os.path.exists(ffprobe_bin):
    # Try just "ffprobe" if bundled in imageio or system
    ffprobe_bin = "ffprobe"

print(f"FFPROBE_BIN: {ffprobe_bin}")

cmd = [
    ffprobe_bin,
    "-v", "error",
    "-show_entries", "stream=codec_type",
    "-of", "csv=p=0",
    "cinema_source_clip.mp4"
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    print(f"Streams found: {result.stdout.strip()}")
    if "audio" not in result.stdout:
        print("WARNING: No audio stream found!")
    else:
        print("Audio stream CONFIRMED.")
except Exception as e:
    print(f"FFprobe failed: {e}")
