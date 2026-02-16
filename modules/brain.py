"""
brain.py - The Selector (Gemini 1.5 Flash Intelligence)
========================================================
Sends the transcript text to Gemini and asks it to identify 
the most viral, self-contained segments. Returns structured JSON
with timestamps, virality scores, and layout type detection.
"""

import json
import re
import google.generativeai as genai
from colorama import Fore, Style

from config import (
    GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE,
    GEMINI_MAX_OUTPUT_TOKENS, MAX_CLIPS_PER_VIDEO,
    CLIP_MIN_DURATION, CLIP_MAX_DURATION,
)


# ── Configure Gemini on import ─────────────────
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


# ── The System Prompt (The "Secret Sauce") ─────
SYSTEM_PROMPT = """You are an expert viral content editor for TikTok and YouTube Shorts 
specializing in Financial, Trading, and Tech content.

Analyze the following transcript from a long-form YouTube video.
Find the {max_clips} most engaging, self-contained segments that would work 
as standalone viral Shorts (duration: {min_dur}-{max_dur} seconds each).

**VIRALITY RULES (Strict):**
1. **HOOK**: Each segment MUST start with a strong opening hook in the first 3 seconds.
   - Good hooks: "The biggest mistake...", "Here's what nobody tells you...", "This one indicator..."
   - BAD hooks: "Um, so today...", "As I was saying..."
2. **VALUE**: The middle must deliver a clear insight, story, or takeaway.
3. **RESOLUTION**: Each segment must end on a COMPLETE thought. Never mid-sentence.
4. **PACING**: Prefer segments with high energy, fast talking, or emotional delivery.

**CONTENT TYPE TAGGING (Critical for visual layout):**
For each segment, predict the PRIMARY visual type based on text context clues:
- `"talking_head"`: Speaker is sharing opinions, telling a story, giving advice (DEFAULT)
- `"screen_share"`: Text mentions "look at this chart", "as you can see on screen", 
  "let me show you", describes visual data, stock patterns, or code

**OUTPUT:**
Return ONLY valid JSON. No markdown, no explanation, no code fences.
Format:
[
  {{
    "start": 120.5,
    "end": 165.0,
    "score": 9.2,
    "layout_type": "talking_head",
    "hook_text": "The one thing every trader gets wrong...",
    "reason": "Strong emotional hook, clear value, complete thought"
  }}
]
"""


def analyze_transcript(full_text: str, metadata: dict = None) -> list:
    """
    Send transcript to Gemini 1.5 Flash and get viral segment suggestions.
    
    Args:
        full_text: Complete transcript text string
        metadata: Optional dict with video title/description for context
        
    Returns:
        List of clip dicts with: start, end, score, layout_type, hook_text, reason
        
    Raises:
        RuntimeError: If Gemini API call fails
    """
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not set. Get one at https://aistudio.google.com")
    
    print(f"{Fore.BLUE}[BRAIN]{Style.RESET_ALL} Analyzing transcript ({len(full_text)} chars)...")
    
    # ── Build the prompt ────────────────────────
    system = SYSTEM_PROMPT.format(
        max_clips=MAX_CLIPS_PER_VIDEO,
        min_dur=CLIP_MIN_DURATION,
        max_dur=CLIP_MAX_DURATION,
    )
    
    # Add video context if available
    context = ""
    if metadata:
        title = metadata.get("title", "")
        description = metadata.get("description", "")[:500]
        if title:
            context = f"\n\n**VIDEO CONTEXT:**\nTitle: {title}\nDescription: {description}\n"
    
    user_prompt = f"{context}\n**TRANSCRIPT:**\n{full_text}"
    
    # ── Call Gemini 1.5 Flash ───────────────────
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system,
        generation_config=genai.GenerationConfig(
            temperature=GEMINI_TEMPERATURE,
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        ),
    )
    
    try:
        response = model.generate_content(user_prompt)
        raw_text = response.text.strip()
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}")
    
    # ── Parse the JSON response ─────────────────
    clips = _parse_gemini_response(raw_text)
    
    # Sort by virality score (highest first)
    clips.sort(key=lambda c: c.get("score", 0), reverse=True)
    
    # Cap at max clips
    clips = clips[:MAX_CLIPS_PER_VIDEO]
    
    print(f"{Fore.GREEN}[BRAIN]{Style.RESET_ALL} ✓ Found {len(clips)} viral segments:")
    for i, clip in enumerate(clips):
        duration = clip["end"] - clip["start"]
        print(f"  {i+1}. [{clip['start']:.1f}s - {clip['end']:.1f}s] "
              f"Score: {clip['score']}/10 | "
              f"Layout: {clip.get('layout_type', 'talking_head')} | "
              f"Hook: \"{clip.get('hook_text', 'N/A')[:50]}\"")
    
    return clips


def _parse_gemini_response(raw_text: str) -> list:
    """
    Parse the Gemini response into a list of clip dicts.
    Handles cases where Gemini wraps JSON in markdown code fences.
    """
    # Strip markdown code fences if present
    cleaned = raw_text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    
    try:
        clips = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}[BRAIN]{Style.RESET_ALL} JSON parse error: {e}")
        print(f"  Raw response: {raw_text[:200]}...")
        return []
    
    if not isinstance(clips, list):
        clips = [clips]
    
    # ── Validate and normalize each clip ────────
    valid_clips = []
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        
        start = clip.get("start") or clip.get("start_time")
        end = clip.get("end") or clip.get("end_time")
        
        if start is None or end is None:
            continue
        
        try:
            start = float(start)
            end = float(end)
        except (ValueError, TypeError):
            continue
        
        # Enforce minimum/maximum duration
        duration = end - start
        if duration < CLIP_MIN_DURATION * 0.8:  # Allow 20% tolerance
            continue
        if duration > CLIP_MAX_DURATION * 1.2:
            end = start + CLIP_MAX_DURATION
        
        valid_clips.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "score": float(clip.get("score", clip.get("virality_score", 5.0))),
            "layout_type": clip.get("layout_type", "talking_head"),
            "hook_text": str(clip.get("hook_text", "")),
            "reason": str(clip.get("reason", clip.get("hook_reasoning", ""))),
        })
    
    return valid_clips
