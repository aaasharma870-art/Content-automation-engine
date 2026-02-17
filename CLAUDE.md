# CLAUDE.md - AutoShorts_Gold (Viral Edition)

## Operational Philosophy
We are building a **"Hyper-Retention" Engine**. Every millisecond of static content is a failure state.
- **Audio:** Must flow continuously (No breath gaps).
- **Visuals:** Must change every 0.75s (using "Fake Cuts").
- **Script:** Must use the "Listicle/Proof" structure, never a "Story" structure.

## Tech Stack Constraints
- **Audio:** `pydub` (for millisecond-level stitching), `edge-tts`.
- **Video:** `ffmpeg-python` (complex filter graphs required).
- **AI Logic:** `google-generativeai` (Gemini 1.5 Flash).
- **Hardware:** Local NVIDIA GPU (Strict Serial Execution for SDXL/SVD).

## Critical Implementation Rules
1. **The 200ms Rule:** All audio transitions must overlap by exactly 200ms.
2. **The 3-Shot Rule:** Every video clip (approx 3.5s - 4s) must be split into 3 distinct visual cuts via FFmpeg filters.
3. **No Hallucinations:** Use the exact logic paths provided in the plan.
4. **SVD Duration:** SVD-XT outputs 25 frames. At 6fps = 4.1s. At 7fps = 3.5s. We will use **6fps** to ensure we have enough footage for the 4s cut pattern.
