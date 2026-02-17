"""
ingest.py - The Watcher (Smart Downloader)
===========================================
Downloads YouTube videos via yt-dlp at max 1080p resolution.
Extracts a separate .wav audio file for Whisper processing.
Saves everything to data/raw/<video_id>/
"""

import re
import json
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import RAW_DIR, COOKIES_FILE
from src.utils.logger import log
from src.utils.ffmpeg_utils import FFMPEG_BIN


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
    Download a YouTube video and extract audio as .wav.

    Downloads:
    - Video: best quality up to 1080p (mp4)
    - Audio: .wav (16kHz mono, optimal for Whisper)
    - Metadata: JSON dump from yt-dlp

    Args:
        url: YouTube URL to download

    Returns:
        dict with: video_path, audio_wav_path, title, work_dir, metadata

    Raises:
        RuntimeError: If download fails
    """
    log("INGEST", f"Downloading: {url}")

    # Create a unique folder for this video
    video_id = _extract_video_id(url)
    work_dir = RAW_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Fetch metadata ───────────────────
    meta_cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--no-download", url]
    try:
        result = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=60)
        metadata = json.loads(result.stdout)
        title = _sanitize_filename(metadata.get("title", video_id))
        log("INGEST", f"Title: {title}")
    except Exception as e:
        log("INGEST", f"Metadata fetch failed, using ID: {e}", "WARN")
        metadata = {}
        title = video_id

    # Save metadata to disk
    meta_path = work_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)

    # ── Step 2: Download video (best mp4 up to 1080p) ─
    video_path = work_dir / f"{title}.mp4"
    
    video_cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(video_path),
        "--no-playlist",
    ]

    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        video_cmd.extend(["--cookies", str(COOKIES_FILE)])

    video_cmd.append(url)

    log("INGEST", "Downloading video (1080p)...")
    result = subprocess.run(video_cmd, capture_output=True, text=True, timeout=900)

    if result.returncode != 0:
        log("INGEST", f"yt-dlp stderr: {result.stderr[:300]}", "WARN")

    # ── Step 2b: Merge separate streams if needed ─
    # yt-dlp may download video+audio as separate files if ffmpeg isn't in PATH
    actual_video = _find_video_file(work_dir)
    audio_track = _find_audio_file(work_dir)
    
    if actual_video and audio_track:
        # Check if the video has an audio stream
        merged_path = work_dir / f"{title}_merged.mp4"
        log("INGEST", "Merging separate video + audio streams...")
        merge_cmd = [
            FFMPEG_BIN, "-y", "-hide_banner",
            "-i", str(actual_video),
            "-i", str(audio_track),
            "-c:v", "copy", "-c:a", "aac",
            "-strict", "experimental",
            str(merged_path),
        ]
        merge_result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=300)
        if merge_result.returncode == 0 and merged_path.exists():
            # Replace original with merged
            actual_video.unlink()
            audio_track.unlink()
            merged_path.rename(actual_video.parent / f"{title}.mp4")
            actual_video = actual_video.parent / f"{title}.mp4"
            log("INGEST", "Streams merged successfully.", "OK")
        else:
            log("INGEST", f"Merge failed: {merge_result.stderr[:200]}", "WARN")
    elif not actual_video:
        raise RuntimeError(f"No video file found in {work_dir}")

    # ── Step 3: Extract .wav audio (16kHz mono for Whisper) ─
    wav_path = work_dir / f"{title}.wav"
    wav_cmd = [
        FFMPEG_BIN, "-y", "-i", str(actual_video), "-hide_banner",
        "-vn",                    # No video
        "-acodec", "pcm_s16le",   # 16-bit PCM
        "-ar", "16000",           # 16kHz sample rate (Whisper optimal)
        "-ac", "1",               # Mono
        str(wav_path),
    ]

    log("INGEST", "Extracting audio as .wav (16kHz mono)...")
    result = subprocess.run(wav_cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        log("INGEST", f"WAV extraction failed: {result.stderr[:200]}", "WARN")
        wav_path = None
    else:
        log("INGEST", f"Audio extracted: {wav_path.name}", "OK")

    log("INGEST", f"Downloaded: {actual_video.name}", "OK")

    # ── Step 4: Calculate Motion Score (CV signal for Brain) ─
    motion_score = _calculate_motion_score(str(actual_video))
    log("INGEST", f"Motion score: {motion_score}", "OK")

    return {
        "video_path": str(actual_video),
        "audio_wav_path": str(wav_path) if wav_path and wav_path.exists() else None,
        "title": title,
        "work_dir": str(work_dir),
        "metadata": metadata,
        "motion_score": motion_score,
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
    return sanitized[:80].strip()


def _find_video_file(directory: Path) -> Path | None:
    """Find the largest .mp4 file in a directory."""
    for f in sorted(directory.glob("*.mp4"), key=lambda x: x.stat().st_size, reverse=True):
        return f
    return None


def _find_audio_file(directory: Path) -> Path | None:
    """Find a separate audio track (m4a/webm) from yt-dlp split download."""
    for ext in ["*.m4a", "*.webm", "*.opus"]:
        for f in sorted(directory.glob(ext), key=lambda x: x.stat().st_size, reverse=True):
            return f
    return None


def _calculate_motion_score(video_path: str, sample_count: int = 30) -> str:
    """
    Calculate average inter-frame pixel delta to classify visual dynamism.
    Used by the Brain to penalize visually static segments.

    Args:
        video_path: Path to the video file
        sample_count: Number of evenly-spaced frames to compare

    Returns:
        "low" (static/podcast), "medium" (casual vlog), or "high" (dynamic action)
    """
    try:
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            log("INGEST", "Could not open video for motion analysis", "WARN")
            return "unknown"

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < 2:
            cap.release()
            return "unknown"

        step = max(1, total_frames // sample_count)
        deltas = []
        prev_gray = None

        for i in range(0, min(total_frames, step * sample_count), step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                delta = float(np.mean(np.abs(gray.astype(float) - prev_gray.astype(float))))
                deltas.append(delta)
            prev_gray = gray

        cap.release()

        if not deltas:
            return "unknown"

        avg_delta = float(np.mean(deltas))
        if avg_delta < 5:
            return "low"
        elif avg_delta < 15:
            return "medium"
        else:
            return "high"
    except ImportError:
        log("INGEST", "OpenCV not available for motion analysis", "WARN")
        return "unknown"
    except Exception as e:
        log("INGEST", f"Motion analysis failed: {e}", "WARN")
        return "unknown"
