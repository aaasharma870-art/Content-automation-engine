
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))

from modules.utils import log, get_ffmpeg_bin, get_ffprobe_bin
from modules.audio import generate_flow_audio

print(f"DEBUG: Detected FFMPEG: {get_ffmpeg_bin()}")
print(f"DEBUG: Detected FFPROBE: {get_ffprobe_bin()}")

# Test Segments
segments = [
    "This is the hook that grabs your attention immediately.",
    "Result number one is that it removes all the silence.",
    "Result number two is that it overlaps the sentences slightly.",
    "And the cherry on top is that it speeds everything up for retention."
]

output_file = "test_flow_audio.mp3"

try:
    log("TEST", "Starting Audio Flow Test...")
    result = generate_flow_audio(segments, output_file)
    print(f"SUCCESS: {result}")
    
    if Path(output_file).exists():
        print(f"File created: {output_file}, Size: {Path(output_file).stat().st_size} bytes")
    else:
        print("ERROR: File not created.")

except Exception as e:
    print(f"TEST FAILED: {e}")
