"""
main.py - The Orchestrator (AutoShorts_Pro)
============================================
The "Ghost Employee" that runs in the background.

Workflow:
1. Monitors queue.txt for new YouTube URLs (every 30 seconds)
2. For each URL: Ingest -> Transcribe -> Brain -> Director -> Editor
3. Moves processed URLs to history.txt
4. Logs errors and keeps running (never crashes on a bad video)

Usage:
    python main.py
    
Then paste YouTube URLs into queue.txt and save. Shorts appear in output/.
"""

import os
import sys
import time
import shutil
import traceback
from datetime import datetime
from pathlib import Path

# ── Colorama for Windows terminal colors ───────
from colorama import init, Fore, Style
init(autoreset=True)

# ── Local modules ──────────────────────────────
import sys
import os
print(f"DEBUG: CWD={os.getcwd()}")
print(f"DEBUG: sys.path={sys.path}")
import config
print(f"DEBUG: config file={config.__file__}")
print(f"DEBUG: config dir={dir(config)}")

from config import (
    QUEUE_FILE, HISTORY_FILE, ERRORS_LOG,
    OUTPUT_DIR, TEMP_DIR, POLL_INTERVAL_SECONDS,
    GOOGLE_API_KEY,
)
from modules.ingest import download_video, is_valid_youtube_url
from modules.transcribe import transcribe_video, refine_timestamps, get_words_in_range
from modules.brain import analyze_transcript
from modules.director import analyze_scene
from modules.editor import render_short


# ══════════════════════════════════════════════
# BANNER
# ══════════════════════════════════════════════

BANNER = f"""
{Fore.RED}╔══════════════════════════════════════════════════════════╗
║  {Fore.WHITE}A U T O S H O R T S   P R O{Fore.RED}                              ║
║  {Fore.YELLOW}Local Opus Clip Replica • "Ghost Employee" Mode{Fore.RED}         ║
║  {Fore.CYAN}Drop URLs in queue.txt → Get Shorts in output/{Fore.RED}           ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""


def main():
    """Main loop: watch queue.txt, process videos, repeat forever."""
    print(BANNER)
    
    # ── Preflight Checks ───────────────────────
    _preflight_checks()
    
    # ── Ensure queue.txt exists ─────────────────
    if not QUEUE_FILE.exists():
        QUEUE_FILE.touch()
    
    print(f"{Fore.GREEN}[MAIN]{Style.RESET_ALL} 🟢 Watching: {QUEUE_FILE}")
    print(f"{Fore.GREEN}[MAIN]{Style.RESET_ALL} 📂 Output:   {OUTPUT_DIR}")
    print(f"{Fore.GREEN}[MAIN]{Style.RESET_ALL} ⏱️  Polling every {POLL_INTERVAL_SECONDS}s")
    print(f"{Fore.GREEN}[MAIN]{Style.RESET_ALL} Press Ctrl+C to stop.\n")
    
    while True:
        try:
            urls = _read_queue()
            
            if urls:
                for url in urls:
                    print(f"\n{'='*60}")
                    print(f"{Fore.WHITE}[MAIN] Processing: {url}{Style.RESET_ALL}")
                    print(f"{'='*60}")
                    
                    try:
                        process_video(url)
                        _mark_completed(url)
                        print(f"\n{Fore.GREEN}[MAIN]{Style.RESET_ALL} ✅ Done: {url}\n")
                    except Exception as e:
                        _log_error(url, e)
                        _mark_completed(url)  # Don't retry failed URLs
                        print(f"\n{Fore.RED}[MAIN]{Style.RESET_ALL} ❌ Failed: {url}")
                        print(f"  Error: {e}\n")
            
            # Sleep then check again
            time.sleep(POLL_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}[MAIN]{Style.RESET_ALL} 🛑 Shutting down gracefully...")
            _cleanup_temp()
            sys.exit(0)


def process_video(url: str):
    """
    Run the full pipeline on a single YouTube URL.
    
    Pipeline: Ingest -> Transcribe -> Brain -> Director -> Editor
    """
    start_time = time.time()
    
    # ═══ STAGE 1: INGEST ═══════════════════════
    print(f"\n{Fore.CYAN}{'─'*40}")
    print(f"[STAGE 1/5] INGESTING VIDEO")
    print(f"{'─'*40}{Style.RESET_ALL}")
    
    video_info = download_video(url)
    video_path = video_info["video_path"]
    title = video_info["title"]
    metadata = video_info.get("metadata", {})
    
    # ═══ STAGE 2: TRANSCRIBE ═══════════════════
    print(f"\n{Fore.MAGENTA}{'─'*40}")
    print(f"[STAGE 2/5] TRANSCRIBING AUDIO")
    print(f"{'─'*40}{Style.RESET_ALL}")
    
    transcript = transcribe_video(video_path)
    words = transcript["words"]
    full_text = transcript["full_text"]
    
    if not full_text.strip():
        raise RuntimeError("Transcription returned empty text")
    
    # ═══ STAGE 3: BRAIN (Gemini) ═══════════════
    print(f"\n{Fore.BLUE}{'─'*40}")
    print(f"[STAGE 3/5] ANALYZING VIRALITY (GEMINI)")
    print(f"{'─'*40}{Style.RESET_ALL}")
    
    clips = analyze_transcript(full_text, metadata)
    
    if not clips:
        raise RuntimeError("Brain found no viral segments in this video")
    
    # ═══ STAGE 4 & 5: DIRECTOR + EDITOR ════════
    results = []
    
    for i, clip in enumerate(clips):
        clip_num = i + 1
        
        print(f"\n{Fore.YELLOW}{'─'*40}")
        print(f"[STAGE 4/5] DIRECTING CLIP {clip_num}/{len(clips)}")
        print(f"{'─'*40}{Style.RESET_ALL}")
        
        # Refine timestamps to snap to silence boundaries
        refined_start, refined_end = refine_timestamps(
            words, clip["start"], clip["end"]
        )
        clip["start"] = refined_start
        clip["end"] = refined_end
        
        # Analyze scene (face tracking / screen detection)
        scene_data = analyze_scene(
            video_path,
            clip["start"],
            clip["end"],
            clip.get("layout_type", "talking_head"),
        )
        
        # Extract words for this clip (0-based relative timestamps)
        clip_words = get_words_in_range(words, clip["start"], clip["end"])
        
        print(f"\n{Fore.RED}{'─'*40}")
        print(f"[STAGE 5/5] RENDERING CLIP {clip_num}/{len(clips)}")
        print(f"{'─'*40}{Style.RESET_ALL}")
        
        # Generate output filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:40].strip()
        score = clip.get("score", 0)
        output_name = f"{safe_title}_Short_{clip_num}_{score:.0f}.mp4"
        
        # Render the short
        output_path = render_short(
            video_path=video_path,
            clip_data=clip,
            scene_data=scene_data,
            words=clip_words,
            output_filename=output_name,
        )
        
        results.append(output_path)
    
    # ═══ CLEANUP ═══════════════════════════════
    elapsed = time.time() - start_time
    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"[COMPLETE] {len(results)} shorts generated in {elapsed:.0f}s")
    print(f"{'='*60}{Style.RESET_ALL}")
    
    for r in results:
        print(f"  📹 {r}")
    
    # Clean up temp files for this video
    work_dir = Path(video_info.get("work_dir", ""))
    if work_dir.exists():
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass


# ══════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════

def _read_queue() -> list:
    """Read queue.txt and return new, valid YouTube URLs."""
    if not QUEUE_FILE.exists():
        return []
    
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    urls = []
    remaining = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            remaining.append(line)
            continue
        
        if is_valid_youtube_url(stripped):
            urls.append(stripped)
        else:
            remaining.append(line)
    
    # Rewrite queue.txt without the URLs we're about to process
    if urls:
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            f.writelines(remaining)
    
    return urls


def _mark_completed(url: str):
    """Append a processed URL to history.txt."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {url}\n")


def _log_error(url: str, error: Exception):
    """Log a processing error to errors.log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERRORS_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] URL: {url}\n")
        f.write(f"Error: {error}\n")
        f.write(traceback.format_exc())
        f.write("\n" + "─" * 60 + "\n")


def _cleanup_temp():
    """Remove all temporary files on shutdown."""
    if TEMP_DIR.exists():
        try:
            shutil.rmtree(TEMP_DIR)
            TEMP_DIR.mkdir(exist_ok=True)
            print(f"{Fore.GREEN}[MAIN]{Style.RESET_ALL} Temp files cleaned up.")
        except Exception:
            pass


def _preflight_checks():
    """Verify that required tools and credentials are available."""
    errors = []
    
    # Check API key
    from config import LLM_PROVIDER, OPENAI_API_KEY, GOOGLE_API_KEY
    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
             errors.append("OPENAI_API_KEY not set in .env file")
    elif not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY not set in .env file")
    
    # Check FFmpeg
    try:
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, timeout=5
        )
        if result.returncode != 0:
            errors.append("FFmpeg not working correctly")
    except FileNotFoundError:
        errors.append("FFmpeg not found in PATH. Install from https://ffmpeg.org")
    
    # Check yt-dlp
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"], capture_output=True, timeout=5
        )
        if result.returncode != 0:
            errors.append("yt-dlp not working correctly")
    except FileNotFoundError:
        errors.append("yt-dlp not found. Install: pip install yt-dlp")
    
    if errors:
        print(f"\n{Fore.RED}{'='*60}")
        print(f"[PREFLIGHT] ⚠️  Issues found:")
        print(f"{'='*60}{Style.RESET_ALL}")
        for e in errors:
            print(f"  ❌ {e}")
        print()
        
        # Only hard-fail on API key (others might be okay)
        # Only hard-fail on API key (others might be okay)
        if "API_KEY" in str(errors):
            print(f"{Fore.YELLOW}  Please check your .env file for the correct API key.{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.GREEN}[PREFLIGHT]{Style.RESET_ALL} ✓ All systems operational.\n")


# Need this import in the process_video scope
import re


if __name__ == "__main__":
    main()
