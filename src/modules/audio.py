
import os
import json
import asyncio
import subprocess
from pathlib import Path
import edge_tts
from faster_whisper import WhisperModel

from config import DEFAULT_VOICE, VOICE_MATRIX, TARGET_LUFS, MUSIC_VOLUME_DB, SFX_DIR
from src.modules.utils import log, get_ffmpeg_bin
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
    try:
        device = "cuda" if subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0 else "cpu"
    except FileNotFoundError:
        device = "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    
    try:
        # Faster-Whisper relies on 'ffmpeg' existing in the system PATH
        # We must temporarily prepend our resolved ffmpeg binary directory to the PATH
        from src.modules.utils import get_ffmpeg_bin
        import os
        ffmpeg_dir = os.path.dirname(get_ffmpeg_bin())
        original_path = os.environ.get("PATH", "")
        if ffmpeg_dir not in original_path:
            os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{original_path}"

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

# ── Viral Audio Upgrade (J-Cuts & Micro-SFX) ──

def generate_flow_audio(segments: list, output_path: str) -> dict:
    """
    Generate 'Flow Audio' using J-Cuts and Breath Removal.
    
    segments: List of text strings (Hook, Proof 1, etc.)
    Returns: {"path": str, "duration": float, "timestamps": list}
    """
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    from src.modules.utils import get_ffmpeg_bin, get_ffprobe_bin

    # Configure Pydub with local FFmpeg
    AudioSegment.converter = get_ffmpeg_bin()
    AudioSegment.ffprobe = get_ffprobe_bin()
    
    log("AUDIO", "Generating Viral Flow Audio (J-Cuts)...")
    
    combined = AudioSegment.empty()
    segment_map = []
    
    # Temp file for TTS
    temp_dir = Path(output_path).parent / "temp_tts"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    current_time_ms = 0
    
    # Async TTS wrapper (using edge-tts CLI or helper would be better, 
    # but here we reuse generate_narration logic strictly if possible, 
    # or just call edge-tts directly for speed).
    # Since generate_narration is async, we can't call it easily from sync function.
    # We will assume caller provides dicts with 'text' and 'speed' or we defaults.
    
    # We'll rely on a localized helper to run TTS synchronously for this batch
    import asyncio
    
    async def _batch_tts(segs):
        files = []
        voice = DEFAULT_VOICE
        for i, text in enumerate(segs):
            if not text: continue
            out = temp_dir / f"seg_{i}.mp3"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(out))
            files.append(str(out))
        return files
        
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    tts_files = loop.run_until_complete(_batch_tts(segments))
    
    for i, file_path in enumerate(tts_files):
        seg = AudioSegment.from_file(file_path)
        
        # 1. Aggressive Silence Removal (Start/End)
        # Scan for non-silent chunks
        ranges = detect_nonsilent(seg, min_silence_len=50, silence_thresh=-45)
        if ranges:
            start_trim = ranges[0][0]
            end_trim = ranges[-1][1]
            seg = seg[start_trim:end_trim]
            
        # 2. J-Cut Overlap (Crossfade)
        # Overlap by 200ms if not the first segment
        OVERLAP = 200 # ms
        
        if i == 0:
            combined += seg
            current_time_ms += len(seg)
        else:
            # We append WITH crossfade, which effectively pulls the track back by OVERLAP ms
            combined = combined.append(seg, crossfade=OVERLAP)
            current_time_ms += (len(seg) - OVERLAP)
        
        segment_map.append({
            "index": i,
            "text": segments[i][:20] + "...",
            "end_time": current_time_ms / 1000.0
        })
        
        # Cleanup
        os.remove(file_path)
        
    # 3. Inject Micro-SFX (Rhythm)
    final_audio = _inject_micro_sfx(combined)
    
    # Export
    final_audio.export(output_path, format="mp3")
    log("AUDIO", f"Flow Audio saved: {output_path} (Duration: {len(final_audio)/1000:.2f}s)", "OK")
    
    return {
        "path": output_path,
        "duration": len(final_audio) / 1000.0,
        "timestamps": segment_map
    }

def _inject_micro_sfx(audio_segment):
    """
    Inject soft 'whoosh' at 1.4s and 2.8s intervals of 4s blocks.
    Syncs with the Visual Flash Cuts.
    """
    from pydub import AudioSegment
    
    # Load Soft Whoosh
    # Assuming standard assets path
    sfx_path = SFX_DIR / "transitions" / "soft_whoosh.wav"
    if not sfx_path.exists():
        # Fallback search or generate silence
        log("AUDIO", "Soft Whoosh SFX not found, skipping injection.", "WARN")
        return audio_segment
        
    whoosh = AudioSegment.from_file(str(sfx_path))
    whoosh = whoosh - 20 # Reduce volume by 20dB (Micro-SFX)
    
    output = audio_segment
    duration_ms = len(audio_segment)
    
    # Logic: Every 4 seconds (approx clip length), we need hits at +1.4 and +2.8 relative to that block.
    # We iterate t from 0 to duration, step 4000ms
    
    for t in range(0, duration_ms, 4000):
        # Hit 1: +1.4s (1400ms)
        hit_1 = t + 1400
        if hit_1 < duration_ms:
            output = output.overlay(whoosh, position=hit_1)
            
        # Hit 2: +2.8s (2800ms)
        hit_2 = t + 2800
        if hit_2 < duration_ms:
            output = output.overlay(whoosh, position=hit_2)
            
    return output
