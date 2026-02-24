"""
utils.py - Shared Utilities for Pipeline Modules
===================================================
Provides FFmpeg/FFprobe binary discovery and re-exports the canonical logger.
"""

import os
import sys
import shutil
from pathlib import Path

# Re-export the canonical logger so all modules can use `from src.modules.utils import log`
from src.utils.logger import log  # noqa: F401

def get_ffmpeg_bin():
    """
    Locate FFmpeg binary.
    Prioritizes bundled version, then system PATH, then imageio-ffmpeg.
    """
    # 1. Check for bundled generic path (from sister service)
    root = Path(__file__).resolve().parent.parent.parent.parent
    bundled = list(root.glob("ffmpeg-*/bin/ffmpeg.exe"))
    if bundled:
        return str(bundled[0])
        
    bundled_linux = list(root.glob("ffmpeg-*/bin/ffmpeg"))
    if bundled_linux:
        return str(bundled_linux[0])

    # 2. Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
        
    # 3. Check imageio-ffmpeg (pip install imageio-ffmpeg)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        pass

    # 4. Check environment variable
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
        
    raise FileNotFoundError("FFmpeg binary not found! Please install FFmpeg or imageio-ffmpeg.")

def get_ffprobe_bin():
    """
    Locate FFprobe binary.
    Prioritizes bundled version, then system PATH.
    """
    # 1. Check for bundled generic path (from sister service)
    root = Path(__file__).resolve().parent.parent.parent.parent
    bundled = list(root.glob("ffmpeg-*/bin/ffprobe.exe"))
    if bundled:
        return str(bundled[0])
        
    bundled_linux = list(root.glob("ffmpeg-*/bin/ffprobe"))
    if bundled_linux:
        return str(bundled_linux[0])

    # 2. Check system PATH
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe
        
    # 3. Check environment variable
    env_path = os.environ.get("FFPROBE_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
        
    # 4. Fallback to imageio-ffmpeg path hack (rarely works for ffprobe)
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if "ffmpeg" in ffmpeg_exe.lower():
            # Try to infer ffprobe path from ffmpeg path
            ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe")
            if os.path.isfile(ffprobe_exe):
                return ffprobe_exe
    except (ImportError, RuntimeError):
        pass
        
    # 5. Auto-Download Fallback (Windows only)
    import platform
    if platform.system() == "Windows":
        bin_dir = Path(__file__).resolve().parent.parent.parent / "bin"
        bin_dir.mkdir(exist_ok=True)
        ffprobe_exe = bin_dir / "ffprobe.exe"
        if ffprobe_exe.exists():
            return str(ffprobe_exe)
            
        log("UTILS", "FFprobe not found. Auto-downloading standalone Windows binary...", "WARN")
        try:
            import urllib.request
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            zip_path = bin_dir / "ffmpeg.zip"
            urllib.request.urlretrieve(url, str(zip_path))
            
            import zipfile
            with zipfile.ZipFile(str(zip_path), 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.endswith("ffprobe.exe"):
                        source = zip_ref.open(member)
                        target = open(str(ffprobe_exe), "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)
                        break
                        
            zip_path.unlink()
            if ffprobe_exe.exists():
                log("UTILS", "FFprobe installed successfully.", "OK")
                return str(ffprobe_exe)
        except Exception as e:
            log("UTILS", f"Auto-download failed: {e}", "ERROR")

    raise FileNotFoundError("FFprobe binary not found! Please install FFmpeg (which includes ffprobe) and add to PATH.")
