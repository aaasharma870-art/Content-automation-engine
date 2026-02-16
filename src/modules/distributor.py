"""
distributor.py - Automated Social Media Distribution
======================================================
Handles scheduling and posting finished Shorts to:
- TikTok
- YouTube Shorts
- Instagram Reels

Uses Ayrshare unified API or direct platform APIs.
Generates platform-optimized metadata (titles, descriptions, hashtags).
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import AYRSHARE_API_KEY
from src.utils.logger import log


def schedule_posts(
    video_paths: list,
    clip_metadata: list,
    interval_hours: int = 24,
    platforms: list = None,
) -> list:
    """
    Schedule finished Shorts for sequential posting across platforms.

    Args:
        video_paths: List of rendered .mp4 file paths
        clip_metadata: List of clip dicts from brain.py (with title, desc, hashtags)
        interval_hours: Hours between each post (drip-feed)
        platforms: Target platforms ["tiktok", "youtube", "instagram"]

    Returns:
        List of scheduling result dicts
    """
    if platforms is None:
        platforms = ["tiktok", "youtube", "instagram"]

    if not AYRSHARE_API_KEY:
        log("DISTRIBUTOR", "No AYRSHARE_API_KEY set. Generating metadata files only.", "WARN")
        return _save_metadata_only(video_paths, clip_metadata, platforms)

    results = []
    post_time = datetime.utcnow() + timedelta(hours=1)  # Start 1hr from now

    for i, (video_path, clip) in enumerate(zip(video_paths, clip_metadata)):
        title = clip.get("proposed_title", f"Short_{i+1}")
        description = clip.get("description", "")
        hashtags = clip.get("hashtags", [])

        # Format for each platform
        caption = _format_caption(title, description, hashtags)

        log("DISTRIBUTOR", f"Scheduling: {title} → {', '.join(platforms)}")
        log("DISTRIBUTOR", f"  Post time: {post_time.isoformat()}")

        try:
            result = _post_via_ayrshare(
                video_path=video_path,
                caption=caption,
                platforms=platforms,
                schedule_time=post_time.isoformat() + "Z",
            )
            results.append({
                "video": video_path,
                "title": title,
                "status": "scheduled",
                "post_time": post_time.isoformat(),
                "result": result,
            })
            log("DISTRIBUTOR", f"Scheduled: {title}", "OK")
        except Exception as e:
            log("DISTRIBUTOR", f"Failed to schedule: {e}", "ERROR")
            results.append({
                "video": video_path,
                "title": title,
                "status": "failed",
                "error": str(e),
            })

        post_time += timedelta(hours=interval_hours)

    return results


def _post_via_ayrshare(video_path: str, caption: str,
                        platforms: list, schedule_time: str) -> dict:
    """Post via Ayrshare unified API."""
    import requests

    url = "https://app.ayrshare.com/api/post"
    headers = {
        "Authorization": f"Bearer {AYRSHARE_API_KEY}",
        "Content-Type": "application/json",
    }

    # For video, we need to upload first or provide a URL
    # Ayrshare accepts direct file upload via multipart
    upload_url = "https://app.ayrshare.com/api/media/upload"

    # Upload the video file
    with open(video_path, "rb") as f:
        upload_resp = requests.post(
            upload_url,
            headers={"Authorization": f"Bearer {AYRSHARE_API_KEY}"},
            files={"file": f},
        )

    if upload_resp.status_code != 200:
        raise RuntimeError(f"Upload failed: {upload_resp.text}")

    media_url = upload_resp.json().get("url", "")

    # Schedule the post
    payload = {
        "post": caption,
        "platforms": platforms,
        "mediaUrls": [media_url],
        "scheduleDate": schedule_time,
        "shortenLinks": False,
    }

    resp = requests.post(url, headers=headers, json=payload)

    if resp.status_code not in [200, 201]:
        raise RuntimeError(f"Post failed: {resp.text}")

    return resp.json()


def _save_metadata_only(video_paths: list, clip_metadata: list,
                         platforms: list) -> list:
    """
    When no API key is set, save metadata files alongside each video.
    User can manually upload with these descriptions.
    """
    results = []

    for i, (video_path, clip) in enumerate(zip(video_paths, clip_metadata)):
        title = clip.get("proposed_title", f"Short_{i+1}")
        description = clip.get("description", "")
        hashtags = clip.get("hashtags", [])

        meta = {
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "caption": _format_caption(title, description, hashtags),
            "platforms": platforms,
            "video_file": video_path,
            "virality_score": clip.get("virality_score", 0),
            "hook_text": clip.get("hook_text", ""),
        }

        # Save metadata file alongside video
        meta_path = Path(video_path).with_suffix(".meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        log("DISTRIBUTOR", f"Saved metadata: {meta_path.name}", "OK")
        results.append({"video": video_path, "title": title, "status": "metadata_saved"})

    return results


def _format_caption(title: str, description: str, hashtags: list) -> str:
    """Format a social media caption from components."""
    parts = []

    if title:
        parts.append(f"🔥 {title}")

    if description:
        parts.append(f"\n{description}")

    if hashtags:
        tag_str = " ".join(h if h.startswith("#") else f"#{h}" for h in hashtags)
        parts.append(f"\n\n{tag_str}")

    return "\n".join(parts)
