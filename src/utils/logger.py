"""
logger.py - Pipeline Logger
=============================
Centralized verbose logging for temporal synchronization tracking.
"""

import sys
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


def log(module: str, message: str, level: str = "INFO"):
    """
    Print a verbose, color-coded log message.

    Args:
        module: Module name (e.g., "INGEST", "BRAIN")
        message: Log message text
        level: "INFO", "OK", "WARN", "ERROR", "DEBUG"
    """
    colors = {
        "INFO": Fore.CYAN,
        "OK": Fore.GREEN,
        "WARN": Fore.YELLOW,
        "ERROR": Fore.RED,
        "DEBUG": Fore.MAGENTA,
        "RENDER": Fore.RED,
    }
    icons = {
        "INFO": "→",
        "OK": "✓",
        "WARN": "⚠",
        "ERROR": "✗",
        "DEBUG": "⚙",
        "RENDER": "▶",
    }

    color = colors.get(level, Fore.WHITE)
    icon = icons.get(level, "→")
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"{Fore.WHITE}[{ts}]{Style.RESET_ALL} "
          f"{color}[{module}]{Style.RESET_ALL} "
          f"{icon} {message}")
    sys.stdout.flush()
