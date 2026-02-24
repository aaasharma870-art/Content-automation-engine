"""
broll.py - Contextual B-Roll Engine (CLIP + FAISS)
====================================================
Uses OpenAI CLIP to semantically search a local B-roll library.
Builds a FAISS index of video frame embeddings, then matches
LLM-generated text queries to find the best visual supplement.

This is the "ClipAnything" equivalent.
"""

import os
import json
import subprocess
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import (
    BROLL_DIR, BROLL_INDEX_DIR, BROLL_SAMPLE_FRAMES, BROLL_OVERLAY_DURATION,
    PEXELS_CLIP_VERIFY, BROLL_MIN_SIMILARITY,
)
from src.utils.logger import log
from src.utils.ffmpeg_utils import FFMPEG_BIN
from src.modules.pexels_broll import search_pexels_video

# Lazy imports for heavy ML libraries
_clip_model = None
_clip_preprocess = None
_faiss_index = None
_index_metadata = []


def _ensure_clip_loaded():
    """Lazy-load CLIP model on first use."""
    global _clip_model, _clip_preprocess
    if _clip_model is not None:
        return

    try:
        import clip
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        log("BROLL", f"Loading CLIP model (ViT-B/32) on {device}...")
        _clip_model, _clip_preprocess = clip.load("ViT-B/32", device=device)
        log("BROLL", "CLIP loaded.", "OK")
    except ImportError:
        log("BROLL", "CLIP not installed. B-roll injection disabled.", "WARN")
        raise


def build_index(force_rebuild: bool = False) -> bool:
    """
    Scan assets/broll/, extract frames, generate CLIP embeddings,
    and store in a FAISS index.

    Returns:
        True if index was built successfully, False otherwise
    """
    global _faiss_index, _index_metadata

    index_path = BROLL_INDEX_DIR / "broll.index"
    meta_path = BROLL_INDEX_DIR / "broll_meta.json"

    # Skip if already built
    if not force_rebuild and index_path.exists() and meta_path.exists():
        try:
            import faiss
            _faiss_index = faiss.read_index(str(index_path))
            with open(meta_path, "r") as f:
                _index_metadata = json.load(f)
            log("BROLL", f"Loaded existing index ({len(_index_metadata)} clips)", "OK")
            return True
        except Exception:
            pass

    # Scan for video files
    broll_files = []
    for ext in ["*.mp4", "*.mov", "*.avi", "*.webm", "*.mkv"]:
        broll_files.extend(BROLL_DIR.glob(ext))

    if not broll_files:
        log("BROLL", "No B-roll files found in assets/broll/", "WARN")
        return False

    log("BROLL", f"Indexing {len(broll_files)} B-roll clips...")

    try:
        _ensure_clip_loaded()
        import clip
        import torch
        import faiss
        from PIL import Image
    except ImportError as e:
        log("BROLL", f"Missing dependency for B-roll: {e}", "ERROR")
        return False

    device = "cuda" if torch.cuda.is_available() else "cpu"
    all_embeddings = []
    _index_metadata = []

    for vf in broll_files:
        log("BROLL", f"  Processing: {vf.name}")
        frames = _extract_frames(str(vf), BROLL_SAMPLE_FRAMES)

        for i, frame_path in enumerate(frames):
            try:
                image = _clip_preprocess(Image.open(frame_path)).unsqueeze(0).to(device)
                with torch.no_grad():
                    embedding = _clip_model.encode_image(image)
                    embedding = embedding / embedding.norm(dim=-1, keepdim=True)
                    all_embeddings.append(embedding.cpu().numpy().flatten())
                    _index_metadata.append({
                        "video_path": str(vf),
                        "video_name": vf.stem,
                        "frame_index": i,
                    })
            except Exception as e:
                log("BROLL", f"  Frame embed failed: {e}", "WARN")
            finally:
                # Clean up temp frame
                try:
                    os.remove(frame_path)
                except OSError:
                    pass

    if not all_embeddings:
        log("BROLL", "No embeddings generated", "ERROR")
        return False

    # Build FAISS index
    embed_matrix = np.vstack(all_embeddings).astype("float32")
    dimension = embed_matrix.shape[1]

    _faiss_index = faiss.IndexFlatIP(dimension)  # Inner product (cosine on normalized)
    _faiss_index.add(embed_matrix)

    # Save to disk
    faiss.write_index(_faiss_index, str(index_path))
    with open(meta_path, "w") as f:
        json.dump(_index_metadata, f, indent=2)

    log("BROLL", f"Index built: {len(all_embeddings)} embeddings from {len(broll_files)} clips", "OK")
    return True


def find_broll(text_query: str, top_k: int = 1, **kwargs) -> list:
    """
    Search the FAISS index for B-roll matching a text description.

    Args:
        text_query: Natural language description of desired visual
        top_k: Number of results to return

    Returns:
        List of dicts with video_path and similarity score
    """
    global _faiss_index, _index_metadata

    if _faiss_index is None or not _index_metadata:
        if not build_index():
            return []

    try:
        _ensure_clip_loaded()
        import clip
        import torch
    except ImportError:
        return []

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Encode text query
    text_tokens = clip.tokenize([text_query]).to(device)
    with torch.no_grad():
        text_embedding = _clip_model.encode_text(text_tokens)
        text_embedding = text_embedding / text_embedding.norm(dim=-1, keepdim=True)
        query_vec = text_embedding.cpu().numpy().astype("float32")

    # Search FAISS
    scores, indices = _faiss_index.search(query_vec, top_k)

    results = []
    seen_videos = set()
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(_index_metadata):
            continue
        meta = _index_metadata[idx]
        video_path = meta["video_path"]

        # Deduplicate by video file
        if video_path in seen_videos:
            continue
        seen_videos.add(video_path)

        results.append({
            "video_path": video_path,
            "video_name": meta["video_name"],
            "similarity": float(score),
            "source": "clip",
            "is_fallback": False,
        })

    if results:
        log("BROLL", f"Best match for \"{text_query[:50]}\": "
            f"{results[0]['video_name']} (sim: {results[0]['similarity']:.3f})", "OK")
    else:
        # Fallback to Pexels if no local match
        log("BROLL", "No local match found. Trying Pexels...", "WARN")
        pexels_result = search_pexels_video(text_query, **kwargs)
        if pexels_result:
            # Optionally verify Pexels result with CLIP for a real similarity score
            pexels_similarity = None
            if PEXELS_CLIP_VERIFY:
                pexels_similarity = _verify_pexels_clip(
                    pexels_result["video_path"], text_query
                )
                if pexels_similarity is not None and pexels_similarity < BROLL_MIN_SIMILARITY:
                    log("BROLL", f"Pexels CLIP verification failed "
                        f"(sim: {pexels_similarity:.3f} < {BROLL_MIN_SIMILARITY})", "WARN")
                    pexels_similarity = None  # Mark as unverified fallback
                    pexels_result = None      # Discard poor match

            if pexels_result:
                results.append({
                    "video_path": pexels_result["video_path"],
                    "video_name": pexels_result["video_name"],
                    "similarity": pexels_similarity,  # None if unverified, real score if CLIP-checked
                    "source": "pexels",
                    "is_fallback": pexels_similarity is None,  # Only fallback if no real score
                })
                src_label = f"CLIP-verified (sim: {pexels_similarity:.3f})" if pexels_similarity else "keyword-only fallback"
                log("BROLL", f"Pexels result: {pexels_result['video_name']} ({src_label})", "OK")

    return results


def _verify_pexels_clip(video_path: str, text_query: str) -> float | None:
    """
    Download one frame from a Pexels video and compute actual CLIP similarity
    against the text query. Returns cosine similarity or None on failure.
    """
    try:
        _ensure_clip_loaded()
        import clip
        import torch
        from PIL import Image

        frames = _extract_frames(video_path, 1)
        if not frames:
            return None

        device = "cuda" if torch.cuda.is_available() else "cpu"
        image = _clip_preprocess(Image.open(frames[0])).unsqueeze(0).to(device)
        text_tokens = clip.tokenize([text_query]).to(device)

        with torch.no_grad():
            img_emb = _clip_model.encode_image(image)
            txt_emb = _clip_model.encode_text(text_tokens)
            img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)
            txt_emb = txt_emb / txt_emb.norm(dim=-1, keepdim=True)
            similarity = (img_emb @ txt_emb.T).item()

        # Clean up temp frame
        try:
            os.remove(frames[0])
        except OSError:
            pass

        log("BROLL", f"Pexels CLIP score: {similarity:.3f}", "DEBUG")
        return float(similarity)
    except Exception as e:
        log("BROLL", f"Pexels CLIP verification failed: {e}", "WARN")
        return None


def build_broll_ffmpeg_cmd(
    main_video: str,
    broll_video: str,
    insert_time: float,
    duration: float = BROLL_OVERLAY_DURATION,
) -> str:
    """
    Generate FFmpeg filter snippet to overlay B-roll at a specific time.

    The B-roll replaces the main video for `duration` seconds starting
    at `insert_time`, with the B-roll's own audio muted.

    Returns:
        FFmpeg filter_complex string fragment
    """
    # Scale B-roll to match target dimensions
    return (
        f"[broll]scale={1080}:{1920}:force_original_aspect_ratio=decrease,"
        f"pad={1080}:{1920}:(ow-iw)/2:(oh-ih)/2,"
        f"setpts=PTS-STARTPTS[broll_scaled];"
        f"[main][broll_scaled]overlay=enable='between(t,{insert_time},{insert_time + duration})'"
    )


def _extract_frames(video_path: str, num_frames: int) -> list:
    """Extract evenly spaced frames from a video using FFmpeg."""
    temp_dir = Path(video_path).parent
    frames = []

    # Get video duration via ffprobe (cross-platform safe)
    try:
        from src.modules.utils import get_ffprobe_bin
        ffprobe_bin = get_ffprobe_bin()
        result = subprocess.run(
            [ffprobe_bin, "-v", "quiet", "-show_entries",
             "format=duration", "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=30
        )
        duration = float(result.stdout.strip())
    except Exception:
        duration = 10.0  # Fallback

    interval = duration / (num_frames + 1)

    for i in range(num_frames):
        timestamp = interval * (i + 1)
        frame_path = str(temp_dir / f"_broll_frame_{Path(video_path).stem}_{i}.jpg")

        cmd = [
            FFMPEG_BIN, "-y", "-ss", str(timestamp),
            "-i", video_path, "-frames:v", "1",
            "-q:v", "2", "-hide_banner",
            frame_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)

        if Path(frame_path).exists():
            frames.append(frame_path)

    return frames
