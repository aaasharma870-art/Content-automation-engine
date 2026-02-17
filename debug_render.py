
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from modules.editor import render_short
from modules.director import analyze_scene


from modules.ingest import download_video

# URL to check/download

# Link to local video file for fast debugging
# url = "https://www.youtube.com/watch?v=An306Mqzb7E"
# print(f"Checking for video: {url}")
# video_info = download_video(url)
# video_path = video_info["video_path"]
video_path = str(Path("cinema_source_clip.mp4").resolve())
if not Path(video_path).exists():
     raise RuntimeError(f"Local test file not found: {video_path}")

print(f"Using video path: {video_path}")

output_filename = "debug_clip_test.mp4"



# 10 second clip

# ── Mock Data for Features (Split-Screen, Emphasis, Style) ──
print("Setting up mock data for Split-Screen & Features...")

# Mock Clip Data
clip_data = {
    "start": 60.0,
    "end": 65.0,
    "virality_score": 95,
    "layout_type": "podcast", 
    # "visual_style": "moody",  # Disabled for now to rule out LUT error
    "emphasis_words": [
        {"word": "debug", "type": "key_noun"},       # Green
        {"word": "test", "type": "key_adjective"},   # Yellow
    ],
    "impact_moments": [1.0, 3.0] # SFX injection points
}

# Mock Scene Data (Split Screen)
# Assuming 1920x1080 source
source_w = 1920
source_h = 1080
scene_data = {
    "mode": "split_screen",
    "face_centers": [source_w // 4, 3 * source_w // 4], # Left/Right split
    "crop_data": [], 
    "frame_count": 150,
    "source_width": source_w,
    "source_height": source_h,
    "fps": 30.0,
}

# Mock Words (relative to clip start)
words = [
    {"word": "This", "start": 0.0, "end": 0.5},
    {"word": "is", "start": 0.5, "end": 1.0},
    {"word": "a", "start": 1.0, "end": 1.5},
    {"word": "debug", "start": 1.5, "end": 2.0}, # Highlighted
    {"word": "test", "start": 2.0, "end": 2.5},  # Highlighted
]

# Ensure assets
(Path("assets") / "luts").mkdir(parents=True, exist_ok=True)
(Path("assets") / "sfx" / "transitions").mkdir(parents=True, exist_ok=True)
dummy_lut = Path("assets") / "luts" / "teal_orange.cube"
if not dummy_lut.exists():
    dummy_lut.write_text("# Dummy LUT")


print("Running render_short with MOCK data...")
try:
    output_path = render_short(
        video_path=video_path,
        clip_data=clip_data,
        scene_data=scene_data,
        words=words,
        output_filename="debug_features_test.mp4",
        broll_insert=None
    )
    print(f"Render SUCCESS: {output_path}")
except Exception as e:
    print(f"Render FAILED: {e}")
    with open("debug_error.log", "w", encoding="utf-8") as f:
        f.write(str(e))

print(f"Render complete: {output_path}")
