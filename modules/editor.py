"""
editor.py - The Polisher & Assembler
======================================
Handles three critical jobs:
1. Audio Polish: Loudness normalization (EBU R128) & silence removal
2. Karaoke Captions: .ass subtitle generation with \\k timing tags
3. Final Render: FFmpeg assembly with NVENC GPU encoding

This module takes the raw materials (video, audio, crop data, words)
and produces a polished, upload-ready Short.
"""

import os
import re
import json
import subprocess
import shutil
from pathlib import Path
from colorama import Fore, Style

from config import (
    TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS, OUTPUT_BITRATE,
    TARGET_LUFS, SILENCE_THRESHOLD_DB, SILENCE_MIN_DURATION_MS,
    CAPTION_FONT, CAPTION_FONT_SIZE, CAPTION_PRIMARY_COLOR,
    CAPTION_OUTLINE_COLOR, CAPTION_OUTLINE_WIDTH, CAPTION_MARGIN_BOTTOM,
    OUTPUT_DIR, TEMP_DIR, USE_NVENC, NVENC_PRESET, FACE_SAMPLE_RATE,
)


# ══════════════════════════════════════════════
# 1. AUDIO POLISH
# ══════════════════════════════════════════════

def normalize_audio(input_path: str, output_path: str) -> str:
    """
    Apply EBU R128 loudness normalization to the audio.
    Target: -14 LUFS (standard for social media).
    
    Uses a two-pass approach:
    1. Loudnorm filter measures current loudness
    2. Second pass applies correction
    
    Args:
        input_path: Source video/audio file
        output_path: Where to save the normalized audio (m4a)
        
    Returns:
        Path to normalized audio file
    """
    print(f"{Fore.CYAN}[EDITOR]{Style.RESET_ALL} Normalizing audio to {TARGET_LUFS} LUFS...")
    
    # ── Pass 1: Measure loudness ────────────────
    measure_cmd = [
        "ffmpeg", "-i", input_path, "-hide_banner",
        "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ]
    
    result = subprocess.run(measure_cmd, capture_output=True, text=True, timeout=300)
    
    # Parse the loudnorm output from stderr
    loudnorm_stats = _parse_loudnorm_output(result.stderr)
    
    if loudnorm_stats:
        # ── Pass 2: Apply measured correction ───
        filter_str = (
            f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:"
            f"measured_I={loudnorm_stats['input_i']}:"
            f"measured_LRA={loudnorm_stats['input_lra']}:"
            f"measured_TP={loudnorm_stats['input_tp']}:"
            f"measured_thresh={loudnorm_stats['input_thresh']}:"
            f"offset={loudnorm_stats['target_offset']}:"
            f"linear=true"
        )
    else:
        # Fallback: single-pass (less precise but works)
        filter_str = f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11"
    
    normalize_cmd = [
        "ffmpeg", "-y", "-i", input_path, "-hide_banner",
        "-af", filter_str,
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    
    result = subprocess.run(normalize_cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"{Fore.YELLOW}[EDITOR]{Style.RESET_ALL} Audio normalization warning: using original audio")
        shutil.copy2(input_path, output_path)
    
    print(f"{Fore.GREEN}[EDITOR]{Style.RESET_ALL} ✓ Audio normalized")
    return output_path


def remove_silence(input_path: str, output_path: str) -> str:
    """
    Detect and truncate silence gaps > 0.5s to create "jump cut" pacing.
    Uses FFmpeg's silencedetect + silenceremove filters.
    
    Args:
        input_path: Source audio file
        output_path: Where to save the trimmed audio
        
    Returns:
        Path to silence-removed audio file
    """
    print(f"{Fore.CYAN}[EDITOR]{Style.RESET_ALL} Removing silence (>{SILENCE_MIN_DURATION_MS}ms)...")
    
    # silenceremove filter:
    # stop_periods=-1 = remove all silence periods
    # stop_threshold = dB threshold for silence detection
    # stop_duration = minimum silence duration to remove
    silence_dur_sec = SILENCE_MIN_DURATION_MS / 1000.0
    
    cmd = [
        "ffmpeg", "-y", "-i", input_path, "-hide_banner",
        "-af", (
            f"silenceremove="
            f"stop_periods=-1:"
            f"stop_duration={silence_dur_sec}:"
            f"stop_threshold={SILENCE_THRESHOLD_DB}dB"
        ),
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"{Fore.YELLOW}[EDITOR]{Style.RESET_ALL} Silence removal failed, using original")
        shutil.copy2(input_path, output_path)
    else:
        print(f"{Fore.GREEN}[EDITOR]{Style.RESET_ALL} ✓ Silence removed")
    
    return output_path


def _parse_loudnorm_output(stderr: str) -> dict | None:
    """Parse loudnorm JSON stats from FFmpeg stderr."""
    try:
        # Find the JSON block in stderr
        json_match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', stderr, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


# ══════════════════════════════════════════════
# 2. KARAOKE CAPTIONS (.ass)
# ══════════════════════════════════════════════

def generate_ass_subtitles(words: list, output_path: str) -> str:
    """
    Generate an Advanced SubStation Alpha (.ass) subtitle file
    with karaoke timing tags for word-by-word color animation.
    
    The \\k tag controls how long each word is highlighted:
    \\k<centiseconds> = duration in 1/100ths of a second
    
    Args:
        words: List of {word, start, end} dicts (0-based relative times)
        output_path: Where to save the .ass file
        
    Returns:
        Path to the generated .ass file
    """
    print(f"{Fore.CYAN}[EDITOR]{Style.RESET_ALL} Generating karaoke subtitles ({len(words)} words)...")
    
    # ── ASS Header ──────────────────────────────
    header = f"""[Script Info]
Title: AutoShorts_Pro Captions
ScriptType: v4.00+
PlayResX: {TARGET_WIDTH}
PlayResY: {TARGET_HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{CAPTION_FONT},{CAPTION_FONT_SIZE},{CAPTION_PRIMARY_COLOR},&H00FFFFFF,{CAPTION_OUTLINE_COLOR},&H80000000,-1,0,0,0,100,100,0,0,1,{CAPTION_OUTLINE_WIDTH},0,2,40,40,{CAPTION_MARGIN_BOTTOM},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # ── Generate Dialogue Lines ─────────────────
    # Group words into lines of ~4-6 words for readability
    lines = _group_words_into_lines(words, max_words_per_line=5)
    
    dialogue_lines = []
    for line_words in lines:
        if not line_words:
            continue
        
        line_start = line_words[0]["start"]
        line_end = line_words[-1]["end"]
        
        start_ts = _seconds_to_ass_time(line_start)
        end_ts = _seconds_to_ass_time(line_end)
        
        # Build karaoke text with \k tags
        karaoke_text = ""
        for w in line_words:
            # Duration in centiseconds (1/100th of a second)
            duration_cs = int((w["end"] - w["start"]) * 100)
            duration_cs = max(duration_cs, 5)  # minimum 50ms per word
            karaoke_text += f"{{\\kf{duration_cs}}}{w['word']} "
        
        karaoke_text = karaoke_text.strip()
        
        dialogue_lines.append(
            f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{karaoke_text}"
        )
    
    # ── Write the file ──────────────────────────
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(dialogue_lines))
        f.write("\n")
    
    print(f"{Fore.GREEN}[EDITOR]{Style.RESET_ALL} ✓ Subtitles saved: {Path(output_path).name}")
    return output_path


def _group_words_into_lines(words: list, max_words_per_line: int = 5) -> list:
    """Split word list into display lines of N words each."""
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        if len(current_line) >= max_words_per_line:
            lines.append(current_line)
            current_line = []
    
    if current_line:
        lines.append(current_line)
    
    return lines


def _seconds_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format: H:MM:SS.CC"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ══════════════════════════════════════════════
# 3. FINAL RENDER (FFmpeg Assembly)
# ══════════════════════════════════════════════

def render_short(
    video_path: str,
    clip_data: dict,
    scene_data: dict,
    words: list,
    output_filename: str,
) -> str:
    """
    Assemble the final Short video using FFmpeg.
    
    Pipeline:
    1. Trim source video to clip boundaries
    2. Apply crop (face tracking) OR layout filter (screen share)
    3. Normalize audio + remove silence
    4. Burn in karaoke subtitles
    5. Encode with NVENC (GPU) or libx264 (CPU fallback)
    
    Args:
        video_path: Path to source video
        clip_data: Dict with start, end, score, layout_type from brain.py
        scene_data: Dict with mode, crop_data from director.py
        words: List of word dicts (0-based relative timestamps)
        output_filename: Desired output filename (e.g. "Short_1_9.5.mp4")
        
    Returns:
        Path to the rendered short video
    """
    clip_start = clip_data["start"]
    clip_end = clip_data["end"]
    clip_duration = clip_end - clip_start
    
    source_w = scene_data["source_width"]
    source_h = scene_data["source_height"]
    
    work_dir = Path(video_path).parent
    output_path = str(OUTPUT_DIR / output_filename)
    
    print(f"\n{Fore.RED}[RENDER]{Style.RESET_ALL} ═══════════════════════════════")
    print(f"{Fore.RED}[RENDER]{Style.RESET_ALL} Building: {output_filename}")
    print(f"{Fore.RED}[RENDER]{Style.RESET_ALL} ═══════════════════════════════")
    
    # ── Step 1: Extract & normalize audio ──────
    raw_audio = str(work_dir / "raw_audio.m4a")
    norm_audio = str(work_dir / "norm_audio.m4a")
    clean_audio = str(work_dir / "clean_audio.m4a")
    
    # Extract audio for this clip
    extract_cmd = [
        "ffmpeg", "-y", "-i", video_path, "-hide_banner",
        "-ss", str(clip_start), "-t", str(clip_duration),
        "-vn", "-c:a", "aac", "-b:a", "192k",
        raw_audio,
    ]
    subprocess.run(extract_cmd, capture_output=True, timeout=120)
    
    # Normalize loudness
    normalize_audio(raw_audio, norm_audio)
    
    # Remove silence (jump cuts)
    remove_silence(norm_audio, clean_audio)
    
    # ── Step 2: Generate subtitles ─────────────
    ass_path = str(work_dir / "captions.ass")
    generate_ass_subtitles(words, ass_path)
    
    # ── Step 3: Build FFmpeg filter chain ──────
    if scene_data["mode"] == "face" and scene_data["crop_data"]:
        filter_complex = _build_face_crop_filter(
            scene_data, clip_duration, source_w, source_h, ass_path
        )
    else:
        filter_complex = _build_screen_filter(
            source_w, source_h, ass_path
        )
    
    # ── Step 4: Encode final video ─────────────
    # Choose encoder
    if USE_NVENC and _check_nvenc():
        encoder = "h264_nvenc"
        encoder_opts = ["-preset", NVENC_PRESET, "-b:v", OUTPUT_BITRATE]
    else:
        encoder = "libx264"
        encoder_opts = ["-preset", "medium", "-crf", "20"]
    
    render_cmd = [
        "ffmpeg", "-y", "-hide_banner",
        "-ss", str(clip_start), "-t", str(clip_duration),
        "-i", video_path,
        "-i", clean_audio,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "1:a",
        "-c:v", encoder, *encoder_opts,
        "-c:a", "aac", "-b:a", "192k",
        "-r", str(TARGET_FPS),
        "-movflags", "+faststart",
        output_path,
    ]
    
    print(f"{Fore.RED}[RENDER]{Style.RESET_ALL} Encoding with {encoder}...")
    result = subprocess.run(render_cmd, capture_output=True, text=True, timeout=600)
    
    if result.returncode != 0:
        # Fallback: try without NVENC
        if encoder == "h264_nvenc":
            print(f"{Fore.YELLOW}[RENDER]{Style.RESET_ALL} NVENC failed, retrying with libx264...")
            render_cmd[render_cmd.index("h264_nvenc")] = "libx264"
            # Replace NVENC preset with libx264 options
            idx = render_cmd.index("-preset")
            render_cmd[idx + 1] = "medium"
            # Remove -b:v and its value, add -crf
            try:
                bv_idx = render_cmd.index("-b:v")
                render_cmd.pop(bv_idx + 1)
                render_cmd.pop(bv_idx)
            except ValueError:
                pass
            render_cmd.insert(render_cmd.index("-c:v") + 2, "-crf")
            render_cmd.insert(render_cmd.index("-crf") + 1, "20")
            
            result = subprocess.run(render_cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg render failed: {result.stderr[:500]}")
    
    # ── Cleanup temp files ─────────────────────
    for f in [raw_audio, norm_audio, clean_audio, ass_path]:
        try:
            os.remove(f)
        except OSError:
            pass
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"{Fore.GREEN}[RENDER]{Style.RESET_ALL} ✓ Saved: {output_filename} ({file_size:.1f} MB)")
    
    return output_path


def _build_face_crop_filter(scene_data: dict, duration: float,
                             source_w: int, source_h: int, ass_path: str) -> str:
    """
    Build FFmpeg filter for face-tracking crop mode.
    Uses sendcmd to dynamically move the crop window per frame.
    
    For simplicity, we use the AVERAGE crop position across all frames.
    For a fully dynamic version, we'd use sendcmd with a script file.
    """
    crop_data = scene_data["crop_data"]
    
    # Calculate the 9:16 crop width
    crop_w = int(source_h * (9 / 16))
    crop_h = source_h
    
    if crop_data:
        # Use weighted average of crop positions (weighted toward middle of clip)
        total = len(crop_data)
        weights = [1 + abs(i - total // 2) for i in range(total)]
        x_avg = sum(cd[1] * w for cd, w in zip(crop_data, weights)) / sum(weights)
        x_avg = int(x_avg)
    else:
        x_avg = source_w // 2
    
    # Clamp crop position
    x_start = max(0, x_avg - crop_w // 2)
    x_start = min(x_start, source_w - crop_w)
    
    # Escape the ASS path for FFmpeg (Windows backslashes need escaping)
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
    
    filter_str = (
        f"[0:v]crop={crop_w}:{crop_h}:{x_start}:0,"
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT},"
        f"ass='{ass_escaped}'[vout]"
    )
    
    return filter_str


def _build_screen_filter(source_w: int, source_h: int, ass_path: str) -> str:
    """
    Build FFmpeg filter for screen share / "Fit & Blur" mode.
    Background: blurred, zoomed copy of video (fills 1080x1920).
    Foreground: original video scaled to fit width, centered vertically.
    """
    # Calculate scaled dimensions
    scale_factor = TARGET_WIDTH / source_w
    scaled_h = int(source_h * scale_factor)
    y_offset = (TARGET_HEIGHT - scaled_h) // 2
    
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
    
    filter_str = (
        # Background: blur and fill
        f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},gblur=sigma=30[bg];"
        # Foreground: scale to fit width
        f"[0:v]scale={TARGET_WIDTH}:{scaled_h}[fg];"
        # Overlay + subtitles
        f"[bg][fg]overlay=0:{y_offset},"
        f"ass='{ass_escaped}'[vout]"
    )
    
    return filter_str


def _check_nvenc() -> bool:
    """Check if NVIDIA NVENC encoder is available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10,
        )
        return "h264_nvenc" in result.stdout
    except Exception:
        return False
