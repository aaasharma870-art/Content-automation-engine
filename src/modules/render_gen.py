
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

    # CASE B: Static Images (Ken Burns)
    # Calculate duration per image
    img_dur = duration / len(images)
    transition_dur = 0.5
    
    # Create input args
    inputs = []
    filter_parts = []
    
    for i, img_path in enumerate(images):
        inputs.extend(["-loop", "1", "-t", str(img_dur + transition_dur), "-i", str(img_path)])
        
        # Ken Burns Zoom: zoom in (1 -> 1.2) or out (1.2 -> 1) alternating
        z_expr = f"min(zoom+0.0015,1.2)" if i % 2 == 0 else f"max(1.2-0.0015*on,1)"
        x_expr = "(iw-ow)/2"
        y_expr = "(ih-oh)/2"
        
        filter_parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={int((img_dur+transition_dur)*30)}:s=1080x1920,"
            f"format=yuv420p[v{i}];"
        )
        
    # Concat with crossfade
    concat_filter = ""
    for i in range(len(images)):
        if i == 0:
            concat_filter += f"[v{i}]"
        else:
            # Xfade logic is complex for N inputs. 
            # Simplified: Just concat without crossfade for v1
            # Or use 'xfade' filter chain
            pass
            
    # Simplified Slideshow (No complex xfade for MVP, just ZoomPan + Concat)
    # Re-building simple concat
    filter_str = "".join(filter_parts)
    concat_str = "".join([f"[v{i}]" for i in range(len(images))])
    filter_str += f"{concat_str}concat=n={len(images)}:v=1:a=0[outv]"
    
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
    cmd = [get_ffmpeg_bin(), "-i", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parse duration from stderr
    import re
    match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", result.stderr)
    if match:
        h, m, s = map(float, match.groups())
        return h * 3600 + m * 60 + s
    return 30.0

def _generate_ass(words, output_path):
    """
    Generate Hormozi-style .ass subtitles with Pop effect.
    """
    header = """[Script Info]
Title: AutoShorts Omni
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat ExtraBold,65,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,500,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    
    # We want word-by-word with POP effect
    # Logic: For every word, create an event
    for w in words:
        start_t = _sec_to_ass(w['start'])
        end_t = _sec_to_ass(w['end'])
        text = w['word']
        
        # Pop Effect: Scale UP to 115% (0-150ms), Scale DOWN to 100% (150-300ms)
        pop_fx = r"{\t(0,150,\fscx115\fscy115)\t(150,300,\fscx100\fscy100)}"
        
        # We need to render this word ONLY (Karaoke) or sentence?
        # The user requested specific Pop.
        # Standard approach: Show 3 words, highlight active one.
        # But Pop usually implies showing just 1 word at a time for fast pacing.
        # We will do: 1 word at a time for maximum retention.
        
        events.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{pop_fx}{text}")
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

def _sec_to_ass(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"
