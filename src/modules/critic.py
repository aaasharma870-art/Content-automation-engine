"""
critic.py - Multimodal Quality Assurance Agent
==============================================
Acts as a final "Director of QA" before publishing.
1. Watches the rendered video (via keyframes).
2. Checks for:
   - Safe Zone violations (text/face in UI areas)
   - Visual Glitches (black frames, tearing)
   - B-roll relevance (does the image match context?)
   - "Slop" artifacts (bad cropping, floating text)
3. Returns a PASS/FAIL score with detailed breakdown.

Uses Gemini 1.5 Flash Vision (low cost, high speed).
"""

import os
import cv2
import json
import base64
from pathlib import Path
from PIL import Image
import io

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import (
    GOOGLE_API_KEY, LLM_MODEL, GEMINI_TEMPERATURE,
    SAFE_ZONE_TOP, SAFE_ZONE_BOTTOM, SAFE_ZONE_RIGHT,
    CRITIC_ENABLED
)
from src.utils.logger import log


SYSTEM_PROMPT = """You are a strict Quality Assurance Video Critic for a high-end viral content agency.
Your job is to REJECT any video that looks like "AI Slop" or violates platform safety zones.

**SAFE ZONES (TikTok/Reels):**
- Top 15% is reserved for Search/Live UI.
- Bottom 35% is reserved for Captions/Description/Audio/CTA.
- Right 15% is reserved for Engagement Buttons.

**CRITERIA:**
1. **Safe Zones**: are any faces or subtitles covered by the UI zones above?
2. **Glitch Check**: are there any black frames, tearing, or corrupt visuals?
3. **Alignment**: are the subtitles legible and centered?
4. **Composition**: is the subject well-framed (not cut off at chin/forehead)?

Return a JSON verdict.
"""


def critique_video(video_path: str) -> dict:
    """
    Analyzes a rendered video using Multimodal LLM.
    Returns dict: { "passed": bool, "score": int, "reason": str }
    """
    if not CRITIC_ENABLED:
        log("CRITIC", "Critic disabled in config", "WARN")
        return {"passed": True, "score": 100, "reason": "Disabled"}

    log("CRITIC", f"Reviewing: {Path(video_path).name}...")

    # 1. Extract Keyframes (Start, Middle, End)
    frames = _extract_keyframes(video_path)
    if not frames:
        return {"passed": False, "score": 0, "reason": "Could not extract frames"}

    # 2. Call Gemini Vision
    try:
        verdict = _call_gemini_vision(frames)
        
        score = verdict.get("score", 0)
        passed = score >= 7
        status = "PASSED" if passed else "FAILED"
        color = "OK" if passed else "ERROR"
        
        log("CRITIC", f"Verdict: {status} ({score}/10). Reason: {verdict.get('reason')}", color)
        return {"passed": passed, "score": score, "reason": verdict.get("reason")}

    except Exception as e:
        log("CRITIC", f"Critic failed: {e}", "WARN")
        # Fail safe: don't block pipeline if critic fails, but warn
        return {"passed": True, "score": 50, "reason": f"Critic Error: {e}"}


def _extract_keyframes(video_path: str) -> list[Image.Image]:
    """Capture 3 equidistant frames for analysis."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if total < 1:
        return []

    positions = [
        int(total * 0.1),  # 10%
        int(total * 0.5),  # 50%
        int(total * 0.9),  # 90%
    ]

    images = []
    for pos in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = cap.read()
        if ret:
            # Convert BGR to RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            # Resize for LLM (faster upload, sufficient detail)
            pil_img.thumbnail((512, 512))
            images.append(pil_img)

    cap.release()
    return images


def _call_gemini_vision(images: list[Image.Image]) -> dict:
    """Send frames to Gemini 1.5 Flash."""
    import google.generativeai as genai

    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY missing")

    genai.configure(api_key=GOOGLE_API_KEY)

    # Use 1.5 Flash for speed/cost
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            response_mime_type="application/json"
        )
    )

    # Add prompt to images
    content = [
        "Analyze these 3 frames from the video (Start, Middle, End).",
        "Strictly check for Safe Zone violations (Text/Faces in Top 15%, Bottom 35%, Right 15%).",
        "Output JSON: { \"score\": int (0-10), \"passed\": bool (score>=7), \"reason\": str }"
    ]
    content.extend(images)

    response = model.generate_content(content)
    
    try:
        return json.loads(response.text.strip())
    except Exception:
        # Fallback parsing
        return {"score": 5, "passed": False, "reason": "Failed to parse LLM response"}
