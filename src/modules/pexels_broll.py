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


def _simplify_query(query: str) -> str:
    """
    Simplify verbose LLM-generated b-roll queries into 2-4 word Pexels-optimized searches.
    Pexels API uses keyword matching, not semantic search. Long queries return garbage.
    """
    # Remove filler words that hurt keyword search
    STOP_WORDS = {
        "a", "an", "the", "of", "with", "and", "in", "on", "at", "to", "for",
        "is", "are", "was", "were", "being", "been", "be", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should", "may", "might",
        "shall", "can", "that", "this", "these", "those", "very", "really",
        "showing", "featuring", "displaying", "depicting", "illustrating",
        "close-up", "closeup", "wide-shot", "dramatic", "beautiful", "stunning",
        "amazing", "incredible", "powerful", "emotional", "intense",
    }
    words = query.lower().replace("-", " ").split()
    keywords = [w.strip(".,!?;:'\"") for w in words if w.strip(".,!?;:'\"") not in STOP_WORDS]

    # Take the first 3-4 meaningful keywords
    keywords = keywords[:4]

    if not keywords:
        # Fallback: just take first 3 words from original
        keywords = query.split()[:3]

    return " ".join(keywords)


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

    # Build contextual query: keep the semantic core, add quality modifiers
    visual_style = kwargs.get("visual_style", "")
    # Avoid appending overly generic style words that dilute search precision
    style_suffix = ""
    if visual_style:
        # Only use style if it adds meaningful context (not just "cinematic")
        useful_styles = [s for s in visual_style.lower().split()
                         if s not in ("cinematic", "default", "standard", "normal")]
        if useful_styles:
            style_suffix = " " + " ".join(useful_styles[:2])

    simplified = _simplify_query(query)
    enhanced_query = f"{simplified}{style_suffix}"
    log("PEXELS", f"Searching Pexels for: \"{enhanced_query[:60]}\"...")

    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": enhanced_query,
        "per_page": 10,
        "orientation": "portrait",
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

    # Retry with progressively simpler queries if no results
    if not videos:
        # Try just the first 2 keywords
        retry_query = " ".join(enhanced_query.split()[:2])
        if retry_query != enhanced_query:
            log("PEXELS", f"No results. Retrying with: \"{retry_query}\"")
            params["query"] = retry_query
            try:
                resp = requests.get("https://api.pexels.com/videos/search",
                                    headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                videos = data.get("videos", [])
            except Exception:
                pass

    if not videos:
        log("PEXELS", "No results found on Pexels after retry", "WARN")
        return None

    # Score and rank candidate videos by quality, duration fit, and resolution
    scored_candidates = []
    for video in videos:
        dur = video.get("duration", 999)
        if dur > duration_max:
            continue

        video_files = video.get("video_files", [])
        # Find the best quality file (prefer >= 1080p, then >= 720p)
        best_file = None
        for vf in sorted(video_files, key=lambda x: x.get("height", 0), reverse=True):
            h = vf.get("height", 0)
            if h >= 720 and vf.get("link"):
                best_file = vf
                break

        if not best_file and video_files:
            best_file = video_files[0]

        if best_file:
            height = best_file.get("height", 0)
            # Scoring: prefer 1080p+, portrait, and shorter duration
            res_score = 2 if height >= 1080 else (1 if height >= 720 else 0)
            dur_score = 1.0 - (dur / max(duration_max, 1))  # Shorter is better
            scored_candidates.append({
                "download_url": best_file["link"],
                "width": best_file.get("width", 0),
                "height": height,
                "pexels_id": video["id"],
                "duration": dur,
                "_score": res_score + dur_score,
            })

    # Sort by composite score (best first)
    scored_candidates.sort(key=lambda x: x["_score"], reverse=True)

    best = scored_candidates[0] if scored_candidates else None

    if not best:
        # Fallback: take any file from the first result regardless of duration
        video = videos[0]
        video_files = video.get("video_files", [])
        if video_files:
            vf = sorted(video_files, key=lambda x: x.get("height", 0), reverse=True)[0]
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
