"""
asset_manager.py - Pre-flight Asset Verification
=================================================
Runs on pipeline startup to verify all required assets
(fonts, LUTs, SFX, models) exist. Auto-downloads missing fonts.
Subsumes the standalone download_fonts.py logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import FONTS_DIR, LUT_DIR, SFX_DIR, MUSIC_DIR, ASSETS_DIR
from src.utils.logger import log

# ── Required Assets ───────────────────────────────

REQUIRED_FONTS = ["Montserrat-Bold.ttf"]

OPTIONAL_FONTS = {
    "DejaVuSans-Bold.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf",
    "Oswald-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Bold.ttf",
    "Impact.ttf": "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf",
}

FONT_URLS = {
    "Montserrat-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf",
    **OPTIONAL_FONTS,
}

REQUIRED_LUT_FILES = ["cinematic.cube", "teal_orange.cube", "standard_rec709.cube"]

REQUIRED_SFX_SUBDIRS = ["transitions"]


def verify_all_assets() -> dict:
    """
    Check all required assets exist.

    Returns:
        dict with keys: fonts, luts, sfx, music — each a list of missing items.
        Empty lists mean everything is present.
    """
    missing = {"fonts": [], "luts": [], "sfx": [], "music": []}

    # Fonts
    for font in REQUIRED_FONTS:
        if not (FONTS_DIR / font).exists():
            missing["fonts"].append(font)

    # LUTs (warn but don't block — LUT application is optional)
    for lut in REQUIRED_LUT_FILES:
        if not (LUT_DIR / lut).exists():
            missing["luts"].append(lut)

    # SFX directories
    for subdir in REQUIRED_SFX_SUBDIRS:
        sfx_path = SFX_DIR / subdir
        sfx_path.mkdir(parents=True, exist_ok=True)
        has_files = any(sfx_path.glob("*.wav")) or any(sfx_path.glob("*.mp3"))
        if not has_files:
            missing["sfx"].append(subdir)

    # Music library
    music_files = []
    for ext in ["*.mp3", "*.wav", "*.m4a", "*.ogg", "*.flac"]:
        music_files.extend(MUSIC_DIR.glob(ext))
    # Also check subdirectories
    for ext in ["*.mp3", "*.wav", "*.m4a", "*.ogg", "*.flac"]:
        music_files.extend(MUSIC_DIR.rglob(ext))
    if not music_files:
        missing["music"].append("No music files found in assets/music/")

    # Report
    total_missing = sum(len(v) for v in missing.values())
    if total_missing == 0:
        log("ASSETS", "All assets verified.", "OK")
    else:
        if missing["fonts"]:
            log("ASSETS", f"Missing fonts: {missing['fonts']}", "WARN")
        if missing["luts"]:
            log("ASSETS", f"Missing LUTs: {missing['luts']} (visual_style grading will be skipped)", "WARN")
        if missing["sfx"]:
            log("ASSETS", f"Empty SFX dirs: {missing['sfx']} (transition SFX will be skipped)", "WARN")
        if missing["music"]:
            log("ASSETS", f"Music library: {missing['music']}", "WARN")

    return missing


def download_missing_fonts():
    """Download all missing fonts from known URLs."""
    import requests

    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    for name, url in FONT_URLS.items():
        path = FONTS_DIR / name
        if not path.exists():
            log("ASSETS", f"Downloading font: {name}...")
            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                path.write_bytes(r.content)
                log("ASSETS", f"Saved: {name}", "OK")
            except Exception as e:
                log("ASSETS", f"Failed to download {name}: {e}", "ERROR")
        else:
            log("ASSETS", f"Font exists: {name}", "OK")


def ensure_all_assets():
    """One-call convenience: verify + auto-fix what we can."""
    missing = verify_all_assets()
    if missing.get("fonts"):
        download_missing_fonts()
        # Re-check after download
        still_missing = [f for f in REQUIRED_FONTS if not (FONTS_DIR / f).exists()]
        if still_missing:
            log("ASSETS", f"CRITICAL: Could not obtain fonts: {still_missing}", "ERROR")
    return missing
