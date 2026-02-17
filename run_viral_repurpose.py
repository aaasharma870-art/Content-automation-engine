
import os
import sys
import asyncio
from pathlib import Path
import re
import random

# Adjust path so we can import from src/
# We are in .automation/
# Src is in .automation/src/
# Adjust path to include the root folder AND src folder
PROJECT_ROOT = Path(__file__).parent.resolve()
SRC_PATH = PROJECT_ROOT / "src"
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(SRC_PATH))

print(f"DEBUG: Added {PROJECT_ROOT} and {SRC_PATH} to sys.path")

try:
    from modules.utils import log
    from modules.ingest import download_video
    from modules.transcribe import transcribe_video, get_words_in_range
    from modules.miner import analyze_transcript_patterns
    from modules.audio import _inject_micro_sfx
    from modules.render_gen import build_video
    from config import OUTPUT_DIR, SFX_DIR

    from pydub import AudioSegment
    from modules.utils import get_ffmpeg_bin, get_ffprobe_bin
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Configure Pydub
AudioSegment.converter = get_ffmpeg_bin()
AudioSegment.ffprobe = get_ffprobe_bin()

# The "Same Link"
URL = "https://www.youtube.com/watch?v=An306Mqzb7E"

def _generate_ass_simple(words, output_path):
    """Generate a minimal ASS subtitle file from word list."""
    header = """[Script Info]
Title: Viral Clip
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    # Group words into ~3 word chunks
    chunk = []
    chunk_start = 0
    for w in words:
        if not chunk:
            chunk_start = w["start"]
        chunk.append(w["word"])
        if len(chunk) >= 3:
            start_ts = _format_ass_time(chunk_start)
            end_ts = _format_ass_time(w["end"])
            text = " ".join(chunk)
            lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}")
            chunk = []
    # Remaining words
    if chunk:
        start_ts = _format_ass_time(chunk_start)
        end_ts = _format_ass_time(words[-1]["end"])
        text = " ".join(chunk)
        lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(lines))

def _format_ass_time(seconds):
    """Convert seconds to ASS time format H:MM:SS.CC"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def run_viral_repurpose():
    log("VIRAL", f"Starting Viral Repurpose for: {URL}")
    
    # 1. Ingest (Reuse existing if possible)
    # Check if we have the file already to save time
    local_video = Path("cinema_source_clip.mp4")
    if local_video.exists():
        video_path = str(local_video.resolve())
        log("VIRAL", f"Using local video: {video_path}", "OK")
    else:
        video_info = download_video(URL)
        video_path = video_info["video_path"]
        
    # 2. Transcribe
    # (Simulated for speed if we have a transcript, but let's run it or fail faster if needed)
    # properly we should check if transcript.json exists
    log("VIRAL", "Transcribing...")
    transcript = transcribe_video(video_path)
    full_text = transcript["full_text"]
    words = transcript["words"]
    
    # 3. Mine for "Listicle" patterns
    log("VIRAL", "Mining for 'Enumeration Markers'...")
    
    if not words:
        log("VIRAL", "Transcription returned no words (video might be silent or short). using generic 45s clip.", "WARN")
        # Generate dummy words for 45s
        words = [{"word": "Viral", "start": 0.0, "end": 1.0}, {"word": "Video", "start": 1.0, "end": 45.0}]
        matches = [{"index": 0, "marker": "Manual Start"}]
    else:
        matches = analyze_transcript_patterns(full_text)
    
    if not matches:
        log("VIRAL", "No viral patterns found. Creating a generic viral clip from start.", "WARN")
        matches = [{"index": 0, "marker": "Manual Start"}]
        
    # Process up to 3 segments
    for i, match in enumerate(matches[:3]):
        start_char = match["index"]
        # Approximate timestamp from char index (rough heuristic: 15 chars ~ 1 sec? No, rely on words)
        # Better: find word with closest start char? 
        # Simpler: Just clip 60 seconds around the marker.
        
        # Find time of matching word
        # This is a bit rough, but let's assume linear mapping for MVP or search word list.
        # Actually, let's just grab a random high-motion segment if matches are ambiguous.
        # But wait, analyze_transcript_patterns returns char index.
        # Let's map char index to word index.
        
        start_time = 0.0
        current_char = 0
        for w in words:
            if current_char >= start_char:
                start_time = w["start"]
                break
            current_char += len(w["word"]) + 1 # +1 for space
            
        duration = 45.0 # Viral Short length
        end_time = min(start_time + duration, words[-1]["end"])
        
        log("VIRAL", f"Creating Clip {i+1}: {start_time:.2f}s - {end_time:.2f}s")
        
        # 4. Audio Upgrade (Micro-SFX)
        # Extract audio segment using FFmpeg directly (bypass pydub's broken path detection)
        clip_audio_path = OUTPUT_DIR / f"viral_clip_{i+1}_audio.mp3"
        temp_wav_path = OUTPUT_DIR / f"_temp_extract_{i+1}.wav"
        try:
            import subprocess
            # Step 1: Extract audio clip via FFmpeg (fast, reliable)
            extract_cmd = [
                get_ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
                "-ss", str(start_time), "-to", str(end_time),
                "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
                str(temp_wav_path)
            ]
            log("VIRAL", f"Extracting audio: {start_time:.1f}s - {end_time:.1f}s...")
            subprocess.run(extract_cmd, check=True)
            
            # Step 2: Load the small WAV into pydub for SFX injection
            seg = AudioSegment.from_file(str(temp_wav_path), format="wav")
            
            # Inject Micro-SFX (whooshes at 1.4s and 2.8s per 4s block)
            seg = _inject_micro_sfx(seg)
            seg.export(str(clip_audio_path), format="mp3")
            log("VIRAL", f"Audio ready: {clip_audio_path} ({len(seg)/1000:.1f}s)", "OK")
            
            # Cleanup temp
            if temp_wav_path.exists():
                os.remove(temp_wav_path)
            
        except Exception as e:
            log("VIRAL", f"Audio processing failed: {e}", "ERR")
            import traceback
            traceback.print_exc()
            continue
            
        # 5. Render with Flash Cuts — Single Pass
        # Instead of chunking + concat (fragile), we do ONE FFmpeg command:
        # Input 0: Audio (processed with Micro-SFX)
        # Input 1: Video segment (seeked to start_time)
        # Filter: Animated crop (Flash Cut) + ASS subtitles
        
        import subprocess, random
        
        # Generate subtitles
        cur_words = get_words_in_range(words, start_time, end_time)
        # Adjust word timestamps relative to 0
        for w in cur_words:
            w["start"] -= start_time
            w["end"] -= start_time
        
        ass_path = str(OUTPUT_DIR / f"viral_clip_{i+1}.ass")
        _generate_ass_simple(cur_words, ass_path)
        
        # Flash Cut: scale up 1.5x then animated crop
        sw, sh = 1620, 2880
        tw, th = 1080, 1920
        pattern = random.choice(["A", "B", "C"])
        
        if pattern == "A":
            x_expr = f"min(t*50,{sw - tw})"
            y_expr = f"{(sh - th) // 2}"
        elif pattern == "B":
            x_expr = f"min(t*30,{(sw - tw) // 2})"
            y_expr = f"min(t*50,{(sh - th) // 2})"
        else:
            x_expr = f"({(sw - tw) // 2})*(1+sin(t*3))/2"
            y_expr = f"({(sh - th) // 2})*(1+cos(t*2))/2"
        
        ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")
        
        filter_str = (
            f"[0:v]scale={sw}:{sh}:force_original_aspect_ratio=disable,"
            f"crop={tw}:{th}:{x_expr}:{y_expr},"
            f"setsar=1,format=yuv420p[outv]"
        )
        
        output_file = str(OUTPUT_DIR / f"viral_clip_{i+1}.mp4")
        
        cmd = [
            get_ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(start_time), "-to", str(end_time),
            "-i", video_path,
            "-i", str(clip_audio_path),
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-map", "1:a",
            "-c:v", "h264_nvenc",
            "-b:v", "5M",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_file
        ]
        
        # Render
        try:
            log("VIRAL", f"Rendering clip {i+1} with Flash Cut pattern {pattern}...")
            subprocess.run(cmd, check=True)
            log("VIRAL", f"✅ Clip {i+1} Complete: {output_file}", "OK")
        except Exception as e:
            log("VIRAL", f"Render failed: {e}", "ERR")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_viral_repurpose()
