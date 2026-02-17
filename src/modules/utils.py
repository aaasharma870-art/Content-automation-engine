
import os
import sys
import shutil
from pathlib import Path
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def log(module: str, message: str, level: str = "INFO"):
    """
    Structured logging with colors.
    Levels: INFO, WARN, ERR, OK, RENDER
    """
    ts = ""  # Timestamp could be added
    
    color = Fore.WHITE
    if level == "WARN": color = Fore.YELLOW
    if level == "ERR": color = Fore.RED
    if level == "OK": color = Fore.GREEN
    if level == "RENDER": color = Fore.CYAN
    
    print(f"{Fore.CYAN}[{module}]{Style.RESET_ALL} {color}{message}")

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
    """Locate FFprobe binary."""
    ffmpeg = get_ffmpeg_bin()
    return ffmpeg.replace("ffmpeg", "ffprobe")
