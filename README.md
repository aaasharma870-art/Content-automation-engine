# AI Content Automation Engine (AutoShorts V2)

**An autonomous, multimodal AI pipeline that generates viral short-form video content from scratch.**

---

## 📖 Overview

This project is a sophisticated **end-to-end content generation engine** designed to automate the creative process of video production. By orchestrating multiple state-of-the-art AI models, the engine can either:
1.  **Repurpose**: Intelligently slice long-form content (YouTube) into engaging Shorts using facial recognition and transcript analysis.
2.  **Generate**: Create entirely original visual stories from a single text prompt using Generative AI.

It demonstrates proficiency in **Python**, **Computer Vision**, **Natural Language Processing (LLMs)**, and **System Architecture**.

---

## 🏗️ Architecture & Technology Stack

The system is built as a modular pipeline where data flows through specialized "Agents":

### 1. The "Brain" (Decision Engine)
-   **Models**: OpenAI GPT-4o / Google Gemini 1.5
-   **Role**: Analyzes transcripts for viral hooks, sentiments, and "visualizability". It acts as the director, deciding *what* to keep and *how* to style it.
-   **Key Feature**: **Adaptive Style Injection**. The LLM tags scenes with moods (e.g., "dark moody", "luxurious"), which downstream agents use to fetch matching assets.

### 2. The "Director" (Computer Vision)
-   **Library**: MediaPipe / OpenCV
-   **Role**: Performs **Active Speaker Detection** and **Face Tracking**.
-   **Logic**: Uses a Kalman Filter to smooth camera movements, simulating a professional human camera operator zooming and panning to keep the subject in the "Rule of Thirds".

### 3. The "Visionary" (Generative Imagery)
-   **Models**: DALL-E 3
-   **Role**: Generates original, vertically-framed (9:16) illustrations for Story Mode. It dynamically constructs prompts based on the narrative arc.

### 4. The "Editor" (FFmpeg + Audio Engineering)
-   **Role**: The final assembler.
-   **Features**:
    -   **Kinetic Typography**: Generates word-by-word animated subtitles (karaoke style) with automatic emoji injection.
    -   **Audio Ducking**: Uses sidechain compression to automatically lower background music volume when voiceover is detected.
    -   **NVENC Acceleration**: Leverages NVIDIA GPUs for high-speed rendering.

---

## 🚀 Key Features

*   **Autonomous Pipeline**: One command (`python run.py`) launches the entire process from ingestion to final render.
*   **Visual Polish**: Enforces strict "Safe Zones" for social platforms (TikTok/Instagram) ensuring no text is covered by UI elements. Includes 70pt high-readability typography.
*   **Semantic B-Roll Search**: Uses **OpenAI CLIP** embeddings to semantically match stock footage (from Pexels) to the spoken content (e.g., discussing "freedom" fetches a clip of a bird flying, not just a literal match).

---

## 🛠️ Setup & Usage

### Prerequisites
-   Python 3.10+
-   FFmpeg (installed and in PATH)
-   NVIDIA GPU (Recommended for Whisper/Rendering)

### Installation
1.  Clone the repository:
    ```bash
    git clone https://github.com/aaasharma870-art/Content-automation-engine
    cd Content-automation-engine
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure Environment:
    Create a `.env` file with your API keys:
    ```env
    OPENAI_API_KEY=sk-...
    PEXELS_API_KEY=...
    ```

### Execution
Run the unified launcher:
```bash
python run.py
```
Select **Mode 1** to repurpose a YouTube video or **Mode 2** to generate a new story.

---

## 📂 Project Structure

-   `src/`: Core application logic.
    -   `modules/`: specialized agents (Brain, Director, Editor, Vision).
    -   `pipelines/`: orchestration logic for different modes.
-   `assets/`: Local resource library (fonts, music, sfx).
-   `config.py`: Centralized configuration management.
