"""
transcribe.py - The Ear (High-Precision Transcription)
=======================================================
Uses faster-whisper (CTranslate2) for GPU-accelerated transcription
with word-level timestamps. Includes timestamp refinement to snap
cut-points to silence boundaries (prevents cutting mid-word).
"""

import numpy as np
from faster_whisper import WhisperModel
from colorama import Fore, Style

from config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE


# ── Module-Level Model Cache ───────────────────
# Load the model once and reuse across calls
_model = None


def _get_model() -> WhisperModel:
    """Lazy-load the Whisper model (heavy init, do it once)."""
    global _model
    if _model is None:
        print(f"{Fore.MAGENTA}[TRANSCRIBE]{Style.RESET_ALL} Loading Whisper model '{WHISPER_MODEL}' on {WHISPER_DEVICE}...")
        try:
            _model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
        except Exception:
            # Fallback to CPU if CUDA fails
            print(f"{Fore.YELLOW}[TRANSCRIBE]{Style.RESET_ALL} CUDA failed, falling back to CPU (int8)...")
            _model = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
            )
        print(f"{Fore.GREEN}[TRANSCRIBE]{Style.RESET_ALL} ✓ Model loaded.")
    return _model


def transcribe_video(video_path: str) -> dict:
    """
    Transcribe a video file and extract word-level timestamps.
    
    Args:
        video_path: Path to the video/audio file
        
    Returns:
        dict with:
            - words: List of {word, start, end} dicts (word-level timing)
            - segments: List of {start, end, text} dicts (sentence-level)
            - full_text: Complete transcript as a single string
    """
    model = _get_model()
    
    print(f"{Fore.MAGENTA}[TRANSCRIBE]{Style.RESET_ALL} Transcribing: {video_path}")
    
    # ── Run transcription with word timestamps ───
    segments_iter, info = model.transcribe(
        video_path,
        beam_size=5,
        word_timestamps=True,         # CRITICAL: word-level timing
        vad_filter=True,              # Voice Activity Detection (skip silence)
        vad_parameters=dict(
            min_silence_duration_ms=300,
            speech_pad_ms=200,
        ),
    )
    
    print(f"{Fore.MAGENTA}[TRANSCRIBE]{Style.RESET_ALL} Language: {info.language} "
          f"(confidence: {info.language_probability:.1%})")
    
    all_words = []
    all_segments = []
    full_text_parts = []
    
    for segment in segments_iter:
        # Collect sentence-level segments
        all_segments.append({
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
        })
        full_text_parts.append(segment.text.strip())
        
        # Collect word-level timestamps
        if segment.words:
            for word in segment.words:
                all_words.append({
                    "word": word.word.strip(),
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                })
    
    full_text = " ".join(full_text_parts)
    
    print(f"{Fore.GREEN}[TRANSCRIBE]{Style.RESET_ALL} ✓ {len(all_words)} words, "
          f"{len(all_segments)} segments transcribed.")
    
    return {
        "words": all_words,
        "segments": all_segments,
        "full_text": full_text,
    }


def refine_timestamps(words: list, target_start: float, target_end: float) -> tuple:
    """
    Snap start/end times to the nearest silence boundary.
    
    This prevents cutting a word in half. It finds the nearest "gap" 
    between words (>= 0.2 seconds) and adjusts the timestamps.
    
    Args:
        words: List of word dicts with 'start' and 'end' keys
        target_start: Desired start time (seconds)
        target_end: Desired end time (seconds)
        
    Returns:
        Tuple of (refined_start, refined_end) in seconds
    """
    if not words:
        return target_start, target_end
    
    SNAP_THRESHOLD = 0.2  # seconds - minimum gap to be considered "silence"
    SEARCH_WINDOW = 2.0   # seconds - how far to search for a snap point
    
    # ── Find gaps between words ─────────────────
    gaps = []
    for i in range(len(words) - 1):
        gap_start = words[i]["end"]
        gap_end = words[i + 1]["start"]
        gap_duration = gap_end - gap_start
        if gap_duration >= SNAP_THRESHOLD:
            gaps.append({
                "time": (gap_start + gap_end) / 2,  # midpoint of the gap
                "gap_start": gap_start,
                "gap_end": gap_end,
                "duration": gap_duration,
            })
    
    # ── Snap start time ─────────────────────────
    refined_start = target_start
    best_gap = None
    best_distance = SEARCH_WINDOW
    
    for gap in gaps:
        distance = abs(gap["time"] - target_start)
        if distance < best_distance:
            best_distance = distance
            best_gap = gap
    
    if best_gap:
        # Snap to the END of the silence gap (right before next word)
        refined_start = best_gap["gap_end"]
    
    # ── Snap end time ───────────────────────────
    refined_end = target_end
    best_gap = None
    best_distance = SEARCH_WINDOW
    
    for gap in gaps:
        distance = abs(gap["time"] - target_end)
        if distance < best_distance:
            best_distance = distance
            best_gap = gap
    
    if best_gap:
        # Snap to the START of the silence gap (right after last word)
        refined_end = best_gap["gap_start"]
    
    # Safety: ensure refined values are valid
    refined_start = max(0, refined_start)
    if refined_end <= refined_start:
        refined_end = target_end  # revert if snapping broke things
    
    return round(refined_start, 3), round(refined_end, 3)


def get_words_in_range(words: list, start: float, end: float) -> list:
    """
    Extract all words that fall within a given time range.
    
    Args:
        words: Full word list from transcribe_video()
        start: Start time in seconds
        end: End time in seconds
        
    Returns:
        List of word dicts within the range, with times adjusted to be
        relative to the clip start (0-based).
    """
    clip_words = []
    for w in words:
        if w["start"] >= start and w["end"] <= end:
            clip_words.append({
                "word": w["word"],
                "start": round(w["start"] - start, 3),
                "end": round(w["end"] - start, 3),
            })
    return clip_words
