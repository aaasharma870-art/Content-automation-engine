
import os
import json
import asyncio
import subprocess
from pathlib import Path
import edge_tts
from faster_whisper import WhisperModel

from config import DEFAULT_VOICE, VOICE_MATRIX, TARGET_LUFS, MUSIC_VOLUME_DB, SFX_DIR
from modules.utils import log, get_ffmpeg_bin
import random

DUCKING_MUSIC_VOL = MUSIC_VOLUME_DB
DUCKING_VOICE_VOL = 0.0

async def generate_narration(text: str, vibe: str = "STORY", output_path: str = None) -> str:
    """
    Generate TTS narration using Edge-TTS.
    Applies R128 normalization and Silence Removal.
    """
    log("AUDIO", f"Generating narration ({len(text)} chars)...")
    
    voice = VOICE_MATRIX.get(vibe, DEFAULT_VOICE)
    communicate = edge_tts.Communicate(text, voice)
    
    temp_mp3 = str(Path(output_path).with_suffix(".temp.mp3"))
    await communicate.save(temp_mp3)
    
    # Process: Silence Removal + Normalization
    _post_process_audio(temp_mp3, output_path)
    
    Path(temp_mp3).unlink()
    return output_path

def _post_process_audio(input_path: str, output_path: str):
    """
    FFmpeg pipeline:
    1. silenceremove (truncate gaps > 0.3s)
    2. loudnorm (EBU R128 target)
    """
    ffmpeg = get_ffmpeg_bin()
    
    # Filter: Remove silence > 0.3s (-50dB), then Normalize
    filter_chain = (
        "silenceremove=stop_periods=-1:stop_duration=0.3:stop_threshold=-50dB,"
        f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11"
    )
    
    cmd = [
        ffmpeg, "-y", "-hide_banner",
        "-i", input_path,
        "-af", filter_chain,
        "-c:a", "libmp3lame", "-q:a", "2",
        output_path
    ]
    
    subprocess.run(cmd, check=True)
    log("AUDIO", "Audio normalized & silence removed.", "OK")

def generate_subtitles(audio_path: str) -> list:
    """
    Generate word-level timestamps using Faster-Whisper.
    Returns list of dicts: {word, start, end, confidence}
    """
    log("AUDIO", "Generating subtitles (Whisper)...")
    
    # Use "tiny" or "base" for speed, "small" for accuracy. "base" is good tradeoff.
    # On GPU if available
    device = "cuda" if subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0 else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    
    try:
        model = WhisperModel("base", device=device, compute_type=compute_type)
        segments, info = model.transcribe(audio_path, word_timestamps=True)
        
        words = []
        for segment in segments:
            for word in segment.words:
                words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                    "conf": word.probability
                })
                
        log("AUDIO", f"Generated {len(words)} subtitle words.", "OK")
        return words
        
    except Exception as e:
        log("AUDIO", f"Subtitle generation failed: {e}", "ERR")
        return []

def duck_audio(voice_path: str, music_path: str, output_path: str, duration: float, scene_changes: list = None):
    """
    Mix voice + music + SFX with auto-ducking.
    scene_changes: List of timestamps to inject 'whoosh' SFX.
    """
    log("AUDIO", "Mixing audio with sidechain ducking & SFX...")
    ffmpeg = get_ffmpeg_bin()
    
    # 1. Base Inputs
    inputs = ["-i", voice_path, "-stream_loop", "-1", "-i", music_path]
    sfx_filter = ""
    sfx_inputs = 0
    
    # 2. SFX Injection
    if scene_changes and SFX_DIR.exists():
        whooshes = list((SFX_DIR / "transitions").glob("*.wav")) + list((SFX_DIR / "transitions").glob("*.mp3"))
        if whooshes:
            for i, ts in enumerate(scene_changes):
                sfx_file = random.choice(whooshes)
                inputs.extend(["-i", str(sfx_file)])
                # Delay SFX to timestamp - 200ms (J-Cut)
                # Input index for this SFX is 2 + i
                sfx_index = 2 + i
                delay = max(0, int((ts - 0.2) * 1000)) # Lead by 200ms
                sfx_filter += f"[{sfx_index}:a]adelay={delay}|{delay},volume=0.6[sfx{i}];"
                sfx_inputs += 1
    
    # 3. Mix SFX into Music (if any)
    if sfx_inputs > 0:
        sfx_merge_str = "".join([f"[sfx{i}]" for i in range(sfx_inputs)])
        sfx_filter += f"[1:a]volume={DUCKING_MUSIC_VOL}dB,atrim=duration={duration}[music_trim];" \
                      f"[music_trim]{sfx_merge_str}amix=inputs={sfx_inputs+1}:duration=first[music_mixed];"
        music_label = "[music_mixed]"
    else:
        # No SFX, just trim music
        sfx_filter += f"[1:a]volume={DUCKING_MUSIC_VOL}dB,atrim=duration={duration}[music_base];"
        music_label = "[music_base]"

    # 4. Sidechain Ducking
    filter_complex = (
        sfx_filter +
        f"[0:a]volume={DUCKING_VOICE_VOL}dB,asplit=2[voice][sc];"
        f"{music_label}[sc]sidechaincompress=threshold=0.015:ratio=4:attack=5:release=200[ducked_music];"
        f"[voice][ducked_music]amix=inputs=2:duration=first[out]"
    )
    
    cmd = [
        ffmpeg, "-y", "-hide_banner",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-t", str(duration),
        output_path
    ]
    
    subprocess.run(cmd, check=True)
