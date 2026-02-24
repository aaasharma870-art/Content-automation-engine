<p align="center">
  <h1 align="center">Content Automation Engine</h1>
  <p align="center">
    <strong>An autonomous AI pipeline that transforms long-form video, text prompts, and Reddit threads into platform-optimized short-form content — from ingestion to distribution — without human intervention.</strong>
  </p>
  <p align="center">
    <em>Python &middot; FFmpeg &middot; Whisper &middot; Gemini &middot; CLIP &middot; FAISS &middot; Stable Diffusion &middot; MediaPipe &middot; NVENC</em>
  </p>
</p>

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Motivation & Problem Statement](#motivation--problem-statement)
3. [Architecture](#architecture)
4. [Pipeline Modes](#pipeline-modes)
5. [Core Modules](#core-modules)
6. [Viral Retention Engineering](#viral-retention-engineering)
7. [Technical Highlights](#technical-highlights)
8. [Features](#features)
9. [Technology Stack](#technology-stack)
10. [Installation & Setup](#installation--setup)
11. [Usage](#usage)
12. [Configuration Reference](#configuration-reference)
13. [Project Structure](#project-structure)
14. [Performance & Output Specifications](#performance--output-specifications)
15. [Roadmap](#roadmap)
16. [Contributing](#contributing)
17. [License](#license)

---

## Project Overview

The **Content Automation Engine** is a production-grade, end-to-end AI system designed to solve a real bottleneck in digital media: the labor-intensive process of repurposing long-form content into short-form vertical clips optimized for TikTok, YouTube Shorts, and Instagram Reels.

The system operates across three distinct pipeline modes — **Repurpose** (URL-to-Shorts), **Generate** (Topic-to-AI-Video), and **Reddit Story** (Subreddit-to-TTS-Overlay) — each sharing a common rendering backbone that produces broadcast-quality output. In its autonomous "ghost employee" configuration, the engine monitors a queue file for YouTube URLs, downloads source material, transcribes with GPU-accelerated speech recognition, uses large language models to identify viral-worthy segments, performs intelligent 16:9-to-9:16 spatial reprojection with face tracking, applies broadcast-grade audio mastering, generates kinetic typography captions, injects semantically-matched B-roll footage, renders with hardware-accelerated encoding, and optionally distributes finished clips across social platforms — all without manual intervention.

**What makes this technically significant:**

- **15,000+ lines of Python** across 20+ specialized modules spanning NLP, computer vision, audio engineering, video rendering, and generative AI
- **Three production pipeline modes** with shared rendering infrastructure and context-aware asset selection
- **Real-time computer vision** using MediaPipe Face Mesh and Kalman filtering for cinematic camera tracking
- **Multimodal AI integration** spanning speech-to-text (Whisper), language understanding (Gemini/GPT-4), image-text alignment (CLIP), vector search (FAISS), image generation (SDXL Turbo), and video synthesis (Stable Video Diffusion)
- **Broadcast-standard audio processing** including EBU R128 loudness normalization, sidechain compression, silence removal, and multi-layer mixing with context-aware music selection
- **Production infrastructure** with Docker Compose orchestrating PostgreSQL, MinIO, N8N, Grafana, and application microservices

---

## Motivation & Problem Statement

The short-form video market has exploded: TikTok, YouTube Shorts, and Instagram Reels collectively serve billions of daily views. Content creators sitting on hours of long-form footage face a bottleneck — turning a 60-minute podcast into five polished, platform-ready Shorts requires:

1. **Manual clip selection** — watching the entire video and identifying emotionally compelling moments
2. **Aspect ratio conversion** — cropping 16:9 to 9:16 while keeping subjects intelligently framed
3. **Audio mastering** — normalizing loudness to platform standards, removing dead air, mixing background music with voice-aware ducking
4. **Caption generation** — transcribing speech, timing word-level subtitles, and styling them for mobile readability
5. **Visual enhancement** — adding contextually relevant B-roll, transitions, color grading, and thumbnail extraction
6. **Platform distribution** — uploading with optimized metadata to multiple platforms simultaneously

Each step traditionally requires a skilled editor and hours of manual work per clip. This engine automates the entire workflow, reducing turnaround from hours to minutes while maintaining professional-grade quality.

The project required integrating knowledge across six distinct technical domains — **natural language processing** (LLM prompt engineering and constrained JSON generation), **computer vision** (face detection, landmark tracking, spatial reprojection), **signal processing** (LUFS loudness normalization, sidechain compression, psychoacoustic gating), **information retrieval** (cross-modal embedding with CLIP, approximate nearest-neighbor search with FAISS), **generative AI** (diffusion models for image and video synthesis), and **systems engineering** (GPU resource management, containerized deployment, fault-tolerant pipeline design). The challenge was not any single domain in isolation, but building a system where all six domains operate cohesively under real-world constraints: limited VRAM, variable input quality, and strict platform specifications.

---

## Architecture

The engine follows a **modular pipeline architecture** where each stage operates independently, communicating through well-defined data contracts (JSON manifests and file paths). This enables parallel development, isolated testing, and straightforward extension.

```
                         CONTENT AUTOMATION ENGINE
┌─────────────────────────────────────────────────────────────────────────────┐
│                           THREE PIPELINE MODES                              │
│                                                                             │
│  ┌─────────────┐    ┌─────────────────┐    ┌──────────────────────┐        │
│  │  REPURPOSE   │    │    GENERATE      │    │    REDDIT STORY      │        │
│  │  URL -> Clip │    │  Topic -> Video  │    │  Subreddit -> TTS    │        │
│  │              │    │                  │    │    + Gameplay         │        │
│  │  YouTube URL │    │  LLM Script Gen  │    │  JSON API Scrape     │        │
│  │  yt-dlp DL   │    │  Edge-TTS Voice  │    │  Edge-TTS Narration  │        │
│  │  Whisper STT │    │  DALL-E / SDXL   │    │  Gameplay Background │        │
│  │  LLM Scoring │    │  Ken Burns FX    │    │  Dynamic Concat      │        │
│  │  Face Track  │    │  Flash Cuts      │    │  Word-level Subs     │        │
│  └──────┬───────┘    └───────┬──────────┘    └──────────┬───────────┘        │
│         │                    │                          │                    │
│         └────────────────────┼──────────────────────────┘                    │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    SHARED RENDERING BACKBONE                         │   │
│  │                                                                      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │  AUDIO   │ │ CAPTIONS │ │  B-ROLL  │ │  RENDER  │ │   QA     │  │   │
│  │  │ Sidechain│ │ Hormozi  │ │ CLIP+    │ │ NVENC    │ │ Gemini   │  │   │
│  │  │ LUFS     │ │ Karaoke  │ │ FAISS    │ │ libx264  │ │ Vision   │  │   │
│  │  │ Context  │ │ Emphasis │ │ Pexels   │ │ Fallback │ │ SafeZone │  │   │
│  │  │ Music    │ │ Pop FX   │ │ Scored   │ │ Chain    │ │ Check    │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       DISTRIBUTION                                   │   │
│  │            Ayrshare API  |  TikTok  |  YouTube  |  Instagram         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Modes

### Mode 1: Repurpose (URL-to-Shorts)

The primary pipeline. Transforms long-form YouTube videos into multiple platform-ready Shorts.

| Stage | Module | Description |
|-------|--------|-------------|
| **Ingest** | `ingest.py` | Downloads video at 1080p via yt-dlp with cookie auth support. Extracts 16kHz mono WAV for Whisper. |
| **Transcribe** | `transcribe.py` | GPU-accelerated speech-to-text via faster-whisper (large-v2, CUDA fp16). Produces word-level timestamps with sub-100ms accuracy. |
| **Brain** | `brain.py` | LLM-powered virality engine. Sends full transcript to Gemini 1.5 Flash with chain-of-thought prompting. Scores segments on four axes: Hook, Flow, Value, Trend. Outputs content mood classification for music selection. |
| **Director** | `director.py` | 16:9-to-9:16 spatial reprojection. MediaPipe Face Mesh + Kalman filter for cinematic crop tracking. Letterbox+blur fallback for non-face content. |
| **Editor** | `editor.py` | Audio mastering (LUFS, sidechain, silence removal), Hormozi-style karaoke captions, B-roll overlay, LUT color grading, hook zoom effect, brand watermark, and 3-stage progressive render with NVENC/libx264 fallback. |
| **Distribute** | `distributor.py` | Automated scheduling to TikTok, YouTube Shorts, Instagram Reels via Ayrshare API. Generates `.meta.json` fallback files when no API key is configured. |

### Mode 2: Generate (Topic-to-AI-Video)

Creates original short-form content from a text prompt.

| Stage | Module | Description |
|-------|--------|-------------|
| **Mine** | `miner.py` | LLM generates a structured story (Hook + Body + CTA) with image generation keywords. Manages gameplay background library. |
| **Voice** | `audio.py` | Edge-TTS narration with voice matrix (Christopher, Guy, Eric, Steffan) matched to content archetype. R128 normalization and silence removal. |
| **Vision** | `vision.py` / `foundry.py` | DALL-E 3 or local SDXL Turbo for scene images. SVD for image-to-video animation (25 frames at 6fps). |
| **Render** | `render_gen.py` | Ken Burns effect with 5 motion variants on static images. Proper crossfade transitions between scenes. Flash cut filter chains for dynamic visuals. |
| **Validate** | `validator.py` | Pre-flight asset validation (audio duration, image existence, word timestamp ordering) and post-render output verification (resolution, streams, duration). |

### Mode 3: Reddit Story (Subreddit-to-TTS)

Scrapes viral Reddit stories and overlays TTS narration on gameplay footage.

| Stage | Module | Description |
|-------|--------|-------------|
| **Scrape** | `reddit.py` | Fetches top posts from any subreddit via Reddit's public JSON API. Filters by upvote count and character length. |
| **Narrate** | `reddit.py` | Edge-TTS with the Steffan voice (high-energy cadence). Word-level subtitle alignment via faster-whisper. |
| **Background** | `reddit.py` | Dynamically concatenates gameplay clips from a library directory to match narration duration. Supports single-file looping or multi-file concatenation. |
| **Compose** | `reddit.py` | Overlays semi-transparent text cards, word-by-word subtitles, and background music. Context-aware music selection defaults to "lofi" mood for story content. |

---

## Core Modules

### Brain — LLM Virality Engine (`brain.py`)

The intelligence core. Analyzes transcripts through a meticulously engineered system prompt that enforces chain-of-thought reasoning:

1. Read the full narrative arc
2. Identify emotional peaks, surprising reveals, and debate-worthy claims
3. Score each candidate segment on **Hook** (0-99), **Flow** (0-99), **Value** (0-99), **Trend** (0-99)
4. Classify content mood (`cinematic`, `upbeat`, `tense`, `lofi`, `neutral`) for downstream music selection
5. Tag emphasis words by type (`key_noun`, `key_adjective`, `negative`) for caption coloring
6. Identify impact moments for transition SFX placement
7. Generate B-roll search queries and insertion timestamps

Enforces clip duration constraints (30-60s), prohibits mid-sentence cuts, and requires each clip to open with a strong hook.

### Director — Spatial Reprojection (`director.py`)

Real-time 16:9-to-9:16 conversion without blind center-cropping:

1. **MediaPipe Face Mesh** detects 468 facial landmarks at configurable frame intervals
2. **Active Speaker Detection** identifies which face is speaking by measuring lip movement variance
3. **Kalman Filter** smooths the crop window trajectory, simulating a virtual gimbal
4. **Fallback** — when no faces are detected (screen shares, B-roll), letterboxing with blurred background fill

### Editor — Post-Production (`editor.py`)

The largest module. Four critical subsystems:

**Audio Engineering:**
- LUFS normalization targeting -14 LUFS (social media standard)
- Sidechain compression with 1ms attack, 500ms release, 3:1 ratio auto-ducking
- Silence removal with -40dB threshold gating
- Context-aware music selection using content mode, visual style, and title keyword signals

**Kinetic Typography:**
- Hormozi-style `.ass` subtitles with word-by-word karaoke animation
- Pop-in scale animation (90% to 100% over 100ms per line)
- Emphasis word detection with yellow color override for high-impact words
- Semantic coloring via Brain's emphasis map (green/yellow/red)
- Emoji injection from 100+ keyword mapping
- Safe zone positioning (vertically centered in readable zone, above platform UI)

**Hook Optimization:**
- Punch-zoom effect in first 2 seconds (1.0x to 1.12x over 0.6s, ease back to 1.0x over 1.4s)
- Brand watermark with cross-platform font resolution

**Rendering:**
- 3-stage progressive render: NVENC full -> libx264 full -> libx264 safe (stripped filters)
- Post-render validation: checks resolution, streams, duration, file size
- 25 Mbps VBR at 1080x1920 @ 30fps with `faststart` flag

### Semantic B-Roll Engine (`broll.py` + `pexels_broll.py`)

Cross-modal visual search using CLIP and FAISS:

1. **Indexing** — extracts frames from local B-roll library, encodes through CLIP ViT-B/32, builds FAISS vector index
2. **Query** — LLM-generated natural-language descriptions encoded through CLIP text encoder
3. **Retrieval** — cosine similarity search with 0.25 minimum threshold
4. **Pexels Fallback** — stock footage API with resolution scoring (prefers 1080p+ portrait), duration fit ranking, and deduplication
5. **Validation** — selected B-roll verified for file existence and minimum resolution

### Context-Aware Music Selection (`editor.py`)

Multi-signal music matching replacing the previous random selection:

| Signal | Priority | Example |
|--------|----------|---------|
| Title keywords | Highest | "horror" -> `tense/`, "money" -> `upbeat/` |
| Visual style | High | "dark moody" -> `cinematic/` |
| Content mode | Medium | Reddit -> `lofi/`, Generate -> `cinematic/` |
| Default | Lowest | `neutral/` |

Supports five mood directories: `cinematic/`, `upbeat/`, `neutral/`, `tense/`, `lofi/`. Falls back to root music directory, then recursive search.

---

## Viral Retention Engineering

### Proof List Scripts

The LLM generates scripts in a rigid **Hook -> 3 Proofs -> Rehook** structure:

- **Hook** (5-8 seconds) — attention-grabbing opening
- **Proof 1, 2, 3** — supporting evidence points, each 8-12 seconds
- **Rehook** — callback to the opening for narrative closure
- Enforced 140-word limit to maintain pacing (~55 seconds at natural speech rate)

### Flash Cuts (`render_gen.py`)

Three randomized zoom/pan animation patterns per clip:

| Pattern | Motion | Expression |
|---------|--------|------------|
| Pan | Smooth rightward drift | `crop=...:(t*50):...` |
| Drift | Diagonal top-left to center | `crop=...:t*30:t*20` |
| Chaos | Sinusoidal oscillation | `crop=...:sin(t*3)*100:cos(t*2)*80` |

Source upscaled to 1.5x target resolution, then a 1080x1920 crop window animates across the canvas.

### Ken Burns Effect (`render_gen.py`)

Five motion variants for static image slideshows:

1. Zoom in center
2. Zoom out center
3. Zoom in from left edge
4. Zoom in from right edge
5. Zoom out from top

Applied with proper xfade crossfade transitions between slides.

### Micro-SFX / J-Cuts (`audio.py`)

- 200ms overlapping audio transitions between segments
- -45dB silence threshold gating
- Whoosh SFX at 1.4s and 2.8s intervals within each 4-second block, synchronized to visual Flash Cut timing
- SFX volume at -20dB (subliminal — felt, not consciously heard)

---

## Technical Highlights

This project demonstrates applied competency across multiple computer science and engineering domains:

### Signal Processing & Audio Engineering
- Implementation of **EBU R128 loudness normalization** (ITU-R BS.1770 standard) with two-pass measurement and linear correction
- Real-time **sidechain compression** with configurable attack/release envelopes for voice-aware music ducking
- Psychoacoustic **silence gating** with minimum duration constraints to preserve natural speech rhythm
- Multi-layer audio mixing pipeline: voice + sidechain-ducked music + subliminal transition SFX

### Computer Vision & Spatial Reasoning
- Real-time **face detection** and 468-point landmark extraction using MediaPipe Face Mesh
- **Active speaker identification** through inter-frame lip movement variance analysis
- **Kalman filter** implementation for temporally smooth crop trajectory estimation (simulating a virtual gimbal)
- Multi-factor **frame quality scoring** combining Laplacian sharpness, luminance distribution, color vibrancy, contrast, and rule-of-thirds face positioning

### Natural Language Processing & Prompt Engineering
- **Chain-of-thought prompting** that forces structured analytical reasoning before segment selection
- Constrained **JSON output generation** with regex-based fallback parsing and error recovery
- Multi-axis **virality scoring** (Hook, Flow, Value, Trend) with cross-validation between dimensions
- **Enumeration pattern detection** via regex for automatic listicle identification in transcripts
- **Content mood classification** that propagates through the pipeline to inform music, visual style, and caption treatment

### Information Retrieval & Vector Search
- **CLIP-based cross-modal embedding** enabling natural-language text queries against video frame databases
- **FAISS index** construction and approximate nearest-neighbor search for sub-second B-roll retrieval
- Cosine similarity thresholding with graceful **fallback cascade** to external stock footage APIs
- Resolution-weighted **scoring model** for Pexels API results (1080p+ preference, duration fit, deduplication)

### Generative AI
- **Stable Diffusion XL Turbo** for single-step high-quality image synthesis from text prompts
- **Stable Video Diffusion** (SVD-XT) for image-to-video animation at 6fps with configurable motion intensity
- Strict serial execution with **VRAM management** — automatic model unloading, garbage collection, and CPU offload to fit within consumer GPU memory

### Systems Engineering
- **3-stage progressive render** fallback chain (NVENC -> libx264 full -> libx264 safe) ensuring output under all hardware configurations
- **Pre-flight and post-render validation** catching asset issues before expensive rendering and verifying output integrity after
- Cross-platform **binary resolution** for FFmpeg/FFprobe with bundled, system PATH, imageio-ffmpeg, and auto-download fallbacks
- **Idempotent pipeline design** with caching at every stage (downloads, transcripts, FAISS indices)
- Docker Compose orchestration of **7 microservices** with health checks, persistent volumes, and automatic restart policies

---

## Features

### Content Intelligence
- Chain-of-thought LLM virality scoring across four dimensions
- Content mood classification for context-aware asset selection
- Emphasis word detection and semantic caption coloring
- Impact moment identification for SFX placement
- Visual viability scoring to penalize static segments

### Video Processing
- 16:9-to-9:16 intelligent spatial reprojection with face tracking
- Kalman-filtered cinematic camera panning
- Ken Burns effect with 5 motion variants and crossfade transitions
- Flash cut animation patterns for maximum visual dynamism
- Punch-zoom hook optimization for the first 2 seconds
- LUT color grading (cinematic, teal-orange, standard rec709)
- Brand watermark with cross-platform font resolution

### Audio Engineering
- EBU R128 loudness normalization (two-pass measurement + correction)
- Sidechain compression with configurable attack/release envelopes
- Psychoacoustic silence gating with minimum duration constraints
- Context-aware background music selection (5 mood categories)
- Multi-layer mixing: voice + ducked music + transition SFX

### Caption System
- Word-by-word Hormozi-style karaoke animation
- Pop-in scale effect per line
- Emphasis word highlighting (yellow override for high-impact words)
- Semantic coloring (green for key nouns, yellow for adjectives, red for negatives)
- Automatic emoji injection (100+ keyword mappings)
- Safe zone compliance (positioned above TikTok/Reels UI)

### Quality Assurance
- Pre-flight asset validation (audio, images, words, gameplay)
- Post-render output verification (resolution, streams, duration, file size)
- Optional Gemini Vision multimodal QA gate
- 3-stage progressive render fallback (NVENC -> libx264 full -> libx264 safe)

### Distribution
- Automated posting to TikTok, YouTube Shorts, Instagram Reels via Ayrshare
- Drip-feed scheduling with configurable intervals
- Platform-optimized metadata generation
- `.meta.json` fallback for manual upload workflows

---

## Technology Stack

| Category | Technologies |
|----------|-------------|
| **Core Language** | Python 3.10+ |
| **Video Processing** | FFmpeg (NVENC GPU encoding, CUDA decoding, complex filter graphs) |
| **Speech Recognition** | faster-whisper (CTranslate2, large-v2, CUDA fp16) |
| **Language Models** | Google Gemini 1.5 Flash, OpenAI GPT-4o, Anthropic Claude, Ollama (local) |
| **Computer Vision** | OpenCV, MediaPipe Face Mesh, Haar Cascades |
| **Semantic Search** | OpenAI CLIP (ViT-B/32), FAISS |
| **Generative AI** | SDXL Turbo, Stable Video Diffusion, DALL-E 3 |
| **Text-to-Speech** | Edge-TTS (Microsoft Neural Voices) |
| **Audio Processing** | pydub, FFmpeg (LUFS loudnorm, sidechain, silence gating) |
| **Infrastructure** | Docker Compose, PostgreSQL, MinIO (S3), N8N, Grafana |
| **Distribution** | Ayrshare API (TikTok, YouTube, Instagram) |
| **Stock Footage** | Pexels API (scored retrieval with resolution ranking) |
| **Scene Detection** | PySceneDetect (ContentDetector) |

### Hardware Acceleration

- **NVIDIA NVENC** for real-time H.264 encoding
- **CUDA** for GPU-accelerated video decoding and Whisper inference
- **PyTorch CUDA** for CLIP embeddings, SDXL Turbo, and SVD inference

---

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- NVIDIA GPU with CUDA support (RTX 3060+ recommended, 12GB VRAM for local generation)
- FFmpeg (system install or bundled via `imageio-ffmpeg`)
- yt-dlp (`pip install yt-dlp`)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/aaasharma870-art/Content-automation-engine.git
cd Content-automation-engine

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate    # Linux/Mac
# venv\Scripts\activate     # Windows

# 3. Install PyTorch with CUDA (must be first)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 4. Install CLIP
pip install git+https://github.com/openai/CLIP.git@main

# 5. Install dependencies
pip install -r requirements.txt

# 6. Configure environment
cp .env.example .env
# Edit .env:
#   GOOGLE_API_KEY=your_gemini_key          (required for Brain)
#   PEXELS_API_KEY=your_pexels_key          (optional, B-roll fallback)
#   AYRSHARE_API_KEY=your_ayrshare_key      (optional, auto-distribution)

# 7. Launch
python run.py
```

### Docker Deployment

```bash
cp .env.example .env
# Edit .env with your API keys and settings

# Launch the full stack
docker-compose up -d

# Monitor
docker-compose logs -f orchestrator
```

### Directory Setup

The engine automatically creates required directories on first run:

```
assets/
  music/          # Background music (organize into cinematic/, upbeat/, neutral/, tense/, lofi/)
  broll/          # Local B-roll video clips (indexed by CLIP)
  fonts/          # Auto-downloads Montserrat-Bold if missing
  luts/           # Color grading LUT files (.cube)
  sfx/transitions # Transition sound effects (.wav/.mp3)
  persistent/gameplay  # Gameplay footage for Reddit Story mode
data/
  raw/            # Downloaded source videos
  processed/      # Rendered output shorts
  temp/           # Working files (auto-cleaned)
```

---

## Usage

### Interactive Mode (Recommended)

```bash
python run.py
```

Presents a menu with all three pipeline modes:

```
Select Mode:
[1] Repurpose Video (URL -> Viral Shorts)
[2] Generate New (Topic -> AI Story)
[3] Reddit Story (Subreddit -> TTS + Gameplay)
[q] Quit
```

### Autonomous Queue Mode

Runs as a persistent daemon, polling `queue.txt` every 30 seconds:

```bash
# Add URLs to the processing queue
echo "https://www.youtube.com/watch?v=VIDEO_ID" >> queue.txt

# Start the daemon
python main.py
```

Processed URLs are moved to `history.txt`. Errors are logged to `errors.log`.

### Pipeline-Specific Examples

**Repurpose a YouTube video:**
```bash
python run.py
# Select [1], paste URL
# Output: data/processed/<title>_<proposed_title>_S<score>.mp4
```

**Generate an AI video from a topic:**
```bash
python run.py
# Select [2], enter topic: "Why discipline beats motivation"
# Output: data/processed/temp_slideshow.mp4
```

**Reddit Story with gameplay background:**
```bash
python run.py
# Select [3], enter subreddit: "TrueOffMyChest"
# Enter gameplay video path or leave blank for auto-selection
# Output: data/processed/reddit_story_<title>.mp4
```

---

## Configuration Reference

All configuration is centralized in `config.py`. Key parameters:

### Video Output
| Parameter | Default | Description |
|-----------|---------|-------------|
| `TARGET_WIDTH` | `1080` | Output width (9:16 vertical) |
| `TARGET_HEIGHT` | `1920` | Output height |
| `TARGET_FPS` | `30` | Output frame rate |
| `EXPORT_BITRATE` | `25M` | VBR target bitrate |
| `USE_NVENC` | `True` | Enable NVIDIA hardware encoding |
| `USE_HWACCEL_CUDA` | `True` | CUDA-accelerated decoding |

### Audio
| Parameter | Default | Description |
|-----------|---------|-------------|
| `TARGET_LUFS` | `-24.0` | Voiceover loudness target |
| `SOCIAL_LUFS` | `-14` | Final mix loudness (social media standard) |
| `MUSIC_VOLUME_DB` | `-20` | Background music level |
| `SIDECHAIN_RATIO` | `3` | Music ducking compression ratio |
| `SIDECHAIN_ATTACK` | `1` | Attack time in ms |
| `SIDECHAIN_RELEASE` | `500` | Release time in ms |

### Captions
| Parameter | Default | Description |
|-----------|---------|-------------|
| `CAPTION_FONT` | `Montserrat-Bold` | Subtitle font family |
| `CAPTION_FONT_SIZE` | `70` | Font size (mobile-optimized) |
| `CAPTION_MAX_CHARS` | `15` | Max characters per caption line |
| `CAPTION_UPPERCASE` | `True` | Force uppercase text |
| `CAPTION_MARGIN_BOTTOM` | `600` | Bottom margin (safe zone) |

### Brain & LLM
| Parameter | Default | Description |
|-----------|---------|-------------|
| `WHISPER_MODEL` | `large-v2` | Whisper model size |
| `WHISPER_DEVICE` | `cuda` | Inference device |
| `GEMINI_TEMPERATURE` | `0.4` | LLM temperature for Brain analysis |
| `MAX_CLIPS_PER_VIDEO` | `3` | Maximum shorts per source video |
| `CLIP_MIN_DURATION` | `30` | Minimum clip length (seconds) |
| `CLIP_MAX_DURATION` | `59.5` | Maximum clip length (YouTube Shorts limit) |

### B-Roll & Assets
| Parameter | Default | Description |
|-----------|---------|-------------|
| `CLIP_MODEL_NAME` | `ViT-B/32` | CLIP model for semantic search |
| `BROLL_MIN_SIMILARITY` | `0.25` | Minimum cosine similarity threshold |
| `BROLL_OVERLAY_DURATION` | `3.0` | B-roll overlay duration (seconds) |
| `ALLOW_BROLL_FALLBACK` | `True` | Enable Pexels stock footage fallback |

### Director
| Parameter | Default | Description |
|-----------|---------|-------------|
| `FACE_SAMPLE_RATE` | `4` | Frame interval for face detection |
| `KALMAN_PROCESS_NOISE` | `0.1` | Kalman filter responsiveness |
| `DYNAMIC_ZOOM_INTENSITY` | `1.05` | Maximum dynamic zoom factor |

### Safe Zones
| Parameter | Default | Description |
|-----------|---------|-------------|
| `SAFE_ZONE_TOP` | `15%` | Reserved for platform search/status UI |
| `SAFE_ZONE_BOTTOM` | `35%` | Reserved for caption/handle/CTA UI |
| `SAFE_ZONE_RIGHT` | `15%` | Reserved for like/comment/share buttons |

---

## Project Structure

```
Content-automation-engine/
├── main.py                        # Autonomous daemon (queue monitor + pipeline runner)
├── run.py                         # Interactive launcher (all 3 modes)
├── config.py                      # Centralized configuration (190+ lines, 60+ parameters)
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
│
├── src/
│   ├── main.py                    # Alternate entry point with FFmpeg path injection
│   │
│   ├── modules/
│   │   ├── brain.py               # LLM virality scoring (Gemini/GPT, chain-of-thought)
│   │   ├── ingest.py              # YouTube downloader (yt-dlp, 1080p, cookie auth)
│   │   ├── transcribe.py          # Speech-to-text (faster-whisper, CUDA, word-level)
│   │   ├── director.py            # Spatial reprojection (MediaPipe, Kalman filter)
│   │   ├── editor.py              # Post-production (audio, captions, render, music)
│   │   ├── audio.py               # Audio engineering (TTS, J-cuts, SFX, crossfade)
│   │   ├── broll.py               # Semantic B-roll search (CLIP + FAISS index)
│   │   ├── pexels_broll.py        # Pexels stock footage API (scored retrieval)
│   │   ├── render_gen.py          # Generative video rendering (Ken Burns, flash cuts)
│   │   ├── miner.py               # Content mining (LLM story gen, scene detect)
│   │   ├── foundry.py             # Local AI generation (SDXL Turbo + SVD)
│   │   ├── vision.py              # DALL-E 3 image generation
│   │   ├── critic.py              # Multimodal QA agent (Gemini Vision)
│   │   ├── thumbnail.py           # AI thumbnail selection (aesthetic scoring)
│   │   ├── distributor.py         # Social media scheduling (Ayrshare API)
│   │   ├── validator.py           # Asset validation and output verification
│   │   └── utils.py               # FFmpeg/FFprobe binary resolution, logger re-export
│   │
│   ├── pipelines/
│   │   ├── repurpose.py           # Mode 1: Long-form URL -> short-form clips
│   │   ├── generate.py            # Mode 2: Topic -> AI-generated video
│   │   └── reddit.py              # Mode 3: Reddit story -> TTS + gameplay overlay
│   │
│   └── utils/
│       ├── logger.py              # Timestamped color-coded logging (canonical)
│       ├── asset_manager.py       # Asset verification and font auto-download
│       ├── emoji_map.py           # 100+ keyword-to-emoji mapping for captions
│       └── ffmpeg_utils.py        # FFmpeg binary discovery utilities
│
├── shared/
│   ├── llm_gateway.py             # Multi-provider LLM router (Ollama/OpenAI/Anthropic)
│   └── schemas.py                 # Pydantic data models for pipeline contracts
│
├── assets/                        # Runtime assets (fonts, music, B-roll, LUTs, SFX)
├── data/                          # Processing data (raw downloads, processed output, temp)
├── db/migrations/                 # PostgreSQL schema migrations (7 versions)
├── db/seed/                       # Database seed data (blocklists, brand defaults, hooks)
├── docker-compose.yml             # 7-service production stack
├── infra/                         # Infrastructure config (MinIO data, Docker Compose)
├── grafana/                       # Monitoring dashboard provisioning
├── scripts/                       # Utility scripts (download, MinIO init, test)
└── tests/                         # Test suite
```

---

## Performance & Output Specifications

### Output Format
| Specification | Value |
|---------------|-------|
| Resolution | 1080 x 1920 (9:16 vertical) |
| Frame Rate | 30 fps |
| Video Codec | H.264 (NVENC or libx264) |
| Audio Codec | AAC @ 192 kbps |
| Bitrate | 25 Mbps VBR |
| Duration | 30-59.5 seconds (YouTube Shorts compliant) |
| Container | MP4 with `faststart` flag |
| Loudness | -14 LUFS (TikTok/Reels/Shorts standard) |

### Encoding Fallback Chain
1. **h264_nvenc** (full filter graph) — fastest, requires NVIDIA GPU
2. **libx264 medium CRF 20** (full filter graph) — CPU fallback
3. **libx264 fast CRF 23** (stripped filters) — safe mode for complex filter failures

### Hardware Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | GTX 1060 6GB | RTX 3060 12GB |
| VRAM | 6 GB | 12 GB |
| RAM | 8 GB | 16 GB |
| Storage | 10 GB free | 50 GB free |
| CPU | 4 cores | 8 cores |

---

## Roadmap

- [ ] **Multi-language support** — extend Whisper pipeline to auto-translate and generate multilingual captions
- [ ] **A/B testing framework** — generate multiple thumbnail/caption variants and track engagement metrics
- [ ] **Audience analytics feedback** — feed platform analytics back into the virality scoring model
- [ ] **Voice cloning** — RVC (Retrieval-based Voice Conversion) integration for consistent narrator voice
- [ ] **Real-time streaming** — live stream repurposing with sub-minute latency
- [ ] **Web dashboard** — React-based control panel for queue management, preview, and analytics
- [ ] **Batch processing** — parallel pipeline execution for high-throughput content farms
- [ ] **Custom LUT generation** — AI-driven color grading based on content mood
- [ ] **Engagement prediction** — ML model trained on platform metrics to predict virality pre-render

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes with clear, descriptive messages
4. Open a pull request against `main`

---

## License

This project is proprietary and intended for portfolio demonstration purposes.

---

<p align="center">
  <sub>Built with obsessive attention to engineering quality across NLP, computer vision, audio engineering, and video processing.</sub>
</p>
