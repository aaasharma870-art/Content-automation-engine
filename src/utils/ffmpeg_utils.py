"""
ffmpeg_utils.py - FFmpeg Binary Discovery
==========================================
Finds the FFmpeg executable through multiple fallback strategies:
1. System PATH (ffmpeg command)
2. imageio-ffmpeg bundled binary
3. Manual path from environment variable FFMPEG_PATH

Usage:
    from src.utils.ffmpeg_utils import FFMPEG_BIN
    cmd = [FFMPEG_BIN, "-y", "-i", ...]
"""

import os
import shutil


def _find_ffmpeg() -> str:
    """Discover FFmpeg binary path with multiple fallback strategies."""

    # 1. Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # 2. Check imageio-ffmpeg (pip install imageio-ffmpeg)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        pass

    # 3. Check environment variable
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 4. Last resort: just return "ffmpeg" and let it fail loudly
    raise RuntimeError(
        "FFmpeg not found! Install it via:\n"
        "  pip install imageio-ffmpeg\n"
        "  OR download from https://ffmpeg.org/download.html and add to PATH"
    )


# Module-level constant — import this everywhere
FFMPEG_BIN = _find_ffmpeg()
