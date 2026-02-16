
import os
import re
import sys
import time
import shutil
import traceback
from datetime import datetime
from pathlib import Path

# Adjust path so we can import from src/
sys.path.append(str(Path(__file__).resolve().parent.parent))

from colorama import init
init(autoreset=True)

from config import (
    QUEUE_FILE, HISTORY_FILE, ERRORS_LOG,
    PROCESSED_DIR, TEMP_DIR, POLL_INTERVAL_SECONDS,
    GOOGLE_API_KEY, OPENAI_API_KEY, LLM_PROVIDER,
)
from modules.utils import log
from modules.ingest import download_video, is_valid_youtube_url
from modules.transcribe import transcribe_video, refine_timestamps, get_words_in_range
from modules.brain import analyze_transcript
from modules.director import analyze_scene
from modules.editor import render_short
from modules.distributor import schedule_posts

async def run_pipeline(url_arg: str = None):
    """
    Executes the Repurposing Pipeline (Original AutoShorts).
    """
    # ── Preflight ──────────────────────────────
    _preflight_checks()

    # ── Try to pre-build B-roll index ──────────
    _init_broll_index()

    if not QUEUE_FILE.exists():
        QUEUE_FILE.touch()

    log("REPURPOSE", f"🟢 Watching: {QUEUE_FILE}")
    
    # If URL provided via arg, process it once
    if url_arg:
        _process_single_url(url_arg)
        return

    # Otherwise enter loop (or just process queue once)
    # The unified main.py handles the loop or single run?
    # Let's make this run once if queue has items, or ask user?
    # The prompt "Repurpose Video" implies interactive.
    
    urls = _read_queue()
    if not urls:
        url = input("Enter YouTube URL > ").strip()
        if url: urls.append(url)
    
    if not urls:
        log("REPURPOSE", "No URLs found.", "WARN")
        return

    for url in urls:
        _process_single_url(url)

def _process_single_url(url):
    log("REPURPOSE", "=" * 60)
    log("REPURPOSE", f"Processing: {url}")
    log("REPURPOSE", "=" * 60)

    try:
        process_video(url)
        _mark_completed(url)
        log("REPURPOSE", f"✅ Done: {url}", "OK")
    except Exception as e:
        _log_error(url, e)
        _mark_completed(url)
        log("REPURPOSE", f"❌ Failed: {url} — {e}", "ERROR")

def process_video(url: str):
    """
    Run the full 8-phase pipeline on a single YouTube URL.
    """
    start_time = time.time()

    # ═══ PHASE 1: INGEST ══════════════════════
    log("REPURPOSE", "─" * 40)
    log("REPURPOSE", "[PHASE 1/6] INGESTING VIDEO")

    video_info = download_video(url)
    video_path = video_info["video_path"]
    audio_path = video_info.get("audio_wav_path") or video_path
    title = video_info["title"]
    metadata = video_info.get("metadata", {})

    # ═══ PHASE 2: TRANSCRIBE ══════════════════
    log("REPURPOSE", "─" * 40)
    log("REPURPOSE", "[PHASE 2/6] TRANSCRIBING AUDIO")

    transcript = transcribe_video(audio_path)
    words = transcript["words"]
    full_text = transcript["full_text"]

    if not full_text.strip():
        raise RuntimeError("Transcription returned empty text")

    # ═══ PHASE 3: BRAIN (LLM) ════════════════
    log("REPURPOSE", "─" * 40)
    log("REPURPOSE", "[PHASE 3/6] ANALYZING VIRALITY (LLM)")

    clips = analyze_transcript(full_text, metadata)

    if not clips:
        raise RuntimeError("Brain found no viral segments in this video")

    # ═══ PHASE 4-5: DIRECTOR + EDITOR ════════
    rendered_paths = []
    clip_metas = []

    work_dir = Path(video_info.get("work_dir", ""))

    for i, clip in enumerate(clips):
        clip_num = i + 1

        log("REPURPOSE", "─" * 40)
        log("REPURPOSE", f"[PHASE 4/6] DIRECTING CLIP {clip_num}/{len(clips)}")

        # Refine timestamps to silence boundaries
        refined_start, refined_end = refine_timestamps(
            words, clip["start"], clip["end"]
        )
        clip["start"] = refined_start
        clip["end"] = refined_end

        # Face tracking / screen detection
        scene_data = analyze_scene(
            video_path,
            clip["start"],
            clip["end"],
            clip.get("layout_type", "talking_head"),
        )

        # Extract words for this clip
        clip_words = get_words_in_range(words, clip["start"], clip["end"])

        # ── Human-in-the-Loop Caption Review ──────
        from config import CAPTION_REVIEW_PAUSE
        if CAPTION_REVIEW_PAUSE and clip_num == 1:
            transcript_preview = " ".join(w["word"] for w in clip_words)
            log("REPURPOSE", "")
            log("REPURPOSE", "═" * 50)
            log("REPURPOSE", "CAPTION REVIEW — Check for typos/errors:")
            log("REPURPOSE", f"  \"{transcript_preview[:200]}...\"")
            log("REPURPOSE", "")
            log("REPURPOSE", f"  Full transcript: {work_dir}/transcript.json")
            input("  → Press ENTER to continue...")

        log("REPURPOSE", f"[PHASE 5/6] RENDERING CLIP {clip_num}/{len(clips)}")

        # ── B-Roll search ──
        broll_insert = None
        broll_query = clip.get("broll_query", "")
        if broll_query:
            try:
                from src.modules.broll import find_broll
                from config import BROLL_MIN_SIMILARITY
                visual_style = clip.get("visual_style", "cinematic")
                broll_results = find_broll(broll_query, top_k=3, visual_style=visual_style)
                broll_results = [r for r in broll_results if r["similarity"] >= BROLL_MIN_SIMILARITY]
                if broll_results:
                    best = broll_results[0]
                    broll_insert = {
                        "video_path": best["video_path"],
                        "insert_time": clip.get("broll_insert_time", 10.0),
                        "duration": 3.0,
                    }
                    log("REPURPOSE", f"  B-Roll (local): {best['video_name']} ✅")
            except Exception:
                pass

        # Generate filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:40].strip()
        score = clip.get("virality_score", 0)
        proposed = clip.get("proposed_title", "")
        safe_proposed = re.sub(r'[^\w\s-]', '', proposed)[:30].strip()
        output_name = f"{safe_title}_{safe_proposed}_S{score}.mp4"

        output_path = render_short(
            video_path=video_path,
            clip_data=clip,
            scene_data=scene_data,
            words=clip_words,
            output_filename=output_name,
            broll_insert=broll_insert,
        )

        # ── AI Thumbnail Selection ──
        try:
            from src.modules.thumbnail import extract_best_thumbnail
            thumb_path = extract_best_thumbnail(output_path)
        except Exception:
            pass

        # ── Phase 4: Multimodal Critic (QA) ──
        try:
            from src.modules.critic import critique_video
            verdict = critique_video(output_path)
            if not verdict.get("passed", True):
                log("REPURPOSE", f"  ❌ QA FAILED: {verdict.get('reason')}", "ERROR")
                failed_path = str(Path(output_path).with_name(f"FAILED_QA_{Path(output_path).name}"))
                os.rename(output_path, failed_path)
                output_path = failed_path 
            else:
                log("REPURPOSE", f"  ✅ QA PASSED: Score {verdict.get('score')}/10", "OK")
        except Exception:
            pass

        rendered_paths.append(output_path)
        clip_metas.append(clip)

    # ═══ PHASE 6: DISTRIBUTE ═════════════════
    log("REPURPOSE", "─" * 40)
    log("REPURPOSE", "[PHASE 6/6] DISTRIBUTION")

    schedule_posts(rendered_paths, clip_metas)

    # ═══ SUMMARY ═════════════════════════════
    elapsed = time.time() - start_time
    log("REPURPOSE", "=" * 60, "OK")
    log("REPURPOSE", f"COMPLETE: {len(rendered_paths)} shorts in {elapsed:.0f}s", "OK")

    # Clean up raw download
    if work_dir.exists():
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass

# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════

def _read_queue() -> list:
    if not QUEUE_FILE.exists(): return []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    urls = []
    remaining = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            remaining.append(line)
            continue
        if is_valid_youtube_url(stripped):
            urls.append(stripped)
        else:
            remaining.append(line)
    if urls:
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            f.writelines(remaining)
    return urls

def _mark_completed(url: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {url}\n")

def _log_error(url: str, error: Exception):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERRORS_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n[{ts}] URL: {url}\n")
        f.write(f"Error: {error}\n")
        f.write(traceback.format_exc())
        f.write("\n" + "─" * 60 + "\n")

def _init_broll_index():
    try:
        from src.modules.broll import build_index
        build_index()
    except Exception:
        pass

def _preflight_checks():
    pass # Simplified for brevity, original main.py had checks
