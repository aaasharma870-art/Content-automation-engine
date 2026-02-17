<p align="center">
  <h1 align="center">⚡ Content Automation Engine</h1>
  <p align="center">
    <strong>A fully autonomous AI pipeline that transforms long-form video into platform-optimized short-form content — from ingestion to distribution — without human intervention.</strong>
  </p>
  <p align="center">
    <em>Built with Python · FFmpeg · Whisper · Gemini · CLIP · FAISS · Stable Diffusion · MediaPipe · NVENC</em>
  </p>
</p>

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Motivation & Problem Statement](#motivation--problem-statement)
3. [System Architecture](#system-architecture)
4. [Pipeline Walkthrough](#pipeline-walkthrough)
5. [Core Modules (Technical Deep Dive)](#core-modules-technical-deep-dive)
6. [Viral Retention Engineering](#viral-retention-engineering)
7. [Infrastructure & Deployment](#infrastructure--deployment)
8. [Technology Stack](#technology-stack)
9. [Installation & Setup](#installation--setup)
10. [Usage](#usage)
11. [Configuration Reference](#configuration-reference)
12. [Project Structure](#project-structure)
13. [Technical Highlights](#technical-highlights)
14. [Future Roadmap](#future-roadmap)

---

## Project Overview

The **Content Automation Engine** is a production-grade, end-to-end AI system that I designed and built from scratch to solve a real problem in digital media: the labor-intensive process of repurposing long-form video content (podcasts, lectures, interviews) into short-form vertical clips optimized for TikTok, YouTube Shorts, and Instagram Reels.

The system operates as an autonomous "ghost employee" — it monitors a queue file for YouTube URLs, downloads the source material, transcribes it with GPU-accelerated speech recognition, uses large language models to identify the most viral-worthy segments, performs intelligent 16:9 → 9:16 spatial reprojection with face tracking, applies broadcast-grade audio mastering, generates kinetic typography captions, injects semantically-matched B-roll footage, renders the final output with hardware-accelerated encoding, and optionally distributes the finished clips across social media platforms — all without a single manual step.

**What makes this project technically significant:**

- **15,000+ lines of Python** across 20 specialized modules, each handling a distinct domain (NLP, computer vision, audio engineering, video rendering, generative AI)
- **Real-time computer vision** using MediaPipe Face Mesh and Kalman filtering for cinematic camera tracking
- **Multimodal AI integration** spanning speech-to-text (Whisper), language understanding (Gemini/GPT-4), image-text alignment (CLIP), vector search (FAISS), image generation (SDXL Turbo), and video synthesis (Stable Video Diffusion)
- **Broadcast-standard audio processing** including LUFS loudness normalization, sidechain compression (auto-ducking), silence removal, and multi-layer mixing
- **Production infrastructure** with Docker Compose orchestrating 7 services (PostgreSQL, MinIO, N8N, Grafana, application microservices)

---

## Motivation & Problem Statement

The short-form video market has exploded: TikTok, YouTube Shorts, and Instagram Reels collectively serve billions of daily views. Content creators sitting on hours of long-form footage face a bottleneck — turning a 60-minute podcast into five polished, platform-ready Shorts requires:

1. **Manual clip selection** — watching the entire video, identifying compelling moments  
2. **Aspect ratio conversion** — cropping 16:9 to 9:16 while keeping subjects in frame  
3. **Audio mastering** — normalizing loudness, removing dead air, mixing background music  
4. **Caption generation** — transcribing, timing, and styling word-by-word subtitles  
5. **Visual enhancement** — adding B-roll, transitions, and thumbnail extraction  
6. **Platform distribution** — uploading with optimized metadata to multiple platforms  

Each of these steps traditionally requires a skilled editor and hours of manual work per clip. This engine automates the entire workflow, reducing the turnaround from hours to minutes while maintaining (and often exceeding) human-level quality.

---

## System Architecture

The engine follows a **modular pipeline architecture** where each stage operates independently, communicating through well-defined data contracts (JSON manifests and file paths). This design enables parallel development, isolated testing, and easy extension.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CONTENT AUTOMATION ENGINE                        │
├─────────────┬──────────────┬──────────────┬─────────────┬──────────────┤
│   INGEST    │  TRANSCRIBE  │    BRAIN     │  DIRECTOR   │    EDITOR    │
│  yt-dlp     │  Whisper     │  Gemini/GPT  │  MediaPipe  │  FFmpeg      │
│  1080p DL   │  large-v2    │  Virality    │  Face Mesh  │  NVENC       │
│  Cookie     │  CUDA fp16   │  Scoring     │  Kalman     │  Sidechain   │
│  Auth       │  Word-level  │  Chain-of-   │  Filter     │  LUFS Norm   │
│             │  Timestamps  │  Thought     │  Smooth Pan │  Captions    │
├─────────────┴──────────────┴──────────────┴─────────────┴──────────────┤
│                          SUPPORT MODULES                                │
├──────────┬──────────┬──────────┬───────────┬──────────┬────────────────┤
│  B-ROLL  │  MINER   │ FOUNDRY  │ THUMBNAIL │  CRITIC  │  DISTRIBUTOR  │
│  CLIP+   │  Scene   │ SDXL     │ Aesthetic │ Gemini   │  Ayrshare     │
│  FAISS   │  Detect  │ Turbo +  │ Scoring   │ Vision   │  TikTok/YT/   │
│  Pexels  │  PyScene │ SVD      │ Face/     │ QA Pass  │  Instagram    │
│  Fallback│  Detect  │ Pipeline │ Thirds    │ Safe     │  Scheduling   │
│          │          │          │           │ Zone     │               │
├──────────┴──────────┴──────────┴───────────┴──────────┴────────────────┤
│                     VIRAL RETENTION LAYER                               │
├──────────────┬─────────────────┬────────────────────────────────────────┤
│  PROOF LIST  │   FLASH CUTS    │          MICRO-SFX (J-CUTS)           │
│  Hook→3      │  Animated Crop  │   200ms Crossfade · -45dB Silence     │
│  Proofs→     │  3 Zoom/Pan     │   Trim · Whoosh at 1.4s/2.8s per     │
│  Rehook      │  Patterns/Clip  │   4-Second Block (Synced to Visual)   │
└──────────────┴─────────────────┴────────────────────────────────────────┘
```

---

## Pipeline Walkthrough

When a YouTube URL enters the queue, the engine executes the following stages sequentially:

### Stage 1: Ingestion (`ingest.py` — 256 lines)

The ingestion module downloads the source video at maximum 1080p resolution using `yt-dlp`, with support for cookie-based authentication to access age-restricted or member-only content. It simultaneously extracts a separate 16kHz mono WAV file optimized for Whisper processing, and organizes all downloaded assets into a structured directory (`data/raw/<video_id>/`).

**Key implementation details:**
- Resolution capping at 1080p to balance quality vs. processing time
- Separate audio extraction (`-vn -ar 16000 -ac 1`) for optimal Whisper input
- Idempotent downloads — skips re-downloading if the video already exists locally
- Metadata preservation (title, duration, channel) in a companion JSON manifest

### Stage 2: Transcription (`transcribe.py` — 188 lines)

Speech-to-text conversion runs on `faster-whisper` (CTranslate2 backend) with the `large-v2` model on CUDA using float16 precision. This produces word-level timestamps with sub-100ms accuracy — critical for the kinetic typography system downstream.

**Key implementation details:**
- Word-level alignment via Whisper's built-in timestamp extraction
- Language auto-detection with confidence scoring
- `get_words_in_range(words, start, end)` utility for extracting transcript segments by timestamp
- Full transcript and word list persisted to JSON for caching and re-use

### Stage 3: Intelligence (`brain.py` — 300 lines)

The "brain" is the LLM-powered virality engine. It sends the complete transcript to Gemini 1.5 Flash (or an OpenAI-compatible endpoint) with a meticulously engineered system prompt that forces chain-of-thought reasoning:

1. Read the full narrative arc  
2. Identify emotional peaks, surprising reveals, and debate-worthy claims  
3. Score each candidate segment on four axes: **Hook** (0–99), **Flow** (0–99), **Value** (0–99), **Trend** (0–99)  
4. Return strict JSON with timestamps, titles, descriptions, and hashtags  

The prompt enforces clip duration constraints (30–60 seconds), prohibits arbitrary slicing, and requires each clip to begin with a strong hook statement.

### Stage 4: Spatial Reprojection (`director.py` — 495 lines)

This is the computer vision core. Converting landscape (16:9) video to portrait (9:16) intelligently — without blindly center-cropping — requires real-time subject tracking:

1. **MediaPipe Face Mesh** detects facial landmarks at configurable frame intervals
2. **Active Speaker Detection** identifies which face is speaking by measuring lip movement variance across consecutive frames
3. **Kalman Filter** smooths the crop window trajectory, eliminating jitter while maintaining responsiveness (configurable process noise: 0.1)
4. **Fallback Strategy** — when no faces are detected (screen shares, B-roll), the system falls back to letterboxing with a blurred background fill

The result is cinematic-quality reprojection that tracks the active speaker smoothly, mimicking the behavior of a professional camera operator.

### Stage 5: Post-Production (`editor.py` — 951 lines)

The editor is the largest module and handles four critical subsystems:

**Audio Engineering:**
- **LUFS Normalization** — targets -14 LUFS for social media loudness standards (configurable per platform)
- **Sidechain Compression** — automatically ducks background music when speech is detected (1ms attack, 500ms release, 3:1 ratio, -14dB base music volume)
- **Silence Removal** — trims dead air below -40dB threshold with minimum 500ms duration gates

**Kinetic Typography:**
- Generates `.ass` subtitle files (Advanced SubStation Alpha) with word-level timing
- **Hormozi-style** visual treatment: bold Montserrat font (70pt), white text with 5px black outline, 3px shadow
- Active word highlighting in yellow (`&H0000FFFF`) for visual emphasis
- Semantic emphasis colors: green for key nouns, yellow for adjectives, red for negative terms
- Automatic emoji injection via a curated 100+ entry mapping (`emoji_map.py`)
- Safe zone compliance — captions positioned above the TikTok/Reels UI overlay (200px bottom margin)

**B-Roll Integration:**
- Splices contextually-matched B-roll footage at LLM-specified insertion points
- 3-second overlay duration with cross-dissolve transitions

**Final Render:**
- FFmpeg assembly with NVIDIA NVENC hardware encoding (`h264_nvenc`)
- 25 Mbps VBR output at 1080×1920 @ 30fps
- GPU-accelerated decoding via CUDA (`-hwaccel cuda`)

### Stage 6: Quality Assurance (`critic.py` — 153 lines)

An optional multimodal QA gate that uses **Gemini 1.5 Flash Vision** to review the rendered output before publishing. It extracts three keyframes (10%, 50%, 90% of duration) and evaluates:

- **Safe Zone Violations** — faces or text obscured by platform UI elements
- **Visual Glitches** — black frames, tearing, corruption
- **Caption Legibility** — text readability and centering
- **Composition Quality** — subject framing (not cut off at chin/forehead)

Returns a PASS/FAIL verdict with a 0–10 quality score. Threshold: ≥7 to pass.

### Stage 7: Distribution (`distributor.py` — 187 lines)

Automated scheduling and posting to TikTok, YouTube Shorts, and Instagram Reels via the Ayrshare unified API. Features include:

- Drip-feed scheduling (configurable interval between posts)
- Platform-optimized caption formatting (title, description, hashtags)
- Fallback mode: generates `.meta.json` files alongside each video when no API key is configured, enabling manual upload with pre-written metadata

---

## Core Modules (Technical Deep Dive)

### Semantic B-Roll Engine (`broll.py` — 337 lines)

Uses **OpenAI CLIP** (ViT-B/32) and **FAISS** for semantic visual search:

1. **Indexing Phase** — extracts 5 frames per clip from the local B-roll library, encodes each through CLIP's vision encoder, and builds a FAISS vector index
2. **Query Phase** — the LLM generates natural-language descriptions of desired B-roll ("person walking through city streets"), which are encoded through CLIP's text encoder
3. **Retrieval** — cosine similarity search against the FAISS index returns the best-matching clip above a 0.25 minimum similarity threshold
4. **Pexels Fallback** — when no local match exists, the engine queries Pexels' stock footage API (`pexels_broll.py`) with optional CLIP verification of retrieved thumbnails

### Content Mining (`miner.py` — 277 lines)

Handles two distinct responsibilities:

1. **Gameplay Library Curation** — downloads, validates, and scene-splits gameplay footage for background content using `PySceneDetect` with `ContentDetector`
2. **Transcript Pattern Analysis** — `analyze_transcript_patterns()` scans transcripts for enumeration markers ("first," "second," "number one," "step 1") that indicate listicle-style content ideal for the Proof List viral format

### Local Generative AI (`foundry.py` — 78 lines)

On-device image and video generation pipeline:

1. **SDXL Turbo** — generates high-quality images from text prompts in ~1 second on consumer GPUs (4-step inference)
2. **Stable Video Diffusion (SVD)** — converts generated images into 4-second video loops at 6fps with motion_bucket_id=180 for high-motion output
3. **VRAM Management** — automatic model unloading and garbage collection to fit within 12GB GPU memory constraints

### AI Thumbnail Selection (`thumbnail.py` — 151 lines)

Algorithmically selects the most visually compelling frame as a thumbnail using a multi-factor scoring model:

| Factor | Weight | Metric |
|--------|--------|--------|
| Sharpness | 25% | Laplacian variance (higher = sharper) |
| Brightness | 20% | Mean luminance with extremes penalty (peak at ~115/255) |
| Contrast | 20% | Standard deviation of luminance |
| Color Vibrancy | 15% | Mean saturation in HSV color space |
| Face Presence | Bonus +30% | Haar cascade detection with rule-of-thirds positioning bonus |
| Anti-Black-Frame | Gate | Heavily penalizes frames below 5% brightness |

---

## Viral Retention Engineering

A dedicated layer of audio and visual techniques engineered to maximize viewer retention on short-form platforms:

### Proof List Scripts (`miner.py`)

The LLM generates scripts in a rigid **Hook → 3 Proofs → Rehook** structure:

- **Hook** (5-8 seconds) — an attention-grabbing opening statement or question
- **Proof 1, 2, 3** — three supporting evidence points, each 8-12 seconds
- **Rehook** — a callback to the opening that creates narrative closure
- Enforced **140-word limit** to maintain pacing (~55 seconds at natural speech rate)
- Enumeration detection identifies existing listicle patterns in source transcripts

### Flash Cuts (`render_gen.py`)

Three randomized zoom/pan animation patterns applied to each clip, creating visual dynamism that prevents viewer disengagement:

| Pattern | Description | Motion |
|---------|-------------|--------|
| **A: Pan** | Scale 1.5× → animated horizontal crop drift | Smooth rightward pan |
| **B: Drift** | Start top-left crop → drift to center | Diagonal drift |
| **C: Chaos** | Sinusoidal oscillation on both axes | Bouncing motion |

The source video is upscaled to 1620×2880 (1.5× target resolution), then a 1080×1920 crop window animates across the larger canvas using FFmpeg's `crop` filter with time-variable expressions (`t*50`, `sin(t*3)`).

### Micro-SFX / J-Cuts (`audio.py`)

Audio enhancement techniques borrowed from professional video editing:

- **J-Cut Crossfading** — 200ms overlapping audio transitions between segments, creating seamless flow
- **Silence Removal** — -45dB threshold gate removes dead air
- **Whoosh Injection** — soft transition SFX overlaid at **1.4s** and **2.8s** intervals within each 4-second block, synchronized with the visual Flash Cut timing
- SFX volume reduced by -20dB to remain subliminal (felt, not consciously heard)

---

## Infrastructure & Deployment

### Docker Compose Stack (7 Services)

The production deployment runs as a containerized microservice architecture:

| Service | Image | Purpose | Resources |
|---------|-------|---------|-----------|
| **PostgreSQL 16** | `postgres:16-alpine` | Content database, job queue, analytics | 1 CPU, 1GB RAM |
| **MinIO** | `minio/minio` | S3-compatible object storage for assets | 0.5 CPU, 512MB |
| **N8N** | `n8nio/n8n` | Visual workflow orchestration | 0.5 CPU, 512MB |
| **Orchestrator** | Custom | Job scheduling, API gateway | 1 CPU, 512MB |
| **AI Services** | Custom | LLM, CLIP, transcription endpoints | 1 CPU, 1GB |
| **Renderer** | Custom | FFmpeg/NVENC video processing | 2 CPU, 2GB |
| **Grafana** | `grafana/grafana` | Monitoring dashboards, metrics | 0.5 CPU, 256MB |

All services communicate over a private Docker network (`aibrain-network`) with health checks and automatic restart policies.

---

## Technology Stack

### Languages & Frameworks
| Category | Technologies |
|----------|-------------|
| **Core Language** | Python 3.10+ |
| **Video Processing** | FFmpeg (NVENC GPU encoding, CUDA decoding) |
| **Speech Recognition** | faster-whisper (CTranslate2, large-v2 model, CUDA fp16) |
| **Large Language Models** | Google Gemini 1.5 Flash, OpenAI GPT-4o (configurable) |
| **Computer Vision** | OpenCV, MediaPipe Face Mesh, Haar Cascades |
| **Semantic Search** | OpenAI CLIP (ViT-B/32), FAISS (Facebook AI Similarity Search) |
| **Generative AI** | Stable Diffusion XL Turbo, Stable Video Diffusion |
| **Audio Engineering** | pydub, librosa, FFmpeg (LUFS, sidechain, loudnorm) |
| **Infrastructure** | Docker Compose, PostgreSQL, MinIO (S3), N8N, Grafana |
| **Distribution** | Ayrshare API (TikTok, YouTube, Instagram) |
| **Scene Detection** | PySceneDetect (ContentDetector) |

### Hardware Acceleration
- **NVIDIA NVENC** for real-time H.264 encoding (10× faster than CPU libx264)
- **CUDA** for GPU-accelerated video decoding and Whisper inference
- **PyTorch CUDA** for CLIP embeddings, SDXL Turbo, and SVD inference

---

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- NVIDIA GPU with CUDA support (RTX 3060+ recommended, 12GB VRAM)
- FFmpeg with NVENC support (bundled via `imageio-ffmpeg` or system install)
- Git

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/aaasharma870-art/Content-automation-engine.git
cd Content-automation-engine

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install PyTorch with CUDA support (must be first)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 4. Install CLIP
pip install git+https://github.com/openai/CLIP.git@main

# 5. Install remaining dependencies
pip install -r requirements.txt

# 6. Configure environment variables
cp .env.example .env
# Edit .env with your API keys:
#   GOOGLE_API_KEY=your_gemini_key
#   PEXELS_API_KEY=your_pexels_key (optional, for B-roll fallback)
#   AYRSHARE_API_KEY=your_ayrshare_key (optional, for auto-distribution)

# 7. Run the engine
python main.py
```

### Docker Deployment

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Launch the full stack (PostgreSQL + MinIO + N8N + Grafana + App Services)
docker-compose up -d

# Monitor logs
docker-compose logs -f orchestrator
```

---

## Usage

### Autonomous Mode (Default)

The engine runs as a persistent daemon, polling `queue.txt` every 30 seconds:

```bash
# Add URLs to the processing queue
echo "https://www.youtube.com/watch?v=VIDEO_ID" >> queue.txt

# Start the engine (runs indefinitely)
python main.py
```

### Direct Pipeline Execution

```bash
# Run the generation pipeline directly
python run.py

# Run the viral repurpose pipeline (Flash Cuts + Micro-SFX)
python run_viral_repurpose.py
```

### Repurpose Pipeline

```bash
# Trigger repurpose mode on a specific URL
python trigger_repurpose.py
```

---

## Configuration Reference

All configuration is centralized in `config.py` (187 lines). Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WHISPER_MODEL` | `large-v2` | Whisper model size (accuracy vs. speed tradeoff) |
| `WHISPER_DEVICE` | `cuda` | Inference device (`cuda` or `cpu`) |
| `TARGET_WIDTH × HEIGHT` | `1080 × 1920` | Output resolution (9:16 vertical) |
| `TARGET_FPS` | `30` | Output frame rate |
| `EXPORT_BITRATE` | `25M` | VBR target bitrate (20-30M preserves quality) |
| `TARGET_LUFS` | `-24.0` | Voiceover loudness target |
| `SOCIAL_LUFS` | `-14` | Final mix loudness (TikTok/Reels standard) |
| `SIDECHAIN_RATIO` | `3:1` | Music ducking compression ratio |
| `CAPTION_FONT` | `Montserrat-Bold` | Subtitle font (Hormozi aesthetic) |
| `CAPTION_FONT_SIZE` | `70` | Font size (optimized for mobile) |
| `CLIP_MODEL_NAME` | `ViT-B/32` | CLIP model for semantic B-roll search |
| `BROLL_MIN_SIMILARITY` | `0.25` | Minimum cosine similarity for B-roll match |
| `FACE_SAMPLE_RATE` | `4` | Frame interval for face detection (lower = smoother) |
| `KALMAN_PROCESS_NOISE` | `0.1` | Kalman filter responsiveness (higher = faster) |
| `USE_NVENC` | `True` | Enable NVIDIA hardware encoding |
| `SAFE_ZONE_BOTTOM` | `35%` | Reserved for TikTok/Reels UI elements |
| `DYNAMIC_ZOOM_INTENSITY` | `1.05` | Maximum zoom factor (1.0 = off) |
| `MAX_CLIPS_PER_VIDEO` | `5` | Maximum shorts generated per source video |
| `CRITIC_ENABLED` | `False` | Enable Gemini Vision QA gate |

---

## Project Structure

```
Content-automation-engine/
├── main.py                    # Orchestrator daemon (queue monitor + pipeline runner)
├── run.py                     # Direct pipeline execution script
├── run_viral_repurpose.py     # Viral clip generator (Flash Cuts + Micro-SFX)
├── config.py                  # Centralized configuration (187 lines, 50+ parameters)
├── requirements.txt           # Python dependencies (53 packages)
│
├── src/
│   ├── modules/
│   │   ├── ingest.py          # YouTube downloader (yt-dlp, 1080p, cookie auth)
│   │   ├── transcribe.py      # Speech-to-text (faster-whisper, CUDA, word-level)
│   │   ├── brain.py           # LLM virality scoring (Gemini/GPT, chain-of-thought)
│   │   ├── director.py        # Spatial reprojection (MediaPipe, Kalman filter)
│   │   ├── editor.py          # Post-production (LUFS, sidechain, captions, render)
│   │   ├── audio.py           # Audio engineering (J-cuts, micro-SFX, crossfade)
│   │   ├── broll.py           # Semantic B-roll search (CLIP + FAISS)
│   │   ├── pexels_broll.py    # Pexels stock footage fallback
│   │   ├── miner.py           # Content mining (scene detect, pattern analysis)
│   │   ├── render_gen.py      # Video rendering (Flash Cuts, filter chains)
│   │   ├── foundry.py         # Local generative AI (SDXL Turbo + SVD)
│   │   ├── critic.py          # Multimodal QA agent (Gemini Vision)
│   │   ├── distributor.py     # Social media scheduling (Ayrshare API)
│   │   ├── thumbnail.py       # AI thumbnail selection (aesthetic scoring)
│   │   ├── vision.py          # Computer vision utilities
│   │   ├── validator.py       # Output validation
│   │   └── utils.py           # Shared utilities (logging, FFmpeg path resolution)
│   │
│   ├── pipelines/
│   │   ├── generate.py        # Original content generation pipeline
│   │   └── repurpose.py       # Long-form → short-form repurposing pipeline
│   │
│   └── utils/
│       ├── logger.py          # Colored terminal logging with timestamps
│       ├── ffmpeg_utils.py    # FFmpeg/FFprobe binary resolution
│       ├── asset_manager.py   # Asset download and caching
│       └── emoji_map.py       # 100+ keyword → emoji mapping for captions
│
├── assets/                    # Runtime assets (fonts, music, B-roll, LUTs, SFX)
├── data/                      # Processing data (raw downloads, processed output)
├── docker-compose.yml         # 7-service production stack
├── Makefile                   # Build automation targets
├── grafana/                   # Monitoring dashboard provisioning
├── db/                        # PostgreSQL migrations and seed data
├── n8n/                       # N8N workflow definitions
├── tests/                     # Test suite
└── scripts/                   # Utility scripts
```

---

## Technical Highlights

This project demonstrates competency across multiple computer science domains:

### Signal Processing & Audio Engineering
- Implementation of LUFS loudness normalization (ITU-R BS.1770 standard)
- Real-time sidechain compression with configurable attack/release envelopes
- Psychoacoustic silence gating with minimum duration constraints

### Computer Vision & Spatial Reasoning
- Real-time face detection and landmark extraction using MediaPipe's 468-point Face Mesh
- Active speaker identification through lip movement variance analysis
- Kalman filter implementation for temporally smooth crop trajectory estimation
- Multi-factor frame quality scoring (Laplacian sharpness, rule-of-thirds composition)

### Natural Language Processing & Prompt Engineering
- Chain-of-thought prompting for structured content analysis
- Constrained JSON output generation with fallback parsing
- Multi-axis virality scoring (Hook, Flow, Value, Trend)
- Enumeration pattern detection via regex for listicle identification

### Information Retrieval & Vector Search
- CLIP-based cross-modal embedding (text queries ↔ video frame retrieval)
- FAISS index construction and approximate nearest-neighbor search
- Cosine similarity thresholding with fallback cascade to external APIs

### Systems Engineering
- Microservice architecture with health checking and automatic recovery
- GPU resource management (VRAM budgeting, model unloading, garbage collection)
- Idempotent pipeline design with caching at every stage
- Containerized deployment with Docker Compose and persistent volumes

### Generative AI
- Stable Diffusion XL Turbo for single-step high-quality image synthesis
- Stable Video Diffusion for image-to-video animation
- Configurable motion intensity and frame rate for stylistic control

---

## Future Roadmap

- [ ] **Multi-language support** — extend Whisper pipeline to auto-translate and generate multilingual captions
- [ ] **A/B testing framework** — generate multiple thumbnail/caption variants and track engagement metrics
- [ ] **Audience analytics integration** — feed platform analytics back into the virality scoring model
- [ ] **Voice cloning** — RVC (Retrieval-based Voice Conversion) integration for consistent narrator voice
- [ ] **Real-time streaming** — live stream repurposing with sub-minute latency
- [ ] **Web dashboard** — React-based control panel for queue management and analytics

---

## License

This project is proprietary and intended for portfolio demonstration purposes.

---

<p align="center">
  <sub>Built with obsessive attention to engineering quality. Every module is production-grade, every parameter is tuned, every edge case is handled.</sub>
</p>
