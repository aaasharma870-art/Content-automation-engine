"""
Reddit Story Pipeline — Scrape viral stories and overlay TTS on gameplay backgrounds.

Usage:
    python -m src.pipelines.reddit --background gameplay.mp4 --subreddit TrueOffMyChest
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import urllib.request
import subprocess
from src.utils.logger import log
from config import OUTPUT_DIR, TARGET_WIDTH, TARGET_HEIGHT
import re
import random
import tempfile

def _prepare_dynamic_background(background_source: str, target_duration: float) -> str:
    """
    Prepare background video: loop single file OR concatenate multiple from directory.

    Args:
        background_source: Path to video file OR directory of videos
        target_duration: Required total duration in seconds

    Returns:
        Path to prepared background video (either original or concatenated temp file)
    """
    bg_path = Path(background_source)

    # If it's a single file, return as-is (will be looped by FFmpeg)
    if bg_path.is_file():
        log("REDDIT", f"Using single background: {bg_path.name}")
        return str(bg_path)

    # If it's a directory, concatenate random clips
    if bg_path.is_dir():
        video_files = []
        for ext in ['*.mp4', '*.mov', '*.avi', '*.mkv']:
            video_files.extend(bg_path.glob(ext))

        if not video_files:
            raise ValueError(f"No video files found in directory: {background_source}")

        log("REDDIT", f"Found {len(video_files)} background videos in directory")

        # Shuffle and select clips to meet duration
        random.shuffle(video_files)
        selected_clips = []
        total_duration = 0.0

        for video in video_files:
            # Get video duration
            clip_duration = _get_video_duration(str(video))
            selected_clips.append(str(video))
            total_duration += clip_duration

            # Stop when we have enough footage (with 20% buffer)
            if total_duration >= target_duration * 1.2:
                break

        log("REDDIT", f"Selected {len(selected_clips)} clips (total: {total_duration:.1f}s for {target_duration:.1f}s target)")

        # Create concat file for FFmpeg
        concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        for clip in selected_clips:
            # FFmpeg concat demuxer requires absolute paths if the txt file is in Temp dir
            abs_clip = str(Path(clip).resolve()).replace(chr(92), '/')
            concat_file.write(f"file '{abs_clip}'\n")
        concat_file.close()

        # Concatenate clips using FFmpeg concat demuxer
        output_path = str(OUTPUT_DIR / "temp_background_concat.mp4")
        from src.modules.utils import get_ffmpeg_bin

        cmd = [
            get_ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file.name,
            "-c", "copy",  # Stream copy for speed (no re-encoding)
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Fallback: re-encode if stream copy fails
            log("REDDIT", "Stream copy failed, re-encoding...", "WARN")
            cmd = [
                get_ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file.name,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                output_path
            ]
            subprocess.run(cmd, check=True)

        # Cleanup concat file
        Path(concat_file.name).unlink()

        log("REDDIT", f"Concatenated background saved: {output_path}", "OK")
        return output_path

    raise ValueError(f"Invalid background source: {background_source} (must be file or directory)")


def _get_video_duration(file_path: str) -> float:
    """Get video duration using ffprobe."""
    from src.modules.utils import get_ffprobe_bin

    cmd = [
        get_ffprobe_bin(), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 10.0  # Default fallback


def _clean_reddit_text(text: str) -> str:
    """
    Remove Reddit-specific noise from story text.
    Strips: Edit notes, TL;DR sections, Update markers, emoji spam, etc.
    """
    if not text:
        return text

    # Remove common Reddit noise patterns
    noise_patterns = [
        r"(?i)edit\s*\d*\s*[:：]\s*.+?(?=\n\n|\Z)",  # Edit: ... (until double newline or end)
        r"(?i)update\s*\d*\s*[:：]\s*.+?(?=\n\n|\Z)",  # Update: ...
        r"(?i)tl\s*;\s*dr\s*[:：]?.+?(?=\n\n|\Z)",  # TL;DR: ...
        r"(?i)thanks\s+for\s+the\s+gold.+?(?=\n\n|\Z)",  # Thanks for the gold/awards
        r"(?i)obligatory\s+mobile\s+apology.+?(?=\n\n|\Z)",  # Mobile formatting apologies
        r"\[deleted\]|\[removed\]",  # Deleted/removed markers
        r"^#+\s+.+$",  # Reddit markdown headers (##)
    ]

    cleaned = text
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE | re.DOTALL)

    # Remove excessive newlines and whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Max 2 consecutive newlines
    cleaned = cleaned.strip()

    return cleaned

def fetch_reddit_story(subreddit: str = "TrueOffMyChest", time_filter: str = "day") -> dict | None:
    """
    Fetch top story from subreddit using Reddit's public JSON API.

    Args:
        subreddit: Subreddit name (e.g., "TrueOffMyChest", "AITA", "AskReddit")
        time_filter: Time window ("hour", "day", "week", "month", "year", "all")

    Returns:
        dict with keys: title, body, author, score
        None if no suitable story found
    """
    url = f"https://www.reddit.com/r/{subreddit}/top.json?t={time_filter}&limit=10"
    headers = {"User-Agent": "AutoShorts/2.0 (Educational Project)"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        # Find first text post with substantial content
        for post in data["data"]["children"]:
            post_data = post["data"]
            selftext = post_data.get("selftext", "")

            # Filter criteria: text post, >200 chars, not removed/deleted
            if selftext and len(selftext) > 200 and "[removed]" not in selftext.lower():
                # Clean Reddit noise before returning
                cleaned_body = _clean_reddit_text(selftext)[:1000]  # Limit to ~1000 chars for TTS

                # Re-check length after cleaning (some stories might be too short now)
                if len(cleaned_body) < 150:
                    continue

                return {
                    "title": post_data["title"],
                    "body": cleaned_body,
                    "author": post_data["author"],
                    "score": post_data["score"],
                    "permalink": f"https://reddit.com{post_data['permalink']}"
                }

        log("REDDIT", f"No suitable stories found in r/{subreddit}", "WARN")
        return None

    except Exception as e:
        log("REDDIT", f"Failed to fetch from r/{subreddit}: {e}", "ERROR")
        return None


async def build_reddit_video(background_video: str, subreddit: str = "TrueOffMyChest") -> str:
    """
    Generate Reddit Story video: fetch story → TTS → overlay on looping gameplay.

    Args:
        background_video: Path to gameplay video (e.g., Subway Surfers, Minecraft)
        subreddit: Source subreddit

    Returns:
        Path to rendered video file

    Raises:
        ValueError: If no suitable story found
        RuntimeError: If rendering fails
    """
    from src.modules.audio import generate_narration
    from src.modules.editor import generate_ass_subtitles, normalize_audio

    log("REDDIT", f"Fetching story from r/{subreddit}...")

    story = fetch_reddit_story(subreddit)
    if not story:
        raise ValueError(f"No suitable story found in r/{subreddit}")

    log("REDDIT", f"Found story: \"{story['title'][:60]}...\" ({story['score']} upvotes)")

    # Combine title + body
    full_text = f"{story['title']}. {story['body']}"

    # Generate TTS with high-energy voice
    # audio.py expects: generate_narration(text, vibe, output_path)
    # REDDIT vibe maps to en-US-SteffanNeural (dynamic, high-energy cadence)
    audio_path = str(OUTPUT_DIR / "reddit_audio.mp3")
    log("REDDIT", "Generating TTS narration (high-energy voice)...")
    await generate_narration(full_text, vibe="REDDIT", output_path=audio_path)

    # Normalize audio to -24 LUFS
    normalized_audio = str(OUTPUT_DIR / "reddit_audio_normalized.m4a")
    log("REDDIT", "Normalizing audio...")
    normalize_audio(audio_path, normalized_audio)

    # Generate subtitles BEFORE mixing music (Whisper needs clean voice-only audio)
    from src.modules.audio import generate_subtitles
    log("REDDIT", "Transcribing and aligning audio for subtitles...")
    words = generate_subtitles(normalized_audio)

    # Generate captions (.ass)
    ass_path = str(OUTPUT_DIR / "reddit_captions.ass")
    log("REDDIT", "Generating captions...")
    generate_ass_subtitles(words, ass_path)

    # NOW mix with background music (lofi mood for Reddit stories)
    from src.modules.editor import select_background_music, build_sidechain_audio

    audio_duration_for_mix = _get_audio_duration(normalized_audio)

    music_path = select_background_music(
        visual_style=None,
        duration=audio_duration_for_mix,
        content_mode="reddit",
        proposed_title=story["title"],
        content_mood="lofi",
    )

    final_audio = normalized_audio  # Default to voice-only
    if music_path:
        mixed_audio = str(OUTPUT_DIR / "reddit_audio_mixed.m4a")
        build_sidechain_audio(normalized_audio, music_path, mixed_audio, audio_duration_for_mix)
        final_audio = mixed_audio
        log("REDDIT", "Background music mixed with sidechain ducking", "OK")

    # Get audio duration
    audio_duration = _get_audio_duration(final_audio)
    log("REDDIT", f"Audio duration: {audio_duration:.1f}s")

    # Prepare dynamic background (concatenate if directory, or use single file)
    log("REDDIT", "Preparing background video...")
    prepared_background = _prepare_dynamic_background(background_video, audio_duration)

    # Render final video
    output_path = str(OUTPUT_DIR / f"reddit_{subreddit}_{story['author']}.mp4")
    log("REDDIT", "Rendering video...")

    # Escape ASS path for FFmpeg filter
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    from src.modules.utils import get_ffmpeg_bin

    cmd = [
        get_ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
        "-stream_loop", "-1", "-i", prepared_background,  # Loop/use concatenated background
        "-i", final_audio,
        "-filter_complex", (
            f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},"
            f"ass='{ass_escaped}'[vout]"
        ),
        "-map", "[vout]", "-map", "1:a",
        "-t", str(audio_duration),  # Trim to audio duration
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log("REDDIT", f"FFmpeg error: {result.stderr[-500:]}", "ERROR")
        raise RuntimeError("Video rendering failed")

    log("REDDIT", f"Video saved: {output_path}", "OK")
    return output_path


def _get_audio_duration(file_path: str) -> float:
    """Get audio/video duration using ffprobe (cross-platform safe)."""
    from src.modules.utils import get_ffprobe_bin

    cmd = [
        get_ffprobe_bin(), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 60.0  # Default fallback


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Reddit Story Video Generator")
    parser.add_argument("--background", "-b", required=True, help="Background video path (e.g., gameplay.mp4)")
    parser.add_argument("--subreddit", "-s", default="TrueOffMyChest", help="Subreddit to scrape (default: TrueOffMyChest)")
    args = parser.parse_args()

    # Verify background video exists
    if not Path(args.background).exists():
        print(f"ERROR: Background video not found: {args.background}")
        sys.exit(1)

    # Run async pipeline
    asyncio.run(build_reddit_video(args.background, args.subreddit))
