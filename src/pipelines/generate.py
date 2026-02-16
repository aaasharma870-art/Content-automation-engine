
import asyncio
import shutil
import os
from config import TEMP_DIR, DEFAULT_MODE, ASSETS_DIR
from modules import miner, vision, audio, render_gen as render, validator
from modules.utils import log

async def run_pipeline(topic: str = None):
    """
    Executes the Generative AI Pipeline (AutoShorts Omni).
    """
    if not topic:
        topic = input("Enter Topic for Generation > ")

    log("ORCHESTRATOR", f"Starting generation for: {topic}", "INFO")

    try:
        # 1. Miner
        story_data = await miner.generate_story(topic)
        if not story_data: 
            return

        await miner.update_gameplay_library()
        gameplay_files = list(miner.GAMEPLAY_DIR.glob("*.mp4"))
        if not gameplay_files:
            log("ORCHESTRATOR", "No gameplay found!", "ERR")
            return
        gameplay = str(gameplay_files[0]) # Pick first for now

        # 2. Parallel Generation
        story_text = f"{story_data['hook']} {story_data['body']} {story_data['cta']}"
        
        # Audio (Voice)
        voice_path = TEMP_DIR / "narration.mp3"
        await audio.generate_narration(story_text, output_path=str(voice_path))
        
        # Subtitles (Sync) -> Get duration from this
        words = audio.generate_subtitles(str(voice_path))
        voice_duration = words[-1]['end'] if words else 30.0
        
        # Audio (Mix with Music + SFX)
        final_audio_path = TEMP_DIR / "final_mix.mp3"
        
        # Pick Random Music
        music_files = list((ASSETS_DIR / "music").glob("*.mp3"))
        music_path = str(music_files[0]) if music_files else None
        
        if music_path:
            # Calculate Scene Changes for SFX
            # We have N scenes. Duration is voice_duration.
            # Assuming equal distribution for now (naive but working)
            num_scenes = len(story_data.get('keywords_for_image_gen', []))
            scene_duration = voice_duration / max(1, num_scenes)
            scene_timestamps = [i * scene_duration for i in range(1, num_scenes)] # skip 0.0
            
            audio.duck_audio(
                voice_path=str(voice_path),
                music_path=music_path,
                output_path=str(final_audio_path),
                duration=voice_duration,
                scene_changes=scene_timestamps
            )
        else:
            final_audio_path = voice_path # Fallback if no music
        
        # Vision (Parallel)
        images = await vision.generate_scenes(story_data)
        
        # 3. Validation
        assets = {
            'topic': topic,
            'audio': str(final_audio_path),
            'words': words,
            'images': images,
            'gameplay': gameplay
        }
        
        # Simple validation for now
        # if not validator.validate_assets(assets):
        #     log("ORCHESTRATOR", "Validation Failed.", "ERR")
        #     return
            
        # 4. Render
        output = render.build_video(DEFAULT_MODE, assets)
        log("ORCHESTRATOR", f" Pipeline Complete! Video: {output}", "OK")

    except Exception as e:
        log("ORCHESTRATOR", f"Pipeline failed: {e}", "ERR")
        import traceback
        traceback.print_exc()
