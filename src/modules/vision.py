
import os
import asyncio
import aiohttp
from pathlib import Path
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, TEMP_DIR
from modules.utils import log

client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def generate_scenes(story_data: dict) -> list:
    """
    Generate AI images for the story.
    Uses AsyncIO to generate images in parallel for speed.
    """
    log("VISION", "Generating scene images (Parallel)...")
    
    keywords = story_data.get("keywords_for_image_gen", [])
    # Enhance keywords into full prompts
    prompts = [
        f"Cinematic shot, dark moody lighting, hyperrealistic 8k, {kw}, vertical aspect ratio 9:16"
        for kw in keywords
    ]
    
    # Cap at 5 scenes
    prompts = prompts[:5]
    
    tasks = []
    for i, prompt in enumerate(prompts):
        tasks.append(_generate_single_image(prompt, i))
        
    # Run all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    # Filter None results
    valid_images = [path for path in results if path is not None]
    
    if valid_images:
        log("VISION", f"Generated {len(valid_images)} images.", "OK")
    else:
        log("VISION", "Image generation failed for all scenes.", "ERR")
        
    return valid_images

async def _generate_single_image(prompt: str, index: int) -> str | None:
    """Generate a single DALL-E 3 image."""
    try:
        if not client:
            raise ValueError("OpenAI Client not initialized")
            
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1792", # Vertical
            quality="standard",
            n=1
        )
        
        url = response.data[0].url
        
        # Download
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    filename = f"scene_{index}.png"
                    path = TEMP_DIR / filename
                    with open(path, "wb") as f:
                        f.write(image_data)
                    return str(path)
                    
    except Exception as e:
        log("VISION", f"Failed scene {index}: {e}", "WARN")
        return None
