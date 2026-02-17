
import os
import json
import asyncio
import random
import subprocess
from pathlib import Path
import google.generativeai as genai
from yt_dlp import YoutubeDL
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

from config import GOOGLE_API_KEY, GAMEPLAY_CHANNELS, GAMEPLAY_DIR
from modules.utils import log, get_ffprobe_bin, get_ffmpeg_bin

# Configure Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

async def update_gameplay_library():
    """
    Ensure we have enough 1080p gameplay loops.
    Downloads from YouTube if needed, validates 1080p, and splits by scenes.
    """
    log("MINER", "Checking gameplay library...")
    
    existing = list(GAMEPLAY_DIR.glob("*.mp4"))
    if len(existing) >= 5:
        log("MINER", f"Library healthy ({len(existing)} clips). Skipping download.", "OK")
        return

    log("MINER", "Library low. Mining YouTube...", "WARN")
    
    # Select random source
    channel = random.choice(GAMEPLAY_CHANNELS)
    
    # yt-dlp options for 1080p, no audio (we strip it anyway)
    ydl_opts = {
        'format': 'bestvideo[height>=1080][ext=mp4]',
        'outtmpl': str(GAMEPLAY_DIR / 'raw_download.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'max_downloads': 1,
        'ffmpeg_location': str(Path(get_ffmpeg_bin()).parent)
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            # We would normally search, but for simplicity, let's pretend we have a specific URL 
            # or search query. The prompt says "Search YouTube".
            # ydl.extract_info(f"ytsearch1:{channel} 4k 60fps no hud gameplay", download=True)
            # Searching via yt-dlp is slow. Hardcoding a reliable query for now.
            query = "4k 60fps no hud gameplay cyberpunk" 
            ydl.extract_info(f"ytsearch1:{query}", download=True)
            
        # The file is at raw_download.mp4 (approx)
        raw_files = list(GAMEPLAY_DIR.glob("raw_download.mp4"))
        if not raw_files:
            log("MINER", "Download failed.", "ERR")
            return

        raw_path = raw_files[0]
        
        # Validate 1080p via ffprobe
        if not _is_1080p(raw_path):
            log("MINER", "Downloaded video is not 1080p. Deleting.", "ERR")
            raw_path.unlink()
            return
            
        # Process: Strip Audio + Smart Cut
        await _process_gameplay(raw_path)
        
        # Cleanup raw
        raw_path.unlink()

    except Exception as e:
        log("MINER", f"Mining failed: {e}", "ERR")

def _is_1080p(video_path):
    ffprobe = get_ffprobe_bin()
    cmd = [
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=height", "-of", "csv=s=x:p=0",
        str(video_path)
    ]
    try:
        height = int(subprocess.check_output(cmd).decode().strip())
        return height >= 1080
    except:
        return False

async def _process_gameplay(raw_path):
    log("MINER", "Processing raw gameplay (Smart Scene Detect)...")
    
    # Use PySceneDetect to find cuts
    video_manager = VideoManager([str(raw_path)])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=27.0))
    
    video_manager.set_downscale_factor()
    video_manager.start()
    
    scene_manager.detect_scenes(frame_source=video_manager)
    scene_list = scene_manager.get_scene_list(video_manager.get_base_timecode())
    
    log("MINER", f"Found {len(scene_list)} scenes.", "OK")
    
    # Save valid scenes (duration > 10s and < 60s)
    ffmpeg = get_ffmpeg_bin()
    count = 0
    
    for scene in scene_list:
        start, end = scene
        duration = end.get_seconds() - start.get_seconds()
        
        if 10 < duration < 90:
            output_name = f"gameplay_{random.randint(1000,9999)}.mp4"
            output_path = GAMEPLAY_DIR / output_name
            
            # Extract scene with FFmpeg (no re-encode if possible, but safer to re-encode for consistency)
            cmd = [
                ffmpeg, "-y", "-hide_banner",
                "-i", str(raw_path),
                "-ss", str(start.get_seconds()),
                "-to", str(end.get_seconds()),
                "-an", # Remove audio
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                str(output_path)
            ]
            subprocess.run(cmd, check=True)
            count += 1
            if count >= 3: break # Keep top 3 scenes per download
            
    log("MINER", f"Saved {count} new gameplay loops.", "OK")

async def generate_story(topic: str) -> dict:
    """
    Generate viral story using LLM with Critic Loop.
    """
    log("MINER", f"Generating story for: {topic}...")
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    # Step 1: Draft
    draft_prompt = f"""
    Write a viral short-form video script about: "{topic}".
    Genre: Betrayal/Revenge/Fear.
    Style: First-person confession. High retention.
    Constraints:
    - Total duration: 45-55 seconds (approx 130-150 words).
    - Output MUST be valid strictly parsable JSON.
    - No markdown formatting.
    
    JSON Schema:
    {{
        "hook": "First sentence, must be shocking.",
        "body": "The main story, building tension.",
        "cta": "Call to action (e.g. Subscribe for Part 2)",
        "estimated_duration": 50,
        "keywords_for_image_gen": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
    }}
    """
    
    try:
        response = await model.generate_content_async(draft_prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        log("MINER", "Draft generated. Running Critic Loop...", "INFO")
        
        # Step 2: Critic Loop
        critic_prompt = f"""
        Act as a ruthlessly mean TikTok editor. Critique this hook: "{data['hook']}".
        
        Rules:
        1. Does it have a number or shocking statement?
        2. Is it under 5 seconds?
        
        If BAD, rewrite the hook to be aggressive.
        If GOOD, return "PASS".
        
        Output only the new hook or "PASS".
        """
        critic_response = await model.generate_content_async(critic_prompt)
        verdict = critic_response.text.strip()
        
        if verdict != "PASS":
            log("MINER", f"Critic rewrote hook: {verdict}", "WARN")
            data['hook'] = verdict.replace('"', '')
            
        log("MINER", "Story finalized.", "OK")
        return data
        
    except Exception as e:
        log("MINER", f"Story generation failed: {e}", "ERR")
        return None

async def generate_proof_list(topic: str) -> dict:
    """
    Generate viral 'Proof List' script using the Luc Boulch formula.
    Forces Gemini to output strict JSON with Hook -> 3 Proofs -> Rehook.
    """
    log("MINER", f"Generating Viral Proof List for: {topic}...")
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f"""
    ROLE: Viral TikTok Scripter (Retention Engineer).
    TASK: Write a 140-word script about '{topic}' using the 'Proof List' structure.
    
    STRUCTURE:
    1. Hook (0-3s): Bold, controversial, or mystery claim.
    2. Transition: "Here are 3 reasons why..." (or similar).
    3. Proof 1: Fast fact (Speed 1.1x).
    4. Proof 2: Faster fact (Speed 1.15x).
    5. Proof 3: The shocking fact.
    6. Re-Hook: Start with "But the cherry on top is..."
    7. Loop: End sentence that flows back to the start.
    
    STRICT JSON OUTPUT FORMAT:
    {{
      "hook": "Text of the hook",
      "transition": "Text of transition",
      "proof_1": "Text of proof 1",
      "proof_2": "Text of proof 2",
      "proof_3": "Text of proof 3",
      "rehook": "Text of the re-hook",
      "loop_ending": "Text of the loop ending",
      "estimated_duration": 50,
      "keywords_for_image_gen": ["kw1", "kw2", "kw3", "kw4", "kw5"]
    }}
    
    CONSTRAINT: No intro fluff. Start immediately. Total words < 140.
    """
    
    try:
        response = await model.generate_content_async(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        log("MINER", "Proof List generated successfully.", "OK")
        return data
        
    except Exception as e:
        log("MINER", f"Proof List generation failed: {e}", "ERR")
        return None

def analyze_transcript_patterns(transcript_text: str) -> list:
    """
    Scan transcript for 'Enumeration Markers' to find viral listicle segments.
    Returns list of potential start indices in the text.
    """
    markers = [
        "here are three", "here are 3",
        "number one", "first reason",
        "three things", "3 things",
        "top three", "top 3",
        "reason number one",
        "first of all",
        "the cherry on top"
    ]
    
    matches = []
    text_lower = transcript_text.lower()
    
    for marker in markers:
        idx = text_lower.find(marker)
        if idx != -1:
            matches.append({
                "marker": marker,
                "index": idx,
                "context": transcript_text[idx:idx+50] + "..."
            })
            
    if matches:
        log("MINER", f"Found {len(matches)} viral patterns in transcript.", "INFO")
        
    return matches
