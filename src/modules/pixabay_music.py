"""
pixabay_music.py - Pixabay Music API Fallback
================================================
When local music library has no tracks for a mood, queries the free
Pixabay Music API to download royalty-free background tracks.

API docs: https://pixabay.com/api/docs/#api-music
Free tier: 100 requests/minute, no attribution required.
Requires PIXABAY_API_KEY in .env (free signup at pixabay.com/api/docs).
"""

import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import MUSIC_DIR
from src.utils.logger import log


# Mood → Pixabay search query mapping
MOOD_QUERIES = {
    "cinematic": "cinematic dark dramatic",
    "upbeat": "energetic motivational",
    "tense": "suspense thriller dark",
    "lofi": "lofi chill hip hop",
    "neutral": "background ambient calm",
}


def search_pixabay_music(mood: str, duration_min: int = 60, duration_max: int = 180) -> str | None:
    """
    Search Pixabay for royalty-free music matching the mood.
    Downloads to assets/music/{mood}/ and caches for future use.

    Args:
        mood: One of cinematic/upbeat/tense/lofi/neutral
        duration_min: Minimum track duration in seconds
        duration_max: Maximum track duration in seconds

    Returns:
        Path to downloaded music file, or None
    """
    api_key = os.getenv("PIXABAY_API_KEY", "")
    if not api_key:
        log("PIXABAY_MUSIC", "No PIXABAY_API_KEY set. Auto-download disabled.", "WARN")
        return None

    try:
        import requests
    except ImportError:
        log("PIXABAY_MUSIC", "requests not installed", "ERROR")
        return None

    query = MOOD_QUERIES.get(mood, MOOD_QUERIES["neutral"])
    log("PIXABAY_MUSIC", f"Searching Pixabay Music for mood '{mood}': \"{query}\"...")

    params = {
        "key": api_key,
        "q": query,
        "per_page": 10,
    }

    try:
        resp = requests.get("https://pixabay.com/api/music/", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log("PIXABAY_MUSIC", f"API request failed: {e}", "ERROR")
        return None

    hits = data.get("hits", [])
    if not hits:
        log("PIXABAY_MUSIC", f"No results for mood '{mood}'", "WARN")
        return None

    # Filter by duration and pick best
    candidates = []
    for hit in hits:
        dur = hit.get("duration", 0)
        if duration_min <= dur <= duration_max:
            candidates.append(hit)

    if not candidates:
        candidates = hits[:3]  # Take top 3 regardless of duration

    best = candidates[0]
    audio_url = best.get("audio", "") or best.get("previewURL", "")
    if not audio_url:
        log("PIXABAY_MUSIC", "No download URL in result", "WARN")
        return None

    # Download to mood subdirectory
    mood_dir = MUSIC_DIR / mood
    mood_dir.mkdir(parents=True, exist_ok=True)

    filename = f"pixabay_{best['id']}.mp3"
    download_path = mood_dir / filename

    if download_path.exists():
        log("PIXABAY_MUSIC", f"Using cached: {filename}", "OK")
        return str(download_path)

    log("PIXABAY_MUSIC", f"Downloading: {filename} ({best.get('duration', '?')}s)...")

    try:
        r = requests.get(audio_url, stream=True, timeout=60)
        r.raise_for_status()
        with open(download_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        log("PIXABAY_MUSIC", f"Downloaded: {filename}", "OK")
        return str(download_path)

    except Exception as e:
        log("PIXABAY_MUSIC", f"Download failed: {e}", "ERROR")
        return None
