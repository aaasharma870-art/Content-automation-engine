# ☁️ Serverless ACE (Pure n8n)

You chose the **Serverless Route**. This means you don't need to run Docker, Python, or manage a VPS.
Instead, you will run everything inside **n8n** and use 3rd party APIs.

---

## ⚠️ The Trade-Offs: Self-Hosted vs. Cloud n8n

| Feature | 🏠 Self-Hosted (RECOMMENDED) | ☁️ Pure Cloud n8n |
| :--- | :--- | :--- |
| **Logic Engine** | **Python (Custom Brain)** | **n8n Nodes (Standard)** |
| **Video Rendering** | **Free (FFmpeg)** | **Paid API (Creatomate/Shotstack)** |
| **Recurring Cost** | **~$8/mo** (VPS) | **~$30-50/mo** (n8n Cloud + APIs) |
| **Setup Difficulty** | Medium (Docker Command) | Easy (Drag & Drop) |
| **Custom Code** | Unlimited (OpenCV, Pandas) | Limited (JavaScript only) |
| **Local LLM** | **Yes (Free)** | No (Must use OpenAI) |

### Why we recommend Self-Hosted (Option A):
1.  **Cost at Scale**: Generating 100 videos/month on "Pure Cloud" will cost you ~$0.20 per video in rendering fees ($20/mo) + OpenAI fees. Self-hosting renders for **free**.
2.  **Visual Quality**: Our Python `Renderer` uses advanced FFmpeg filters (grading, beat-sync) that are hard to replicate in standard SaaS tools without complex JSON.
3.  **Local Intelligence**: You lose the "Hybrid LLM" savings. Pure Cloud forces you to pay OpenAI for *everything*.

### When to choose Pure Cloud (Option B):
*   You absolutely cannot touch a terminal/server.
*   You are okay paying ~$0.30-$0.50 per video for convenience.
*   You want to edit the logic visually without reading Python code.

---

## 1. Setup Guide

### A. Get n8n
1.  Sign up for [n8n Cloud](https://n8n.io) (or use your existing instance).

### B. Get API Keys
You need 3 keys:
1.  **OpenAI** (Script Writing): [Get Key](https://platform.openai.com)
2.  **Pexels** (Stock Video): [Get Key](https://www.pexels.com/api/)
3.  **Creatomate** (Video Rendering): [Sign Up](https://creatomate.com)
    *   Create a template in Creatomate.
    *   Note your `Template ID` and `API Key`.

### C. Import Workflow
1.  Download `n8n_serverless.json` from this repo.
2.  Import it into n8n.
3.  **Configure Nodes**:
    *   **AI Writer**: Connect your OpenAI Credentials.
    *   **Asset Finder**: Paste your Pexels Key in the Header (`Authorization`).
    *   **Render**: Paste your Creatomate Key and Template ID.

---

## 2. How it Works
1.  **Trigger**: Wakes up daily.
2.  **AI Writer**: GPT-4 writes the script and picks visual keywords.
3.  **Asset Finder**: Searches Pexels for a portrait video.
4.  **Render**: Sends the text + video URL to Creatomate to burn the video.
5.  **Publish**: (Add your YouTube/TikTok nodes here).

---
*Back to [README.md](README.md)*
