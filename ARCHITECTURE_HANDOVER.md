# AutoShorts_Omni: The "Magnum Opus" Whitepaper

**Technical Blueprint for Sovereign AI Content Generation**
**Target Audience:** Senior AI Engineers & Systems Architects
**Version:** 2.0 (Unified Platform)

---

## 1. Executive Summary
**AutoShorts** is now a **Unified Content Factory** capable of both:
1.  **Repurposing**: Editing long-form YouTube videos into viral shorts.
2.  **Generating**: Creating entire narratives from scratch using AI (Omni Mode).

The system is designed to run 24/7 without human intervention.

---

## 2. System Architecture (Unified)

### The Orchestrator (`src/main.py`)
The entry point asks the user to select a mode:
-   **Mode 1: Repurpose** (`src/pipelines/repurpose.py`)
    -   *Input*: YouTube URL.
    -   *Process*: valid -> download -> transcript -> viral clip select -> face tracking -> render.
-   **Mode 2: Generate** (`src/pipelines/generate.py`)
    -   *Input*: Topic (e.g., "Dark Reality of AI").
    -   *Process*: topic -> script (LLM) -> parallel image gen (DALL-E) + voice (TTS) -> hybrid composite -> render.

### The Stack
-   **Language**: Python 3.10+
-   **Core**: FFmpeg (NVENC), OpenCV, PyTorch.
-   **AI**: Gemini 1.5 Flash (Logic), DALL-E 3 (Vision), Edge-TTS (Voice), Whisper (Transcribe).

---

## 3. Omni Module Deep-Dive (Generation Mode)

### A. The Miner (`src/modules/miner.py`)
**Role:** Acquires raw materials (Scripts & Gameplay).
-   **Gameplay**: Scrapes 1080p clips, validaties resolution, and uses `scenedetect` to slice them seamlessly.
-   **Script**: Uses Gemini 1.5 Flash with strict JSON schema enforcement.

### B. The Visionary (`src/modules/vision.py`)
**Role:** Visualizes the narrative.
-   **Parallel Execution**: Async DALL-E 3 generation (5 images in ~15s).

### C. The Audio Engineer (`src/modules/audio.py`)
**Role:** Creates the auditory experience.
-   **R128 Normalization**: Broadcast standard loudness (-14 LUFS).
-   **Sidechain Ducking**: Background music automatically lowers when voice speaks.

### D. The Renderer (`src/modules/render_gen.py`)
**Role:** Assembles the final asset for Generation Mode.
-   **Hybrid Compositing**: AI Images (Top) + Gameplay (Bottom).
-   **Karaoke Subtitles**: `.ass` format with word-level highlighting.

---

## 4. Cost Analysis (Generation Mode)

| Component | Cost per Unit | Units per Video | Total Cost | Improvement Path |
| :--- | :--- | :--- | :--- | :--- |
| **Script** (Gemini) | $0.0001 / 1k chars | ~2k chars | **$0.0002** | Negligible. |
| **Images** (DALL-E 3) | $0.040 / image | 5 images | **$0.2000** | **CRITICAL FIX NEEDED** |
| **Voice** (Edge) | Free | 1 | $0.0000 | Good. |
| **Compute** (Local) | Electricity | ~2 mins | $0.0100 | Good. |
| **TOTAL** | | | **~$0.21** | |

---

## 5. Roadmap
1.  **Local Image Gen**: Replace DALL-E 3 with SDXL Turbo to reduce cost to $0.
2.  **Semantic Match**: Use CLIP to better match gameplay to story sentiment.
