"""
config.py - Sovereign AI Pipeline Configuration
=================================================
Central configuration for the entire pipeline.
Loads secrets from .env and defines all path constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv



# ── Load Environment Variables ───────────────────
load_dotenv()

# ── API Keys ─────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")  # LM Studio: http://localhost:1234/v1
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")  # or "gpt-4o-mini", local model name, etc.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini" | "openai"

# Social Media Distribution
AYRSHARE_API_KEY = os.getenv("AYRSHARE_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# ── Paths ────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

# Data paths
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
TEMP_DIR = DATA_DIR / "temp"

# Asset paths
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
MUSIC_DIR = ASSETS_DIR / "music"
BROLL_DIR = ASSETS_DIR / "broll"
BROLL_INDEX_DIR = ASSETS_DIR / "broll_index"
LUT_DIR = ASSETS_DIR / "luts"

# Pipeline files
QUEUE_FILE = BASE_DIR / "queue.txt"
HISTORY_FILE = BASE_DIR / "history.txt"
ERRORS_LOG = BASE_DIR / "errors.log"
OUTPUT_DIR = PROCESSED_DIR  # Final shorts land here
COOKIES_FILE = BASE_DIR / "cookies.txt"

# ── Ensure directories exist ────────────────────
for d in [RAW_DIR, PROCESSED_DIR, TEMP_DIR, FONTS_DIR, MUSIC_DIR, BROLL_DIR, BROLL_INDEX_DIR, LUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Gold Tier (Local Cinema) ─────────────────────
USE_LOCAL_GENERATION = False    # Set to False to use Cloud (DALL-E/OpenAI) for stability check
GPU_VRAM_LIMIT = 12            # GB
SFX_DIR = ASSETS_DIR / "sfx"
(SFX_DIR / "transitions").mkdir(parents=True, exist_ok=True)
VOICE_MODEL_DIR = ASSETS_DIR / "models" / "rvc"

# ── Whisper Configuration ────────────────────────
WHISPER_MODEL = "large-v2"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"

# ── LLM / Brain Configuration ───────────────────
GEMINI_MAX_OUTPUT_TOKENS = 4096
GEMINI_TEMPERATURE = 0.4

# ── Video Constants ──────────────────────────────
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30
EXPORT_BITRATE = "25M"        # VBR target for social (20-30M preserves quality)
OUTPUT_BITRATE = EXPORT_BITRATE  # Alias for backward compatibility

# ── Audio Constants ──────────────────────────────
TARGET_LUFS = -24.0            # Per spec: -24 LUFS for voiceover (sidechain reference)
SILENCE_THRESHOLD_DB = -40
SILENCE_MIN_DURATION_MS = 500

# Sidechain Compression (Auto-ducking) — Professional Parameters
SIDECHAIN_THRESHOLD = 0.015
SIDECHAIN_RATIO = 3
SIDECHAIN_ATTACK = 1          # ms — instant drop when speech detected
SIDECHAIN_RELEASE = 500        # ms — smooth fade-back during pauses
MUSIC_VOLUME_DB = -14          # Base music volume before ducking (lower = subtler)

# ── Director Constants ───────────────────────────
FACE_SAMPLE_RATE = 4           # Lower = smoother tracking (was 10)
KALMAN_PROCESS_NOISE = 0.1     # Higher = faster response (was 0.03)

# ── Caption Styling (Hormozi Aesthetic) ──────────
CAPTION_FONT = "Montserrat-Bold"
CAPTION_FONT_SIZE = 70                   # Readable on mobile
CAPTION_PRIMARY_COLOR = "&H00FFFFFF"     # White base (BGR in ASS)
CAPTION_HIGHLIGHT_COLOR = "&H0000FFFF"   # Yellow highlight for active word
CAPTION_OUTLINE_COLOR = "&H00000000"     # Black outline
CAPTION_OUTLINE_WIDTH = 5                # Thicker outline for readability
CAPTION_SHADOW_DEPTH = 3
CAPTION_MARGIN_BOTTOM = 200              # Increased for safety (above UI)
CAPTION_MAX_CHARS = 15                   # Max chars on screen at once
CAPTION_UPPERCASE = True

# ── B-Roll (CLIP/FAISS) ─────────────────────────
CLIP_MODEL_NAME = "ViT-B/32"
BROLL_SAMPLE_FRAMES = 5      # Frames to extract per b-roll clip
BROLL_OVERLAY_DURATION = 3.0  # Seconds of b-roll to inject
BROLL_MIN_SIMILARITY = 0.25  # Review: Increased from 0.20 to reduce bad matches

# ── Pipeline Settings ────────────────────────────
POLL_INTERVAL_SECONDS = 30
MAX_CLIPS_PER_VIDEO = 5
CLIP_MIN_DURATION = 30
CLIP_MAX_DURATION = 60
CLIP_MAX_DURATION = 60
CAPTION_REVIEW_PAUSE = False   # Pause for human caption review before rendering
CRITIC_ENABLED = False         # Enable Multimodal Critic (Gemini Vision) for QA

# ── Safe Zones (TikTok/Reels UI) ─────────────────
# Percent of screen dimension to exclude
SAFE_ZONE_TOP = 0.15           # 15% top (Search, Live status)
SAFE_ZONE_BOTTOM = 0.35        # 35% bottom (Caption, handle, audio, CTA)
SAFE_ZONE_RIGHT = 0.15         # 15% right (Like, comment, share buttons)
SAFE_ZONE_LEFT = 0.02          # 2% left (minimal margin)

# ── NVENC Encoding ───────────────────────────────
USE_NVENC = True
NVENC_PRESET = "slow"
USE_HWACCEL_CUDA = True        # CUDA-accelerated decoding (requires NVIDIA GPU)

# ── Color Grading (LUTs) ────────────────────────
LUT_FILE = ""                  # Place .cube file in assets/luts/, set name here
                               # e.g. "cinematic_warm.cube"

# ── B-Roll Policy ──────────────────────────────
ALLOW_BROLL_FALLBACK = True    # Allow Pexels fallback when no CLIP match exists
PEXELS_CLIP_VERIFY = False     # True = CLIP-verify Pexels thumbnails (slower but accurate)

# ── Visual Style → LUT Mapping ─────────────────
VISUAL_STYLE_LUT_MAP = {
    "dark": "teal_orange.cube",
    "moody": "teal_orange.cube",
    "cinematic": "cinematic.cube",
    "bright": "standard_rec709.cube",
    "vlog": "standard_rec709.cube",
    "energetic": "vibrant.cube",
    "luxury": "cinematic.cube",
    "minimal": "standard_rec709.cube",
}

# ── Caption Emphasis Colors (ASS BGR format) ────
EMPHASIS_COLOR_KEY_NOUN = "&H0000FF00"       # Green
EMPHASIS_COLOR_KEY_ADJECTIVE = "&H0000FFFF"  # Yellow
EMPHASIS_COLOR_NEGATIVE = "&H000000FF"       # Red

# ── Audio Final Mix ────────────────────────────
SOCIAL_LUFS = -14              # Final output loudness (TikTok/Reels/Shorts standard)

# ── Dynamic Zoom ────────────────────────────────
DYNAMIC_ZOOM_INTENSITY = 1.05  # Max zoom factor (1.0 = off, 1.05 = subtle, 1.15 = punchy)

# ── Thumbnail Extraction ────────────────────────
THUMBNAIL_FRAME_COUNT = 20     # Candidate frames to score for best thumbnail

# ── AutoShorts Omni Configuration ────────────────
DEFAULT_MODE = "HYBRID" # HYBRID, VISUAL, GAMEPLAY
DEFAULT_VOICE = "en-US-ChristopherNeural"
VOICE_MATRIX = {
    "STORY": "en-US-ChristopherNeural",
    "NEWS": "en-US-GuyNeural",
    "FACTS": "en-US-EricNeural",
    "HORROR": "en-US-ChristopherNeural" # Deep voice
}
SAFETY_FILTERS = ["hate speech", "explicit", "self-harm", "violence"]

# Gameplay Source Channels (Fallback if local library empty)
GAMEPLAY_CHANNELS = ["@NoCopyrightGameplay", "@RelaxingGameplay"]
GAMEPLAY_DIR = ASSETS_DIR / "persistent" / "gameplay"
GAMEPLAY_DIR.mkdir(parents=True, exist_ok=True)

# Resource Governor
FFMPEG_THREADS = 2 # Prevent system freeze during parallel gen
