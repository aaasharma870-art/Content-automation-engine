"""
editor.py - The Polisher & Assembler
======================================
Handles all post-production:
1. Audio Engineering: LUFS normalization, silence removal, sidechain compression
2. Kinetic Typography: Hormozi-style .ass captions with emoji injection
3. B-Roll integration: Splicing semantically matched footage
4. Final Render: FFmpeg assembly with NVENC GPU acceleration
"""

import os
import re
import json
import random
import subprocess
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import (
    TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS, OUTPUT_BITRATE,
    TARGET_LUFS, SILENCE_THRESHOLD_DB, SILENCE_MIN_DURATION_MS,
    CAPTION_FONT, CAPTION_FONT_SIZE, CAPTION_PRIMARY_COLOR,
    CAPTION_HIGHLIGHT_COLOR, CAPTION_OUTLINE_COLOR,
    CAPTION_OUTLINE_WIDTH, CAPTION_SHADOW_DEPTH,
    CAPTION_MARGIN_BOTTOM, CAPTION_MAX_CHARS, CAPTION_UPPERCASE,
    SIDECHAIN_THRESHOLD, SIDECHAIN_RATIO, SIDECHAIN_ATTACK, SIDECHAIN_RELEASE,
    MUSIC_VOLUME_DB, MUSIC_DIR, PROCESSED_DIR,
    USE_NVENC, NVENC_PRESET, BROLL_OVERLAY_DURATION,
    USE_HWACCEL_CUDA, LUT_FILE, LUT_DIR, DYNAMIC_ZOOM_INTENSITY,
    SAFE_ZONE_BOTTOM,
)
from src.utils.logger import log
from src.utils.emoji_map import get_emoji_for_word
from src.utils.ffmpeg_utils import FFMPEG_BIN

# ── Safe Zone Calculation ───────────────────────
# Ensure captions are above the bottom UI layer
SAFE_MARGIN_BOTTOM = int(TARGET_HEIGHT * SAFE_ZONE_BOTTOM) + 20
if CAPTION_MARGIN_BOTTOM < SAFE_MARGIN_BOTTOM:
    CAPTION_MARGIN_BOTTOM = SAFE_MARGIN_BOTTOM


# ══════════════════════════════════════════════
# 1. AUDIO ENGINEERING
# ══════════════════════════════════════════════

def normalize_audio(input_path: str, output_path: str) -> str:
    """
    EBU R128 loudness normalization (two-pass).
    Target: -24 LUFS for voiceover (per spec for sidechain reference).
    """
    log("EDITOR", f"Normalizing audio to {TARGET_LUFS} LUFS...")

    # Pass 1: Measure loudness
    measure_cmd = [
        FFMPEG_BIN, "-i", input_path, "-hide_banner",
        "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ]
    result = subprocess.run(measure_cmd, capture_output=True, text=True, timeout=300)
    stats = _parse_loudnorm_output(result.stderr)

    if stats:
        filter_str = (
            f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:"
            f"measured_I={stats['input_i']}:"
            f"measured_LRA={stats['input_lra']}:"
            f"measured_TP={stats['input_tp']}:"
            f"measured_thresh={stats['input_thresh']}:"
            f"offset={stats['target_offset']}:"
            f"linear=true"
        )
    else:
        filter_str = f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11"

    norm_cmd = [
        FFMPEG_BIN, "-y", "-i", input_path, "-hide_banner",
        "-af", filter_str,
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    result = subprocess.run(norm_cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log("EDITOR", "Normalization failed, using original", "WARN")
        shutil.copy2(input_path, output_path)

    log("EDITOR", "Audio normalized", "OK")
    return output_path


def remove_silence(input_path: str, output_path: str) -> str:
    """Truncate silence gaps >500ms for jump-cut pacing."""
    log("EDITOR", f"Removing silence (>{SILENCE_MIN_DURATION_MS}ms)...")

    silence_dur = SILENCE_MIN_DURATION_MS / 1000.0
    cmd = [
        FFMPEG_BIN, "-y", "-i", input_path, "-hide_banner",
        "-af", (
            f"silenceremove="
            f"stop_periods=-1:"
            f"stop_duration={silence_dur}:"
            f"stop_threshold={SILENCE_THRESHOLD_DB}dB"
        ),
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log("EDITOR", "Silence removal failed, using original", "WARN")
        shutil.copy2(input_path, output_path)
    else:
        log("EDITOR", "Silence removed", "OK")

    return output_path


def select_background_music(voice_path: str = None) -> str | None:
    """
    Select background music by matching acoustic features (tempo, mood, intensity).
    Uses a cached index (music_index.json) to avoid re-analyzing music library.
    """
    music_files = []
    for ext in ["*.mp3", "*.wav", "*.m4a", "*.ogg", "*.flac"]:
        music_files.extend(MUSIC_DIR.glob(ext))

    if not music_files:
        log("EDITOR", "No music files in assets/music/", "WARN")
        return None

    if not voice_path:
        return str(random.choice(music_files))

    # ── 1. Analyze Voice Track (Reference) ──
    try:
        import librosa
        import numpy as np
        
        # Load 30s of voice
        y_voice, sr = librosa.load(voice_path, sr=22050, duration=30)
        
        # Extract Features
        # 1. Energy (RMS) - Intensity
        rms_voice = float(np.mean(librosa.feature.rms(y=y_voice)))
        # 2. Spectral Centroid - Brightness
        cent_voice = float(np.mean(librosa.feature.spectral_centroid(y=y_voice, sr=sr)))
        # 3. Spectral Contrast - Emotional tension
        # (mean of the 4th band, roughly 200-400Hz, good for voice warmth)
        contrast_voice = float(np.mean(librosa.feature.spectral_contrast(y=y_voice, sr=sr)[3]))
        # 4. Tempo (BPM) - Pacing
        onset_env = librosa.onset.onset_strength(y=y_voice, sr=sr)
        tempo_voice = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)
        tempo_voice = float(tempo_voice[0] if isinstance(tempo_voice, np.ndarray) else tempo_voice)

        log("EDITOR", f"Voice Profile: BPM={tempo_voice:.0f}, Energy={rms_voice:.3f}, Contrast={contrast_voice:.1f}")

    except Exception as e:
        log("EDITOR", f"Voice analysis failed: {e}", "WARN")
        return str(random.choice(music_files))

    # ── 2. Load/Build Music Index ──
    index_path = MUSIC_DIR / "music_index.json"
    music_index = {}
    if index_path.exists():
        try:
            with open(index_path, "r") as f:
                music_index = json.load(f)
        except Exception:
            pass

    # Update index for new files
    updated = False
    valid_files = []
    
    for mf in music_files:
        if mf.name not in music_index:
            try:
                log("EDITOR", f"Analyzing new track: {mf.name}...")
                y_m, sr_m = librosa.load(str(mf), sr=22050, duration=30)
                
                # Extract same features
                rms_m = float(np.mean(librosa.feature.rms(y=y_m)))
                cent_m = float(np.mean(librosa.feature.spectral_centroid(y=y_m, sr=sr_m)))
                contrast_m = float(np.mean(librosa.feature.spectral_contrast(y=y_m, sr=sr_m)[3]))
                onset_m = librosa.onset.onset_strength(y=y_m, sr=sr_m)
                tempo_m = librosa.beat.tempo(onset_envelope=onset_m, sr=sr_m)
                tempo_m = float(tempo_m[0] if isinstance(tempo_m, np.ndarray) else tempo_m)
                
                music_index[mf.name] = {
                    "rms": rms_m,
                    "centroid": cent_m,
                    "contrast": contrast_m,
                    "tempo": tempo_m
                }
                updated = True
            except Exception as e:
                log("EDITOR", f"Failed to analyze {mf.name}: {e}", "WARN")
                continue
        
        valid_files.append(mf)

    if updated:
        with open(index_path, "w") as f:
            json.dump(music_index, f, indent=2)

    # ── 3. Find Best Match (Weighted Euclidean Distance) ──
    best_match = None
    best_dist = float('inf')

    # Weights: Tempo (40%), Energy (30%), Contrast (30%)
    # Normalize differences roughly to 0-1 range before weighting
    
    for mf in valid_files:
        data = music_index.get(mf.name)
        if not data:
            continue
            
        # Delta features
        d_tempo = abs(data["tempo"] - tempo_voice) / 200.0  # Normalize by ~200 BPM range
        d_rms = abs(data["rms"] - rms_voice) / 0.5          # Normalize by ~0.5 RMS range
        d_contrast = abs(data["contrast"] - contrast_voice) / 30.0
        
        # Composite distance
        dist = (d_tempo * 0.4) + (d_rms * 0.3) + (d_contrast * 0.3)
        
        if dist < best_dist:
            best_dist = dist
            best_match = mf

    if best_match:
        log("EDITOR", f"Mood Match: {best_match.name} (dist={best_dist:.3f})", "OK")
        return str(best_match)
    
    return str(random.choice(music_files))


def build_sidechain_audio(voice_path: str, music_path: str, output_path: str,
                          duration: float) -> str:
    """
    Mix voice + music with sidechain compression (auto-ducking).

    The voice acts as the sidechain control: when speech is detected,
    the music volume drops automatically.

    FFmpeg filtergraph:
    - Trim music to clip duration
    - Lower music base volume
    - Apply sidechaincompress with voice as control
    - Mix compressed music with voice
    """
    log("EDITOR", "Building sidechain mix (auto-ducking)...")

    # Complex filter: voice ducks music
    filter_complex = (
        # Input 0 = voice, Input 1 = music
        # Lower music volume first
        f"[1:a]volume={MUSIC_VOLUME_DB}dB,atrim=duration={duration},asetpts=PTS-STARTPTS[music];"
        # Split voice for sidechain control
        f"[0:a]asplit=2[voice][sc];"
        # Sidechain compress: music controlled by voice
        f"[music][sc]sidechaincompress="
        f"threshold={SIDECHAIN_THRESHOLD}:"
        f"ratio={SIDECHAIN_RATIO}:"
        f"attack={SIDECHAIN_ATTACK}:"
        f"release={SIDECHAIN_RELEASE}"
        f"[ducked_music];"
        # Mix voice + ducked music
        f"[voice][ducked_music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    cmd = [
        FFMPEG_BIN, "-y", "-hide_banner",
        "-i", voice_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log("EDITOR", f"Sidechain failed: {result.stderr[:200]}", "WARN")
        log("EDITOR", "Using voice only (no music)", "WARN")
        shutil.copy2(voice_path, output_path)
    else:
        log("EDITOR", "Sidechain mix complete (music auto-ducks under speech)", "OK")

    return output_path


def _parse_loudnorm_output(stderr: str) -> dict | None:
    """Parse loudnorm JSON stats from FFmpeg stderr."""
    try:
        match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', stderr, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


# ══════════════════════════════════════════════
# 2. KINETIC TYPOGRAPHY (Hormozi Style)
# ══════════════════════════════════════════════

def generate_ass_subtitles(words: list, output_path: str) -> str:
    """
    Generate .ass subtitles with Hormozi-style karaoke animation.

    Features:
    - Montserrat Bold, uppercase
    - White base text, yellow highlight for active word
    - Heavy black outline + drop shadow
    - Emoji injection for high-impact words
    - Max 15 chars per line
    - \\kf tags for word-by-word color fill animation
    """
    log("EDITOR", f"Generating Hormozi captions ({len(words)} words)...")

    # ── ASS Header ──────────────────────────────
    header = f"""[Script Info]
Title: Sovereign AI Pipeline Captions
ScriptType: v4.00+
PlayResX: {TARGET_WIDTH}
PlayResY: {TARGET_HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{CAPTION_FONT},{CAPTION_FONT_SIZE},{CAPTION_PRIMARY_COLOR},{CAPTION_HIGHLIGHT_COLOR},{CAPTION_OUTLINE_COLOR},&H80000000,-1,0,0,0,100,100,0,0,1,{CAPTION_OUTLINE_WIDTH},{CAPTION_SHADOW_DEPTH},2,40,40,{CAPTION_MARGIN_BOTTOM},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # ── Group words into lines (max chars) ──────
    lines = _group_words_smart(words, CAPTION_MAX_CHARS)

    dialogue_lines = []
    for line_words in lines:
        if not line_words:
            continue

        line_start = line_words[0]["start"]
        line_end = line_words[-1]["end"]

        start_ts = _seconds_to_ass(line_start)
        end_ts = _seconds_to_ass(line_end)

        # Build karaoke text with \kf tags + emoji injection
        karaoke_text = ""
        for w in line_words:
            duration_cs = int((w["end"] - w["start"]) * 100)
            duration_cs = max(duration_cs, 5)

            display_word = w["word"].upper() if CAPTION_UPPERCASE else w["word"]

            # Inject emoji if matched
            emoji = get_emoji_for_word(w["word"])
            if emoji:
                display_word = f"{display_word} {emoji}"

            karaoke_text += f"{{\\kf{duration_cs}}}{display_word} "

        karaoke_text = karaoke_text.strip()
        dialogue_lines.append(
            f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{karaoke_text}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(dialogue_lines))
        f.write("\n")

    log("EDITOR", f"Subtitles saved: {Path(output_path).name}", "OK")
    return output_path


def _group_words_smart(words: list, max_chars: int) -> list:
    """
    Group words into display lines respecting max character limit.
    Uses character count instead of word count for tighter control.
    """
    lines = []
    current_line = []
    current_chars = 0

    for word in words:
        word_len = len(word["word"])
        if current_chars + word_len + 1 > max_chars and current_line:
            lines.append(current_line)
            current_line = []
            current_chars = 0

        current_line.append(word)
        current_chars += word_len + 1  # +1 for space

    if current_line:
        lines.append(current_line)

    return lines


def _seconds_to_ass(seconds: float) -> str:
    """Convert seconds to ASS timestamp: H:MM:SS.CC"""
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
    broll_insert: dict = None,
) -> str:
    """
    Assemble the final Short using FFmpeg.

    Pipeline:
    1. Trim source to clip boundaries
    2. Apply crop (face) OR letterbox+blur (screen)
    3. Optionally overlay B-roll at specified timestamp
    4. Normalize + silence-remove audio
    5. Mix with background music (sidechain compression)
    6. Burn in Hormozi-style karaoke subtitles
    7. Encode with NVENC or libx264

    Args:
        video_path: Source video path
        clip_data: Dict from brain.py (start, end, score, layout_type, etc.)
        scene_data: Dict from director.py (mode, crop_data, dimensions)
        words: Word dicts (0-based relative timestamps)
        output_filename: Output file name
        broll_insert: Optional dict with video_path, insert_time, duration

    Returns:
        Path to rendered short
    """
    clip_start = clip_data["start"]
    clip_end = clip_data["end"]
    clip_duration = clip_end - clip_start

    source_w = scene_data["source_width"]
    source_h = scene_data["source_height"]

    work_dir = Path(video_path).parent
    output_path = str(PROCESSED_DIR / output_filename)

    log("RENDER", "═" * 50, "RENDER")
    log("RENDER", f"Building: {output_filename}", "RENDER")
    log("RENDER", f"Duration: {clip_duration:.1f}s | Score: {clip_data.get('virality_score', '?')}/99")

    # ── Step 1: Extract & normalize audio ──────
    raw_audio = str(work_dir / "raw_clip_audio.m4a")
    norm_audio = str(work_dir / "norm_clip_audio.m4a")
    clean_audio = str(work_dir / "clean_clip_audio.m4a")
    final_audio = str(work_dir / "final_audio.m4a")

    extract_cmd = [
        FFMPEG_BIN, "-y", "-i", video_path, "-hide_banner",
        "-ss", str(clip_start), "-t", str(clip_duration),
        "-vn", "-c:a", "aac", "-b:a", "192k",
        raw_audio,
    ]
    subprocess.run(extract_cmd, capture_output=True, timeout=120)

    normalize_audio(raw_audio, norm_audio)
    remove_silence(norm_audio, clean_audio)

    # ── Step 2: Background music + sidechain ───
    music_path = select_background_music(clean_audio)
    if music_path:
        build_sidechain_audio(clean_audio, music_path, final_audio, clip_duration)
    else:
        shutil.copy2(clean_audio, final_audio)

    # ── Step 3: Generate subtitles ─────────────
    ass_path = str(work_dir / "captions.ass")
    generate_ass_subtitles(words, ass_path)

    # ── Step 4: Build video filter chain ───────
    if scene_data["mode"] == "face" and scene_data["crop_data"]:
        filter_complex = _build_face_crop_filter(
            scene_data, source_w, source_h, ass_path
        )
    else:
        filter_complex = _build_screen_filter(source_w, source_h, ass_path)

    # ── Step 4b: Integrate B-Roll overlay ──────
    broll_input_args = []
    if broll_insert and Path(broll_insert["video_path"]).exists():
        broll_path = broll_insert["video_path"]
        insert_t = broll_insert.get("insert_time", 10.0)
        broll_dur = broll_insert.get("duration", BROLL_OVERLAY_DURATION)

        log("RENDER", f"Splicing B-roll at t={insert_t:.1f}s for {broll_dur:.1f}s")

        broll_input_args = ["-i", broll_path]

        # Rewrite filter: insert B-roll overlay between crop/scale and subtitles
        # Remove the [vout] label from existing filter, add B-roll chain
        base_filter = filter_complex.replace("[vout]", "[vmain]")

        broll_filter = (
            f"{base_filter};"
            f"[2:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            f"setpts=PTS-STARTPTS[broll_scaled];"
            f"[vmain][broll_scaled]overlay=enable='"
            f"between(t,{insert_t},{insert_t + broll_dur})'"
            f"[vout]"
        )
        filter_complex = broll_filter
    else:
        if broll_insert:
            log("RENDER", f"B-roll file not found: {broll_insert.get('video_path', '?')}", "WARN")

    # ── Step 4c: Apply LUT color grading ──────
    if LUT_FILE:
        lut_path = LUT_DIR / LUT_FILE
        if lut_path.exists():
            lut_escaped = str(lut_path).replace("\\", "/").replace(":", "\\:")
            # Insert LUT before the [vout] label
            filter_complex = filter_complex.replace(
                "[vout]",
                f"lut3d='{lut_escaped}'[vout]"
            )
            log("RENDER", f"LUT applied: {LUT_FILE}")
        else:
            log("RENDER", f"LUT file not found: {lut_path}", "WARN")

    # ── Step 5: Build hwaccel + encode command ─
    encoder, encoder_opts = _get_encoder()
    hwaccel_args = []
    if USE_HWACCEL_CUDA and _check_nvenc():
        hwaccel_args = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        # Must use software filters, so decode back to system memory
        hwaccel_args = ["-hwaccel", "cuda"]  # Decode on GPU, filter on CPU
        log("RENDER", "CUDA hardware-accelerated decoding enabled")

    render_cmd = [
        FFMPEG_BIN, "-y", "-hide_banner",
        *hwaccel_args,
        "-ss", str(clip_start), "-t", str(clip_duration),
        "-i", video_path,
        "-i", final_audio,
        *broll_input_args,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "1:a",
        "-c:v", encoder, *encoder_opts,
        "-c:a", "aac", "-b:a", "192k",
        "-r", str(TARGET_FPS),
        "-movflags", "+faststart",
        output_path,
    ]

    log("RENDER", f"Encoding with {encoder}...")
    result = subprocess.run(render_cmd, capture_output=True, text=True, timeout=900)

    if result.returncode != 0 and encoder == "h264_nvenc":
        log("RENDER", "NVENC failed, retrying with libx264...", "WARN")
        render_cmd[render_cmd.index("h264_nvenc")] = "libx264"
        idx = render_cmd.index("-preset")
        render_cmd[idx + 1] = "medium"
        try:
            bv_idx = render_cmd.index("-b:v")
            render_cmd.pop(bv_idx + 1)
            render_cmd.pop(bv_idx)
        except ValueError:
            pass
        render_cmd.insert(render_cmd.index("-c:v") + 2, "-crf")
        render_cmd.insert(render_cmd.index("-crf") + 1, "20")
        result = subprocess.run(render_cmd, capture_output=True, text=True, timeout=900)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed: {result.stderr[:500]}")

    # ── Cleanup ────────────────────────────────
    for f in [raw_audio, norm_audio, clean_audio, final_audio, ass_path]:
        try:
            os.remove(f)
        except OSError:
            pass

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    log("RENDER", f"Saved: {output_filename} ({file_size:.1f} MB)", "OK")

    return output_path


def _build_face_crop_filter(scene_data, source_w, source_h, ass_path):
    """FFmpeg filter for DYNAMIC face-tracking crop with subtitle burn-in.

    Uses sendcmd to change crop X per-frame, simulating a real camera
    operator panning to follow the active speaker.
    """
    crop_data = scene_data["crop_data"]
    crop_w = int(source_h * (9 / 16))
    crop_h = source_h
    fps = scene_data.get("fps", 30)

    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    if not crop_data or len(crop_data) < 2:
        # Static fallback if not enough keyframes
        x = crop_data[0][1] - crop_w // 2 if crop_data else (source_w - crop_w) // 2
        x = max(0, min(x, source_w - crop_w))
        return (
            f"[0:v]crop={crop_w}:{crop_h}:{x}:0,"
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT},"
            f"ass='{ass_escaped}'[vout]"
        )

    # ── Build per-frame dynamic crop via FFmpeg expression ──
    # Sample every N frames to build a piecewise-linear expression
    # FFmpeg crop filter supports expressions with 't' (time)
    sample_step = max(1, len(crop_data) // 60)  # Max ~60 keypoints for expression
    sampled = crop_data[::sample_step]
    if sampled[-1] != crop_data[-1]:
        sampled.append(crop_data[-1])

    # Build nested if(gte(t,T), X, ...) expression
    half_crop = crop_w // 2
    expr_parts = []
    for frame_idx, center_x in sampled:
        t = round(frame_idx / fps, 3)
        x = max(0, min(center_x - half_crop, source_w - crop_w))
        expr_parts.append((t, x))

    # Build from innermost to outermost
    x_expr = str(expr_parts[0][1])  # Default: first position
    for t, x in reversed(expr_parts):
        x_expr = f"if(gte(t\,{t})\,{x}\,{x_expr})"

    # ── Dynamic zoom: Ken Burns breathing effect ──
    zoom_filter = ""
    if DYNAMIC_ZOOM_INTENSITY > 1.0:
        z = DYNAMIC_ZOOM_INTENSITY
        ow = int(TARGET_WIDTH * z)
        oh = int(TARGET_HEIGHT * z)
        dx = (ow - TARGET_WIDTH) // 2
        dy = (oh - TARGET_HEIGHT) // 2
        zoom_filter = (
            f"scale={ow}:{oh},"
            f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}:"
            f"'{dx}*(0.5+0.5*sin(t*PI/2))':"
            f"'{dy}*(0.5+0.5*sin(t*PI/3))',"
        )

    return (
        f"[0:v]crop={crop_w}:{crop_h}:'{x_expr}':0,"
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT},"
        f"{zoom_filter}"
        f"ass='{ass_escaped}'[vout]"
    )


def _build_screen_filter(source_w, source_h, ass_path):
    """FFmpeg filter for letterbox+blur with subtitle burn-in."""
    scale_factor = TARGET_WIDTH / source_w
    scaled_h = int(source_h * scale_factor)
    y_offset = (TARGET_HEIGHT - scaled_h) // 2

    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    return (
        f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},gblur=sigma=30[bg];"
        f"[0:v]scale={TARGET_WIDTH}:{scaled_h}[fg];"
        f"[bg][fg]overlay=0:{y_offset},"
        f"ass='{ass_escaped}'[vout]"
    )


def _get_encoder():
    """Determine best available encoder with social-optimized VBR."""
    if USE_NVENC and _check_nvenc():
        return "h264_nvenc", [
            "-preset", NVENC_PRESET,
            "-rc", "vbr",              # Variable Bitrate mode
            "-b:v", OUTPUT_BITRATE,     # Target VBR (25M default)
            "-maxrate", "30M",          # Cap at 30 Mbps
            "-bufsize", "60M",          # Buffer for VBR headroom
            "-profile:v", "high",       # High profile for quality
        ]
    return "libx264", [
        "-preset", "medium",
        "-crf", "18",                   # Lower CRF = higher quality
        "-maxrate", "30M",
        "-bufsize", "60M",
        "-profile:v", "high",
    ]


def _check_nvenc() -> bool:
    """Check if NVIDIA NVENC is available."""
    try:
        result = subprocess.run(
            [FFMPEG_BIN, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10,
        )
        return "h264_nvenc" in result.stdout
    except Exception:
        return False
