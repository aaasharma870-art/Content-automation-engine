"""
ingest.py - The Watcher (Smart Downloader)
===========================================
Monitors queue.txt for YouTube URLs and downloads them using yt-dlp.
Downloads video (1080p) and audio (m4a) separately for maximum quality.
"""

import re
import json
import subprocess
from pathlib import Path
from colorama import Fore, Style

from config import TEMP_DIR, COOKIES_FILE


def is_valid_youtube_url(url: str) -> bool:
    """Validate that a string is a real YouTube URL."""
    patterns = [
        r'(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(https?://)?(www\.)?youtu\.be/[\w-]+',
        r'(https?://)?(www\.)?youtube\.com/shorts/[\w-]+',
    ]
    return any(re.match(p, url.strip()) for p in patterns)


def download_video(url: str) -> dict:
    """
    Download a YouTube video using yt-dlp.
    
    Downloads:
    - Video: best quality up to 1080p (mp4)
    - Audio: best quality (m4a)
    - Auto-captions: .vtt backup for timestamp alignment
    
    Args:
        url: YouTube URL to download
        
    Returns:
        dict with keys: video_path, audio_path, title, metadata
        
    Raises:
        RuntimeError: If download fails
    """
    print(f"{Fore.CYAN}[INGEST]{Style.RESET_ALL} Downloading: {url}")
    
    # Create a unique temp folder for this video
    video_id = _extract_video_id(url)
    work_dir = TEMP_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # ── Step 1: Download metadata first ──────────────
    meta_cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        url,
    ]
    
    try:
        result = subprocess.run(
            meta_cmd, capture_output=True, text=True, timeout=60
        )
        metadata = json.loads(result.stdout)
        title = _sanitize_filename(metadata.get("title", video_id))
    except Exception as e:
        print(f"{Fore.YELLOW}[INGEST]{Style.RESET_ALL} Metadata fetch failed, using ID: {e}")
        metadata = {}
        title = video_id
    
    # ── Step 2: Download video (best mp4 up to 1080p) ─
    video_path = work_dir / f"{title}.mp4"
    video_cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(video_path),
        "--no-playlist",
    ]
    
    # Add cookies if file exists (helps avoid bot detection)
    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        video_cmd.extend(["--cookies", str(COOKIES_FILE)])
    
    video_cmd.append(url)
    
    print(f"{Fore.CYAN}[INGEST]{Style.RESET_ALL} Downloading video...")
    result = subprocess.run(video_cmd, capture_output=True, text=True, timeout=600)
    
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp video download failed: {result.stderr[:500]}")
    
    # ── Step 3: Download auto-captions (.vtt) as backup ─
    vtt_path = work_dir / f"{title}.en.vtt"
    vtt_cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "--skip-download",
        "-o", str(work_dir / title),
        url,
    ]
    
    print(f"{Fore.CYAN}[INGEST]{Style.RESET_ALL} Fetching auto-captions...")
    subprocess.run(vtt_cmd, capture_output=True, text=True, timeout=120)
    # Captions are optional, don't fail if missing
    
    # Find the actual downloaded file (yt-dlp may alter the name slightly)
    actual_video = _find_video_file(work_dir)
    if not actual_video:
        raise RuntimeError(f"No video file found in {work_dir}")
    
    print(f"{Fore.GREEN}[INGEST]{Style.RESET_ALL} ✓ Downloaded: {actual_video.name}")
    
    return {
        "video_path": str(actual_video),
        "title": title,
        "work_dir": str(work_dir),
        "metadata": metadata,
        "vtt_path": str(vtt_path) if vtt_path.exists() else None,
    }


def _extract_video_id(url: str) -> str:
    """Extract the YouTube video ID from a URL."""
    patterns = [
        r'v=([\w-]+)',
        r'youtu\.be/([\w-]+)',
        r'shorts/([\w-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return "unknown_video"


def _sanitize_filename(name: str) -> str:
    """Remove characters that are illegal in Windows filenames."""
    illegal = r'[<>:"/\\|?*]'
    sanitized = re.sub(illegal, '', name)
    return sanitized[:80].strip()  # Cap length at 80 chars


def _find_video_file(directory: Path) -> Path | None:
    """Find the first .mp4 file in a directory."""
    for f in sorted(directory.glob("*.mp4"), key=lambda x: x.stat().st_size, reverse=True):
        return f
    return None
