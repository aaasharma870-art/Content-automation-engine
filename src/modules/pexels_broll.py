"""
pexels_broll.py - Pexels API B-Roll Fallback
===============================================
When the local CLIP/FAISS library has no matches above the similarity
threshold, this module queries the free Pexels Video API to download
royalty-free stock footage matching the LLM's broll_query.

This ensures B-roll injection never becomes repetitive even with a
small local library.
"""

import os
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import PEXELS_API_KEY, BROLL_DIR, BROLL_OVERLAY_DURATION
from src.utils.logger import log
from src.utils.ffmpeg_utils import FFMPEG_BIN


def search_pexels_video(query: str, duration_max: int = 15, **kwargs) -> dict | None:
    """
    Search Pexels for a short stock video matching the query.

    Args:
        query: Natural language description (from LLM broll_query)
        duration_max: Max video duration in seconds

    Returns:
        dict with video_path (downloaded), video_name, source="pexels"
        or None if no results / no API key
    """
    if not PEXELS_API_KEY:
        log("PEXELS", "No PEXELS_API_KEY set. API B-roll disabled.", "WARN")
        return None

    try:
        import requests
    except ImportError:
        log("PEXELS", "requests not installed", "ERROR")
        return None

    # Enforce adaptive visual style
    visual_style = kwargs.get("visual_style", "cinematic vertical 4k")
    enhanced_query = f"{query} {visual_style} vertical"
    
    log("PEXELS", f"Searching Pexels for: \"{enhanced_query[:60]}\"...")

    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": enhanced_query,
        "per_page": 5,
        "orientation": "portrait",  # Prefer vertical footage for 9:16
    }

    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log("PEXELS", f"API request failed: {e}", "ERROR")
        return None

    videos = data.get("videos", [])
    if not videos:
        log("PEXELS", "No results found on Pexels", "WARN")
        return None

    # Pick the best short video (prefer shorter clips)
    best = None
    for video in videos:
        dur = video.get("duration", 999)
        if dur <= duration_max:
            # Get the HD or SD video file
            video_files = video.get("video_files", [])
            # Prefer HD quality, portrait orientation
            for vf in sorted(video_files, key=lambda x: x.get("height", 0), reverse=True):
                if vf.get("height", 0) >= 720:
                    best = {
                        "download_url": vf["link"],
                        "width": vf.get("width", 0),
                        "height": vf.get("height", 0),
                        "pexels_id": video["id"],
                        "duration": dur,
                    }
                    break
            if best:
                break

    if not best:
        # Fallback: take any file from the first result
        video = videos[0]
        video_files = video.get("video_files", [])
        if video_files:
            vf = video_files[0]
            best = {
                "download_url": vf["link"],
                "width": vf.get("width", 0),
                "height": vf.get("height", 0),
                "pexels_id": video["id"],
                "duration": video.get("duration", 10),
            }

    if not best:
        return None

    # Download to assets/broll/ for caching
    filename = f"pexels_{best['pexels_id']}.mp4"
    download_path = BROLL_DIR / filename

    if download_path.exists():
        log("PEXELS", f"Using cached: {filename}", "OK")
        return {
            "video_path": str(download_path),
            "video_name": filename,
            "source": "pexels",
        }

    log("PEXELS", f"Downloading: {filename} ({best['duration']}s, {best['height']}p)...")

    try:
        import requests
        r = requests.get(best["download_url"], stream=True, timeout=60)
        r.raise_for_status()
        with open(download_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        # Trim to BROLL_OVERLAY_DURATION if needed
        if best["duration"] > BROLL_OVERLAY_DURATION + 1:
            trimmed_path = BROLL_DIR / f"pexels_{best['pexels_id']}_trimmed.mp4"
            trim_cmd = [
                FFMPEG_BIN, "-y", "-i", str(download_path), "-hide_banner",
                "-t", str(BROLL_OVERLAY_DURATION),
                "-c", "copy", str(trimmed_path),
            ]
            subprocess.run(trim_cmd, capture_output=True, timeout=30)
            if trimmed_path.exists():
                os.replace(str(trimmed_path), str(download_path))

        log("PEXELS", f"Downloaded: {filename}", "OK")
        return {
            "video_path": str(download_path),
            "video_name": filename,
            "source": "pexels",
        }

    except Exception as e:
        log("PEXELS", f"Download failed: {e}", "ERROR")
        return None
