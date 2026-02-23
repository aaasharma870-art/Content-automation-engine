"""
brain.py - The Selector (LLM Virality Curation)
=================================================
Sends transcript to an LLM (Gemini or OpenAI-compatible) to identify
the most viral segments. Scores each on Hook/Flow/Value/Trend (0-99).
Returns strict JSON with timestamps, titles, and descriptions.
"""

import json
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import (
    GOOGLE_API_KEY, LLM_PROVIDER, LLM_MODEL,
    OPENAI_API_KEY, OPENAI_BASE_URL,
    GEMINI_TEMPERATURE, GEMINI_MAX_OUTPUT_TOKENS,
    MAX_CLIPS_PER_VIDEO, CLIP_MIN_DURATION, CLIP_MAX_DURATION,
)
from src.utils.logger import log


# ── The System Prompt (Virality Engine) ──────────
SYSTEM_PROMPT = """You are a world-class viral content producer and senior video editor.
Your client has hired you to turn their long-form video into maximum-impact short clips.
You think like a creative director — not a mindless slicer. You NEVER cut at arbitrary intervals.

**YOUR PROCESS (Chain of Thought):**
1. Read the entire transcript to understand the full narrative arc
2. Identify moments of peak emotional/intellectual intensity
3. For each candidate, ask: "Would I stop scrolling for THIS?"
4. Score each on the 4-pillar system below
5. SELF-CHECK: Verify every start/end falls on a word boundary. Verify no mid-sentence starts. Fix any that fail.

Select the {max_clips} most engaging, self-contained segments ({min_dur}-{max_dur} seconds each).

**SCORING SYSTEM (0-99 composite):**

| Pillar | Weight | 90+ Example | <30 Example |
|--------|--------|-------------|-------------|
| Hook (30%) | "The one indicator that never lies..." | "Um, so today..." or "Let me explain..." |
| Flow (25%) | Complete thought arc: setup → development → payoff | Mid-sentence cuts, dangling references |
| Value (25%) | Concrete takeaway + visual dynamism (movement, expressions, scene changes). Penalize static visuals with no B-roll potential. | Vague filler, motionless talking head with no visual hooks |
| Trend (20%) | Aligns with current cultural search momentum | Obscure niche with no broader appeal |

**virality_score = (hook * 0.30) + (flow * 0.25) + (value * 0.25) + (trend * 0.20)**

**VIRAL STRUCTURE PREFERENCE:**
ALWAYS prioritize segments with enumeration patterns ("3 reasons", "first", "number one", "here are").
Listicle/Proof structures have 15-20% higher retention than narrative storytelling.
When scanning segments:
- If enumeration markers detected → boost Hook score by +10
- If list structure spans 30-60s → automatic virality_score floor of 85

**ANTI-SLOP RULES:**
- NEVER select filler ("thanks for watching", "subscribe", "let me know in the comments")
- NEVER select segments just because they're near the beginning or end
- PREFER strong declarative statements, surprising reveals, or contrarian takes
- PREFER moments where the speaker's vocal energy is high

**VIRALITY THRESHOLD:**
ONLY output segments with virality_score ≥ 85. Reject:
- Filler commentary ("so yeah", "as I was saying")
- Low-energy explanations without conflict/surprise
- Segments with <75 Hook score (weak openings kill retention)

Prioritize: High-retention stories, contrarian takes, actionable tips, shocking reveals.

**CONTENT TYPE TAGGING:**
- `"talking_head"`: Speaker on camera (DEFAULT)
- `"screen_share"`: Charts, screens, visual data mentioned
- `"gameplay"`: Gaming footage (Minecraft, GTA, Subway Surfers, etc.) — use when: no visible human speaker, game UI/HUD present, transcript references game actions/mechanics. This mode uses center-crop for full-screen immersive framing.

**B-ROLL QUERY:**
For each segment, identify ONE 3-second window needing visual supplementation.
Provide `broll_query` (descriptive phrase) and `broll_insert_time` (offset from segment start).

**VISUAL STYLE:**
For each segment, identify the mood/vibe (e.g., "dark moody", "bright energetic", "luxury minimal").
Field: `visual_style`

**EMPHASIS MAP:**
For each segment, identify 3-6 high-impact words that deserve visual emphasis in captions:
- `"key_noun"`: Important nouns/subjects (highlighted green in captions)
- `"key_adjective"`: Power adjectives/verbs (highlighted yellow in captions)
- `"negative"`: Negative/warning words (highlighted red in captions)
Field: `emphasis_words` (list of {{"word": "...", "type": "..."}})

**IMPACT MOMENTS:**
Identify 1-3 timestamps within each segment where a dramatic beat, topic shift, or reveal occurs.
These are used for transition SFX (whoosh/impact sounds) placement.
Field: `impact_moments` (list of float offsets from segment start, in seconds)

**VISUAL VIABILITY:**
{visual_viability_context}
Before finalizing each segment, ask: "Does this segment have enough visual movement, expression changes, or scene variety to hold attention on a phone screen?"
- If the segment is visually static AND no strong B-roll opportunity exists, reduce the Value score by 10-15 points.
- Segments with dynamic gestures, scene changes, product demos, or strong facial expressions get a Value bonus.
Field: `visual_viability_score` (0-99, for debugging)

**STRICT RULES:**
1. Each segment MUST start with a hook in the first 3 seconds
2. Each segment MUST end on a COMPLETE thought (never mid-sentence)
3. Use exact word-level timestamps from the transcript
4. No overlapping segments
5. PREFER segments where the speaker is clearly visible or the subject is visually obvious (avoid vague or off-topic rants)
6. SELF-VERIFY all timestamps before responding

**OUTPUT FORMAT (STRICT JSON, NO MARKDOWN):**
[
  {{
    "start_time": 120.5,
    "end_time": 165.0,
    "virality_score": 87,
    "hook_score": 92,
    "flow_score": 85,
    "value_score": 88,
    "trend_score": 80,
    "layout_type": "talking_head",
    "proposed_title": "The One Indicator That Never Lies",
    "description": "Expert reveals the hidden signal most traders miss",
    "hook_text": "The one indicator that never lies...",
    "hashtags": ["#trading", "#stocks", "#investing", "#finance"],
    "broll_query": "close-up stock chart with green candles rising",
    "broll_insert_time": 12.0,
    "visual_style": "high-tech financial data visualization",
    "emphasis_words": [{{"word": "never", "type": "negative"}}, {{"word": "indicator", "type": "key_noun"}}, {{"word": "hidden", "type": "key_adjective"}}],
    "impact_moments": [8.5, 22.0],
    "visual_viability_score": 75
  }}
]

Return ONLY valid JSON. No markdown, no explanation, no code fences."""


def analyze_transcript(full_text: str, metadata: dict = None, motion_score: str = "unknown") -> list:
    """
    Send transcript to LLM and get viral segment suggestions.

    Args:
        full_text: Complete transcript text
        metadata: Optional dict with video title/description
        motion_score: CV-computed motion level ("low", "medium", "high", "unknown")

    Returns:
        List of clip dicts sorted by virality_score (highest first)
    """
    log("BRAIN", f"Analyzing transcript ({len(full_text)} chars)...")
    log("BRAIN", f"Motion score: {motion_score}")

    # Build visual viability context from CV signal
    motion_labels = {
        "low": "Motion_Score: Low (static shot / podcast / slideshow). Visually boring — penalize segments without strong B-roll potential.",
        "medium": "Motion_Score: Medium (casual vlog / moderate movement). Average visual engagement.",
        "high": "Motion_Score: High (dynamic action / walking / demos). Visually engaging — these segments hold attention well.",
        "unknown": "Motion_Score: Unknown (no CV data available). Judge visual viability from transcript context only.",
    }
    visual_viability_context = motion_labels.get(motion_score, motion_labels["unknown"])

    system = SYSTEM_PROMPT.format(
        max_clips=MAX_CLIPS_PER_VIDEO,
        min_dur=CLIP_MIN_DURATION,
        max_dur=CLIP_MAX_DURATION,
        visual_viability_context=visual_viability_context,
    )

    # Add context
    context = ""
    if metadata:
        title = metadata.get("title", "")
        desc = metadata.get("description", "")[:500]
        if title:
            context = f"\n\n**VIDEO CONTEXT:**\nTitle: {title}\nDescription: {desc}\n"

    user_prompt = f"{context}\n**TRANSCRIPT:**\n{full_text}"

    # ── Route to correct LLM provider ──────────
    if LLM_PROVIDER == "gemini":
        raw_text = _call_gemini(system, user_prompt)
    else:
        raw_text = _call_openai(system, user_prompt)

    # ── Parse response ─────────────────────────
    clips = _parse_response(raw_text)
    clips.sort(key=lambda c: c.get("virality_score", 0), reverse=True)
    clips = clips[:MAX_CLIPS_PER_VIDEO]

    log("BRAIN", f"Found {len(clips)} viral segments:", "OK")
    for i, clip in enumerate(clips):
        dur = clip["end"] - clip["start"]
        log("BRAIN", f"  {i+1}. [{clip['start']:.1f}s-{clip['end']:.1f}s] "
            f"Score: {clip['virality_score']}/99 | "
            f"Layout: {clip.get('layout_type', 'talking_head')} | "
            f"\"{clip.get('proposed_title', 'N/A')[:40]}\"")

    return clips


def _call_gemini(system: str, user_prompt: str) -> str:
    """Call Gemini API."""
    import google.generativeai as genai

    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not set in .env")

    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel(
        model_name=LLM_MODEL,
        system_instruction=system,
        generation_config=genai.GenerationConfig(
            temperature=GEMINI_TEMPERATURE,
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        ),
    )

    response = model.generate_content(user_prompt)
    return response.text.strip()


def _call_openai(system: str, user_prompt: str) -> str:
    """Call OpenAI-compatible API (works with LM Studio, Ollama, etc.)."""
    from openai import OpenAI

    client = OpenAI(
        api_key=OPENAI_API_KEY or "lm-studio",
        base_url=OPENAI_BASE_URL,
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=GEMINI_TEMPERATURE,
        max_tokens=GEMINI_MAX_OUTPUT_TOKENS,
    )

    return response.choices[0].message.content.strip()


def _parse_response(raw_text: str) -> list:
    """Parse LLM JSON response into validated clip list."""
    # Strip markdown fences
    cleaned = raw_text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        clips = json.loads(cleaned)
    except json.JSONDecodeError as e:
        log("BRAIN", f"JSON parse error: {e}", "ERROR")
        log("BRAIN", f"Raw: {raw_text[:200]}...", "DEBUG")
        return []

    if not isinstance(clips, list):
        clips = [clips]

    valid = []
    for clip in clips:
        if not isinstance(clip, dict):
            continue

        start = clip.get("start_time") or clip.get("start")
        end = clip.get("end_time") or clip.get("end")

        if start is None or end is None:
            continue

        try:
            start, end = float(start), float(end)
        except (ValueError, TypeError):
            continue

        duration = end - start
        if duration < CLIP_MIN_DURATION * 0.8:
            continue
        if duration > CLIP_MAX_DURATION * 1.2:
            end = start + CLIP_MAX_DURATION

        # Compute composite score if individual scores provided
        hook = float(clip.get("hook_score", 50))
        flow = float(clip.get("flow_score", 50))
        value = float(clip.get("value_score", 50))
        trend = float(clip.get("trend_score", 50))
        composite = clip.get("virality_score",
                             int(hook * 0.30 + flow * 0.25 + value * 0.25 + trend * 0.20))

        # VIRAL FORMULA: Boost score if enumeration markers detected (listicle preference)
        enumeration_markers = [
            "here are", "number one", "first reason", "three things", "3 reasons",
            "top 3", "top three", "first,", "second,", "third,", "finally,",
            "reason 1", "reason 2", "point number", "step one"
        ]
        description_text = str(clip.get("description", "")).lower()
        hook_text = str(clip.get("hook_text", "")).lower()
        title_text = str(clip.get("proposed_title", "")).lower()
        combined_text = f"{description_text} {hook_text} {title_text}"

        has_list_structure = any(marker in combined_text for marker in enumeration_markers)
        if has_list_structure:
            composite = min(100, composite + 10)  # +10 bonus for listicle structure
            log("BRAIN", f"  → Listicle detected! Boosting score: {composite}", "DEBUG")

        valid.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "virality_score": int(composite),
            "hook_score": int(hook),
            "flow_score": int(flow),
            "value_score": int(value),
            "trend_score": int(trend),
            "layout_type": clip.get("layout_type", "talking_head"),
            "proposed_title": str(clip.get("proposed_title", "")),
            "description": str(clip.get("description", "")),
            "hook_text": str(clip.get("hook_text", "")),
            "hashtags": clip.get("hashtags", []),
            "broll_query": str(clip.get("broll_query", "")),
            "broll_insert_time": float(clip.get("broll_insert_time", 0)),
            "visual_style": str(clip.get("visual_style", "cinematic")),
            "emphasis_words": clip.get("emphasis_words", []),
            "impact_moments": clip.get("impact_moments", []),
            "visual_viability_score": int(clip.get("visual_viability_score", 50)),
        })

    return valid
