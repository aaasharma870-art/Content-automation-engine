
import os
import math
import subprocess
from pathlib import Path
from src.modules.utils import log, get_ffmpeg_bin
from config import USE_NVENC, TARGET_WIDTH, TARGET_HEIGHT, FFMPEG_THREADS, OUTPUT_DIR

def _escape_path(path: str) -> str:
    """Escape file path for use in FFmpeg filter expressions (Windows backslashes + colons)."""
    return str(path).replace("\\", "/").replace(":", "\\:")

VIDEO_ENCODER = "h264_nvenc" if USE_NVENC else "libx264"

def build_video(mode: str, assets: dict) -> str:
    """
    Render final video based on mode.
    assets = {
        'audio': path, 
        'words': list, 
        'images': [paths], 
        'gameplay': path,
        'topic': str
    }
    """
    log("RENDER", f"Rendering video in {mode} mode...")
    
    # 1. Generate Subtitles (.ass)
    ass_path = str(Path(assets['audio']).with_suffix(".ass"))
    _generate_ass(assets['words'], ass_path)
    
    # 2. Build Filter Complex
    filter_complex = ""
    inputs = []
    
    # Input 0: Audio (Already mixed)
    inputs.append("-i")
    inputs.append(assets['audio'])
    
    # Mode Logic
    if mode == "HYBRID":
        # Input 1: Images (Pattern: glob or list?)
        # For simplicity, let's assume we create a slideshow video first or use complex filter
        # It's better to create a slideshow input from images
        slideshow_path = _create_slideshow(assets['images'], _get_duration(assets['audio']))
        inputs.append("-i")
        inputs.append(slideshow_path)
        
        # Input 2: Gameplay
        inputs.append("-i")
        inputs.append(assets['gameplay'])
        
        # Split Screen Filter
        # Top: Slideshow (Crop 1080x960)
        # Bottom: Gameplay (Crop 1080x960 + Darken)
        filter_complex = (
            "[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,setsar=1[top];"
            "[2:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,setsar=1,eq=brightness=-0.3[bottom];"
            "[top][bottom]vstack[base];"
            f"[base]ass={_escape_path(ass_path)}[outv]"
        )
        
    elif mode == "VISUAL":
        # Full screen slideshow
        slideshow_path = _create_slideshow(assets['images'], _get_duration(assets['audio']))
        inputs.append("-i")
        inputs.append(slideshow_path)
        
        filter_complex = f"[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass={_escape_path(ass_path)}[outv]"
        
    elif mode == "GAMEPLAY":
        # Full screen gameplay
        inputs.append("-i")
        inputs.append(assets['gameplay'])
        
        filter_complex = f"[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass={_escape_path(ass_path)}[outv]"
    
    # Output file
    output_filename = f"{assets['topic'].replace(' ', '_')}_{mode}.mp4"
    output_path = OUTPUT_DIR / output_filename
    
    cmd = [
        get_ffmpeg_bin(), "-y", "-hide_banner",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a",
        "-c:v", VIDEO_ENCODER,
        "-b:v", "5M", # Target high bitrate
        "-c:a", "aac", "-b:a", "192k",
        "-threads", str(FFMPEG_THREADS),
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True)
    log("RENDER", f"Video saved to: {output_path}", "OK")
    return str(output_path)

def _create_slideshow(images: list, duration: float) -> str:
    """
    Create a video sequence from images (Ken Burns) or video clips (SVD).
    Supported inputs: .png (Image) or .mp4 (Video Loop).
    """
    if not images: return None
    
    is_video_input = str(images[0]).endswith(".mp4")
    
    # CASE A: Video Loops (SVD) or Repurposed Clips
    if is_video_input:
        # Create complex filter graph to apply Flash Cuts per clip
        inputs = []
        filter_parts = []
        
        for i, vid in enumerate(images):
            inputs.extend(["-i", str(vid)])
            # Apply randomized Flash Cut
            # Duration must be known? Flash cut logic uses 'time' so it's consistent.
            # We assume clip is ~4s.
            filter_parts.append(_create_flash_cut_filter(f"{i}:v", duration=4.0) + f"[v{i}];")
            
        # Concat all [vN] streams
        concat_str = "".join([f"[v{i}]" for i in range(len(images))])
        filter_str = "".join(filter_parts) + f"{concat_str}concat=n={len(images)}:v=1:a=0[outv]"
        
        output_path = str(OUTPUT_DIR / "temp_slideshow.mp4")
        
        cmd = [
            get_ffmpeg_bin(), "-y", "-hide_banner",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-c:v", VIDEO_ENCODER,
            "-preset", "fast",
            output_path
        ]
        subprocess.run(cmd, check=True)
        return output_path

    # CASE B: Static Images (Ken Burns + Crossfade)
    num_images = len(images)
    transition_dur = 0.5
    # Account for transition overlap in per-image duration
    img_dur = (duration + transition_dur * (num_images - 1)) / num_images
    img_dur = max(img_dur, 1.5)  # Minimum 1.5s per image

    fps = 30
    inputs = []
    filter_parts = []

    # Ken Burns effect variants for visual variety
    kb_variants = [
        # (zoom_expr, x_expr, y_expr) — different motion patterns
        ("min(zoom+0.0015,1.2)", "(iw-ow)/2", "(ih-oh)/2"),           # Zoom in center
        ("if(eq(on,1),1.2,max(zoom-0.0015,1))", "(iw-ow)/2", "(ih-oh)/2"),  # Zoom out center
        ("min(zoom+0.001,1.15)", "0", "(ih-oh)/2"),                     # Zoom in from left
        ("min(zoom+0.001,1.15)", "iw-ow", "(ih-oh)/2"),                # Zoom in from right
        ("if(eq(on,1),1.15,max(zoom-0.001,1))", "(iw-ow)/2", "0"),    # Zoom out from top
    ]

    for i, img_path in enumerate(images):
        frame_count = int((img_dur + transition_dur) * fps)
        inputs.extend(["-loop", "1", "-t", str(img_dur + transition_dur), "-i", str(img_path)])

        # Cycle through Ken Burns variants for visual variety
        z_expr, x_expr, y_expr = kb_variants[i % len(kb_variants)]

        filter_parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frame_count}:s=1080x1920:fps={fps},"
            f"setpts=PTS-STARTPTS,format=yuv420p[v{i}];"
        )

    # Build crossfade chain: v0 xfade v1 -> xf0, xf0 xfade v2 -> xf1, ...
    if num_images == 1:
        filter_str = "".join(filter_parts).rstrip(";")
        filter_str = filter_str.replace(f"[v0]", "[outv]")
    elif num_images == 2:
        filter_str = "".join(filter_parts)
        offset = round(img_dur - transition_dur, 3)
        filter_str += f"[v0][v1]xfade=transition=fade:duration={transition_dur}:offset={offset}[outv]"
    else:
        filter_str = "".join(filter_parts)
        # Chain xfade for N images
        prev_label = "[v0]"
        for i in range(1, num_images):
            offset = round(img_dur * i - transition_dur * i, 3)
            offset = max(0.1, offset)
            out_label = "[outv]" if i == num_images - 1 else f"[xf{i}]"
            filter_str += f"{prev_label}[v{i}]xfade=transition=fade:duration={transition_dur}:offset={offset}{out_label};"
            prev_label = f"[xf{i}]"
        # Remove trailing semicolon
        filter_str = filter_str.rstrip(";")

    output_path = str(OUTPUT_DIR / "temp_slideshow.mp4")

    cmd = [
        get_ffmpeg_bin(), "-y", "-hide_banner",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[outv]",
        "-c:v", VIDEO_ENCODER,
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    subprocess.run(cmd, check=True)
    return output_path

def _create_flash_cut_filter(stream_label, duration=4.0):
    """
    Generate 3-stage Flash Cut filter implementing the Luc Boulch viral formula.

    The 3-Shot Rule: Every 4-second clip is divided into 3 distinct visual shots:
    - Shot 1 (0-1.3s): Wide — centered, establishes context
    - Shot 2 (1.3-2.6s): Zoom 150% — crop from top-left to simulate zoom-in
    - Shot 3 (2.6-4.0s): Pan Left at Zoom 120% — animated pan from right to left

    Syncs with micro-SFX at 1.4s and 2.8s for maximum engagement.
    Uses FFmpeg's conditional expressions: if(lt(t, threshold), value_if_true, value_if_false)
    """

    # Scale video to 1.5x the target size for crop headroom
    sw = int(1080 * 1.5)  # 1620 (scaled width)
    sh = int(1920 * 1.5)  # 2880 (scaled height)
    tw = 1080  # Target width
    th = 1920  # Target height

    # ── Shot 1 (0-1.3s): Wide — Centered Crop ──
    # Establishes full context, calm before the storm
    x_wide = (sw - tw) // 2  # Center horizontally: 270
    y_wide = (sh - th) // 2  # Center vertically: 480

    # ── Shot 2 (1.3-2.6s): Zoom 150% — Top-Left Crop ──
    # Simulates zoom-in by cropping from a different offset
    x_zoom = 0  # Crop from left edge
    y_zoom = 0  # Crop from top edge

    # ── Shot 3 (2.6-4.0s): Pan Left at Zoom 120% — Animated Drift ──
    # Pan from right edge to left edge over 1.4 seconds
    x_pan_start = sw - tw  # Start at right edge: 540
    x_pan_end = 0          # End at left edge: 0
    y_pan = (sh - th) // 2  # Center vertically: 480

    # Build conditional expressions using FFmpeg's 'if(condition, then, else)' syntax
    # Structure: if(t < 1.3, shot1_value, if(t < 2.6, shot2_value, shot3_value))

    # X-axis: Wide center -> Zoom left -> Pan left (right to left drift)
    x_expr = f"if(lt(t,1.3),{x_wide},if(lt(t,2.6),{x_zoom},{x_pan_start}-((t-2.6)/1.4)*{x_pan_start}))"

    # Y-axis: Wide center -> Zoom top -> Pan center
    y_expr = f"if(lt(t,1.3),{y_wide},if(lt(t,2.6),{y_zoom},{y_pan}))"

    return (
        f"[{stream_label}]scale={sw}:{sh}:force_original_aspect_ratio=disable,"
        f"crop={tw}:{th}:{x_expr}:{y_expr},"
        f"setsar=1,format=yuv420p"
    )

def _get_duration(file_path):
    """Get media duration in seconds using ffprobe (or ffmpeg fallback)."""
    try:
        from src.modules.utils import get_ffprobe_bin
        ffprobe = get_ffprobe_bin()
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass

    # Fallback: parse from ffmpeg stderr
    import re
    cmd = [get_ffmpeg_bin(), "-i", str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", result.stderr)
    if match:
        h, m, s = map(float, match.groups())
        return h * 3600 + m * 60 + s
    return 30.0

def _generate_ass(words, output_path):
    """
    Generate Hormozi-style .ass subtitles with Pop + Emphasis effects.

    Features:
    - Word-by-word display (1 word at a time for maximum retention)
    - Pop scale animation on each word appearance
    - High-contrast white text with black outline (mobile-optimized)
    - Safe zone placement (centered vertically in the middle 50%)
    """
    header = """[Script Info]
Title: AutoShorts Omni
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat ExtraBold,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,5,40,40,450,1
Style: Emphasis,Montserrat ExtraBold,80,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,5,40,40,450,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    # Emphasis words that get special treatment (color + larger scale)
    emphasis_triggers = {
        "never", "always", "secret", "money", "million", "billion",
        "dead", "kill", "rich", "free", "now", "stop", "why",
        "truth", "lie", "dark", "fear", "power", "hack", "best",
    }

    for w in words:
        start_t = _sec_to_ass(w['start'])
        end_t = _sec_to_ass(w['end'])
        text = w['word']
        clean_word = text.strip().lower().rstrip(".,!?;:")

        is_emphasis = clean_word in emphasis_triggers

        if is_emphasis:
            # Emphasis word: yellow color, larger pop, slight bounce
            pop_fx = (
                r"{\c&H00FFFF&"
                r"\t(0,120,\fscx120\fscy120)"
                r"\t(120,250,\fscx105\fscy105)"
                r"\t(250,350,\fscx110\fscy110)}"
            )
            events.append(f"Dialogue: 0,{start_t},{end_t},Emphasis,,0,0,0,,{pop_fx}{text}")
        else:
            # Standard word: white, clean pop
            pop_fx = r"{\t(0,120,\fscx112\fscy112)\t(120,250,\fscx100\fscy100)}"
            events.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{pop_fx}{text}")
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

def _sec_to_ass(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"
