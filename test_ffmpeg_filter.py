"""Minimal FFmpeg filter chain test to isolate the crash."""
import subprocess
import imageio_ffmpeg

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
video = r"data\raw\An306Mqzb7E\almost 1 HOUR of reddit stories and minecraft to fall asleep to (or stay awake,.mp4"

# Test 1: Simple extract + scale (no animated crop)
print("=== TEST 1: Simple Scale ===")
r = subprocess.run([
    ffmpeg, "-y", "-hide_banner",
    "-ss", "60", "-t", "10",
    "-i", video,
    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p",
    "-c:v", "h264_nvenc", "-b:v", "5M",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    "output/test_simple.mp4"
], capture_output=True, text=True)
print(f"RC: {r.returncode}")
if r.returncode != 0:
    print(f"STDERR: {r.stderr[-500:]}")
else:
    print("PASS")

# Test 2: Animated crop (the Flash Cut)
print("\n=== TEST 2: Animated Crop (Flash Cut) ===")
r2 = subprocess.run([
    ffmpeg, "-y", "-hide_banner",
    "-ss", "60", "-t", "10",
    "-i", video,
    "-vf", "scale=1620:2880:force_original_aspect_ratio=disable,crop=1080:1920:min(t*50\\,540):480,setsar=1,format=yuv420p",
    "-c:v", "h264_nvenc", "-b:v", "5M",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    "output/test_flash_cut.mp4"
], capture_output=True, text=True)
print(f"RC: {r2.returncode}")
if r2.returncode != 0:
    print(f"STDERR: {r2.stderr[-500:]}")
else:
    print("PASS")

# Test 3: filter_complex style (matching run_viral_repurpose.py exactly)
print("\n=== TEST 3: filter_complex ===")
filter_str = "[0:v]scale=1620:2880:force_original_aspect_ratio=disable,crop=1080:1920:min(t*50\\,540):480,setsar=1,format=yuv420p[outv]"
r3 = subprocess.run([
    ffmpeg, "-y", "-hide_banner",
    "-ss", "60", "-t", "10",
    "-i", video,
    "-filter_complex", filter_str,
    "-map", "[outv]",
    "-map", "0:a",
    "-c:v", "h264_nvenc", "-b:v", "5M",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    "output/test_fc_complex.mp4"
], capture_output=True, text=True)
print(f"RC: {r3.returncode}")
if r3.returncode != 0:
    print(f"STDERR: {r3.stderr[-500:]}")
else:
    print("PASS")
