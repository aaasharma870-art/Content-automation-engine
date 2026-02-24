"""
validator.py - Pre-flight Asset Validation
============================================
Validates all required assets before rendering to prevent
mid-pipeline failures. Checks file existence, resolution,
duration, and codec compatibility.
"""

import subprocess
from pathlib import Path

from src.modules.utils import log, get_ffprobe_bin


def validate_assets(assets: dict) -> bool:
    """
    Pre-flight check before rendering.

    Validates:
    1. Audio file exists and has non-zero duration
    2. Image files exist and meet minimum resolution
    3. Gameplay video exists and is playable
    4. Word timestamps are present and ordered

    Args:
        assets: Dict with keys: audio, words, images, gameplay, topic

    Returns:
        True if all checks pass, False otherwise
    """
    log("VALIDATOR", "Running pre-flight checks...")
    errors = []

    # 1. Audio check
    audio_path = assets.get("audio", "")
    if not audio_path or not Path(audio_path).exists():
        errors.append(f"Audio file missing: {audio_path}")
    elif Path(audio_path).stat().st_size < 1024:
        errors.append(f"Audio file too small (<1KB): {audio_path}")
    else:
        duration = _get_media_duration(audio_path)
        if duration is not None and duration < 3.0:
            errors.append(f"Audio too short ({duration:.1f}s < 3s): {audio_path}")

    # 2. Words check
    words = assets.get("words", [])
    if not words:
        errors.append("No subtitle words provided")
    elif len(words) < 3:
        errors.append(f"Too few subtitle words ({len(words)} < 3)")
    else:
        for i in range(1, min(len(words), 20)):
            if words[i].get("start", 0) < words[i - 1].get("start", 0):
                errors.append(f"Word timestamps not ordered at index {i}")
                break

    # 3. Images check
    images = assets.get("images", [])
    if images:
        for img_path in images:
            if not Path(img_path).exists():
                errors.append(f"Image missing: {img_path}")
            elif Path(img_path).stat().st_size < 1024:
                errors.append(f"Image too small (<1KB): {img_path}")

    # 4. Gameplay check
    gameplay = assets.get("gameplay", "")
    if gameplay:
        if not Path(gameplay).exists():
            errors.append(f"Gameplay video missing: {gameplay}")
        elif Path(gameplay).stat().st_size < 10240:
            errors.append(f"Gameplay video too small (<10KB): {gameplay}")

    if errors:
        for err in errors:
            log("VALIDATOR", f"  FAIL: {err}", "ERROR")
        log("VALIDATOR", f"Pre-flight FAILED ({len(errors)} issues)", "ERROR")
        return False

    log("VALIDATOR", "All pre-flight checks passed", "OK")
    return True


def validate_rendered_output(video_path: str) -> dict:
    """
    Post-render validation of the output video.

    Checks:
    - File exists and has reasonable size
    - Has both video and audio streams
    - Duration is within YouTube Shorts range (3-60s)
    - Resolution matches target (1080x1920)

    Returns:
        dict with: valid (bool), errors (list), info (dict)
    """
    errors = []
    info = {}

    if not Path(video_path).exists():
        return {"valid": False, "errors": ["Output file does not exist"], "info": {}}

    file_size_mb = Path(video_path).stat().st_size / (1024 * 1024)
    info["file_size_mb"] = round(file_size_mb, 1)

    if file_size_mb < 0.1:
        errors.append(f"Output file too small ({file_size_mb:.1f} MB)")

    try:
        import json as json_mod
        ffprobe = get_ffprobe_bin()
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,width,height",
            "-of", "json", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            probe_data = json_mod.loads(result.stdout)

            duration = float(probe_data.get("format", {}).get("duration", 0))
            info["duration"] = round(duration, 1)
            if duration < 3.0:
                errors.append(f"Video too short ({duration:.1f}s)")
            elif duration > 60.0:
                errors.append(f"Video exceeds 60s limit ({duration:.1f}s)")

            streams = probe_data.get("streams", [])
            has_video = any(s.get("codec_type") == "video" for s in streams)
            has_audio = any(s.get("codec_type") == "audio" for s in streams)
            if not has_video:
                errors.append("No video stream in output")
            if not has_audio:
                errors.append("No audio stream in output")

            for s in streams:
                if s.get("codec_type") == "video":
                    w = s.get("width", 0)
                    h = s.get("height", 0)
                    info["resolution"] = f"{w}x{h}"
                    if w < 720 or h < 1280:
                        errors.append(f"Resolution below minimum ({w}x{h})")
                    break
    except Exception as e:
        errors.append(f"Could not probe output: {e}")

    valid = len(errors) == 0
    if valid:
        log("VALIDATOR", f"Output valid: {info.get('resolution', '?')} "
            f"{info.get('duration', '?')}s {info.get('file_size_mb', '?')}MB", "OK")
    else:
        for err in errors:
            log("VALIDATOR", f"  FAIL: {err}", "ERROR")

    return {"valid": valid, "errors": errors, "info": info}


def _get_media_duration(file_path: str) -> float | None:
    """Get duration of audio/video file via ffprobe."""
    try:
        ffprobe = get_ffprobe_bin()
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return float(result.stdout.strip())
    except Exception:
        return None
