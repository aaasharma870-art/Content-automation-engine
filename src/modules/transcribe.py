"""
transcribe.py - The Ear (High-Precision Transcription)
=======================================================
Uses faster-whisper (CTranslate2) for GPU-accelerated transcription
with word-level timestamps in milliseconds. Exports JSON with precise
temporal mapping for downstream subtitle animation and LLM curation.
"""

import json
from pathlib import Path
from faster_whisper import WhisperModel

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE
from src.utils.logger import log


# ── Module-Level Model Cache ───────────────────
_model = None


def _get_model() -> WhisperModel:
    """Lazy-load the Whisper model (heavy init, do it once)."""
    global _model
    if _model is None:
        log("TRANSCRIBE", f"Loading Whisper model '{WHISPER_MODEL}' on {WHISPER_DEVICE}...")
        try:
            _model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
        except Exception:
            log("TRANSCRIBE", "CUDA failed, falling back to CPU (int8)...", "WARN")
            _model = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
            )
        log("TRANSCRIBE", "Model loaded.", "OK")
    return _model


def transcribe_video(audio_path: str, save_json: bool = True) -> dict:
    """
    Transcribe audio and extract word-level timestamps (in seconds with ms precision).

    Args:
        audio_path: Path to .wav audio file (16kHz mono preferred)
        save_json: Whether to save transcript JSON alongside the audio

    Returns:
        dict with:
            - words: List of {word, start, end} (float seconds, ms precision)
            - segments: List of {start, end, text}
            - full_text: Complete transcript string
            - json_path: Path to saved JSON (if save_json=True)
    """
    model = _get_model()

    log("TRANSCRIBE", f"Transcribing: {Path(audio_path).name}")

    # ── Run transcription with word timestamps ───
    segments_iter, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,         # CRITICAL: word-level timing (ms precision)
        vad_filter=True,              # Voice Activity Detection
        vad_parameters=dict(
            min_silence_duration_ms=300,
            speech_pad_ms=200,
        ),
    )

    log("TRANSCRIBE", f"Language: {info.language} (confidence: {info.language_probability:.1%})")

    all_words = []
    all_segments = []
    full_text_parts = []

    for segment in segments_iter:
        all_segments.append({
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
        })
        full_text_parts.append(segment.text.strip())

        if segment.words:
            for word in segment.words:
                all_words.append({
                    "word": word.word.strip(),
                    "start": round(word.start, 3),  # float seconds with ms precision
                    "end": round(word.end, 3),
                    "start_ms": int(word.start * 1000),  # Also store as integer ms
                    "end_ms": int(word.end * 1000),
                })

    full_text = " ".join(full_text_parts)

    log("TRANSCRIBE", f"{len(all_words)} words, {len(all_segments)} segments transcribed.", "OK")

    result = {
        "words": all_words,
        "segments": all_segments,
        "full_text": full_text,
        "language": info.language,
    }

    # ── Save JSON to disk ──────────────────────────
    if save_json:
        json_path = Path(audio_path).parent / "transcript.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        result["json_path"] = str(json_path)
        log("TRANSCRIBE", f"Saved: {json_path.name}", "OK")

    return result


def refine_timestamps(words: list, target_start: float, target_end: float) -> tuple:
    """
    Snap start/end times to the nearest silence boundary.
    Prevents cutting a word in half.

    Args:
        words: List of word dicts with 'start' and 'end'
        target_start: Desired start (seconds)
        target_end: Desired end (seconds)

    Returns:
        (refined_start, refined_end) in seconds
    """
    if not words:
        return target_start, target_end

    SNAP_THRESHOLD = 0.2
    SEARCH_WINDOW = 2.0

    gaps = []
    for i in range(len(words) - 1):
        gap_start = words[i]["end"]
        gap_end = words[i + 1]["start"]
        gap_duration = gap_end - gap_start
        if gap_duration >= SNAP_THRESHOLD:
            gaps.append({
                "time": (gap_start + gap_end) / 2,
                "gap_start": gap_start,
                "gap_end": gap_end,
            })

    # Snap start time
    refined_start = target_start
    best_distance = SEARCH_WINDOW
    for gap in gaps:
        distance = abs(gap["time"] - target_start)
        if distance < best_distance:
            best_distance = distance
            refined_start = gap["gap_end"]

    # Snap end time
    refined_end = target_end
    best_distance = SEARCH_WINDOW
    for gap in gaps:
        distance = abs(gap["time"] - target_end)
        if distance < best_distance:
            best_distance = distance
            refined_end = gap["gap_start"]

    refined_start = max(0, refined_start)
    if refined_end <= refined_start:
        refined_end = target_end

    return round(refined_start, 3), round(refined_end, 3)


def get_words_in_range(words: list, start: float, end: float) -> list:
    """
    Extract words within a time range with 0-based relative timestamps.

    Returns:
        List of word dicts with times relative to clip start.
    """
    clip_words = []
    for w in words:
        if w["start"] >= start and w["end"] <= end:
            clip_words.append({
                "word": w["word"],
                "start": round(w["start"] - start, 3),
                "end": round(w["end"] - start, 3),
                "start_ms": int((w["start"] - start) * 1000),
                "end_ms": int((w["end"] - start) * 1000),
            })
    return clip_words
