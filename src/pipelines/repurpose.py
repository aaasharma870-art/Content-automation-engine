
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
    MAX_CLIPS_PER_VIDEO,
)
from src.modules.utils import log
from src.modules.ingest import download_video, is_valid_youtube_url
from src.modules.transcribe import transcribe_video, refine_timestamps, get_words_in_range
from src.modules.brain import analyze_transcript
from src.modules.director import analyze_scene
from src.modules.editor import render_short
from src.modules.distributor import schedule_posts

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

def _is_already_processed(url: str) -> bool:
    """Check if URL was already processed (exists in history.txt)."""
    if not HISTORY_FILE.exists():
        return False
    try:
        history = HISTORY_FILE.read_text(encoding="utf-8")
        return url.strip() in history
    except Exception:
        return False

def _process_single_url(url):
    # Check if already processed
    if _is_already_processed(url):
        log("REPURPOSE", f"Skipping (already processed): {url}", "WARN")
        return

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

    motion_score = video_info.get("motion_score", "unknown")
    clips = analyze_transcript(full_text, metadata, motion_score=motion_score)

    # ENGAGEMENT FILTER: Only keep top-tier clips (virality_score >= 85)
    clips = [c for c in clips if c.get("virality_score", 0) >= 85]

    # Remove overlapping clips (keep higher-scored one)
    clips = _remove_overlaps(clips)

    clips = clips[:MAX_CLIPS_PER_VIDEO]  # Hard cap at 3 (quality over quantity)

    log("REPURPOSE", f"After filtering: {len(clips)} clips passed virality threshold (≥85)")

    if not clips:
        raise RuntimeError("Brain found no viral segments in this video (no clips passed virality_score ≥ 85)")

    # ═══ PHASE 4-5: DIRECTOR + EDITOR ════════
    rendered_paths = []
    clip_metas = []

    work_dir = Path(video_info.get("work_dir", ""))

    batch_used_broll = set()  # Prevent same b-roll across clips in this batch

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

        # ── B-Roll search (multiple inserts) ──
        broll_inserts = []
        broll_queries = clip.get("broll_queries", [])

        # Backward compat: single query format
        if not broll_queries:
            single_query = clip.get("broll_query", "")
            if single_query and len(single_query) > 5:
                broll_queries = [{"query": single_query, "insert_time": clip.get("broll_insert_time", 10.0)}]

        clip_duration = clip["end"] - clip["start"]

        if broll_queries and clip_duration > 15:
            try:
                from src.modules.broll import find_broll
                from config import BROLL_MIN_SIMILARITY, ALLOW_BROLL_FALLBACK
                visual_style = clip.get("visual_style", "cinematic")

                used_videos = set(batch_used_broll)  # Inherit batch-level + per-clip dedup

                for bq in broll_queries[:4]:  # Cap at 4 b-roll inserts
                    query_text = bq.get("query", "")
                    insert_time = float(bq.get("insert_time", 10.0))

                    if not query_text or len(query_text) < 3:
                        continue

                    broll_results = find_broll(query_text, top_k=3, visual_style=visual_style)

                    valid_results = [
                        r for r in broll_results
                        if r["video_path"] not in used_videos
                        and ((r.get("similarity") is not None and r["similarity"] >= BROLL_MIN_SIMILARITY)
                             or (r.get("is_fallback") and ALLOW_BROLL_FALLBACK))
                    ]

                    if valid_results:
                        best = valid_results[0]
                        used_videos.add(best["video_path"])
                        batch_used_broll.add(best["video_path"])
                        broll_inserts.append({
                            "video_path": best["video_path"],
                            "insert_time": insert_time,
                            "duration": 3.0,
                        })
                        sim_label = f"Sim: {best['similarity']:.2f}" if best.get("similarity") is not None else "fallback"
                        log("REPURPOSE", f"  B-Roll [{len(broll_inserts)}]: {best['video_name']} ({sim_label}) at t={insert_time:.1f}s")

                if not broll_inserts:
                    log("REPURPOSE", f"  No B-roll found meeting quality threshold")

            except Exception as e:
                log("REPURPOSE", f"  B-Roll search failed: {e}", "WARN")

        # Generate filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:40].strip()
        score = clip.get("virality_score", 0)
        proposed = clip.get("proposed_title", "")
        safe_proposed = re.sub(r'[^\w\s-]', '', proposed)[:30].strip()
        output_name = f"{safe_title}_{safe_proposed}_S{score}.mp4"

        # Tag clip with content mode for downstream context-aware decisions
        clip["content_mode"] = "repurpose"

        output_path = render_short(
            video_path=video_path,
            clip_data=clip,
            scene_data=scene_data,
            words=clip_words,
            output_filename=output_name,
            broll_inserts=broll_inserts if broll_inserts else None,
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

def _remove_overlaps(clips: list) -> list:
    """Remove overlapping clips, keeping the higher-scored one."""
    if len(clips) <= 1:
        return clips
    # Already sorted by virality_score descending
    kept = []
    for clip in clips:
        overlaps = False
        for existing in kept:
            # Check if clips overlap
            if clip["start"] < existing["end"] and clip["end"] > existing["start"]:
                overlaps = True
                break
        if not overlaps:
            kept.append(clip)
    return kept

def _init_broll_index():
    try:
        from src.modules.broll import build_index
        build_index()
    except Exception:
        pass

def _preflight_checks():
    """Verify required assets (fonts, LUTs, SFX) and auto-download what's missing."""
    try:
        from src.utils.asset_manager import ensure_all_assets
        ensure_all_assets()
    except Exception as e:
        log("REPURPOSE", f"Asset check failed (non-fatal): {e}", "WARN")
