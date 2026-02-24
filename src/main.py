
import asyncio
import sys
import os
from pathlib import Path
from colorama import Fore, Style

# Ensure src/ and root/ are in path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(SRC_DIR))

from src.modules.utils import log, get_ffmpeg_bin


LOGO = r"""
    ___         __      Shorts
   /   | __  __/ /_____  / /
  / /| |/ / / / __/ __ \/ / 
 / ___ / /_/ / /_/ /_/ /_/  
/_/  |_\__,_/\__/\____(_)   
   Sovereign Content Factory
"""

async def main():
    print(LOGO)
    print("Welcome to AutoShorts Unified Platform.")
    
    # Check API key based on provider
    from config import LLM_PROVIDER, OPENAI_API_KEY, GOOGLE_API_KEY
    
    errors = []
    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY not set in .env file")
    elif not GOOGLE_API_KEY: # Assuming 'google' is the other provider or default
        errors.append("GOOGLE_API_KEY not set in .env file")

    if errors:
        print("\nConfiguration Errors:")
        # Only hard-fail on API key
        if "API_KEY" in str(errors):
            print(f"{Fore.YELLOW}  Please check your .env file for the correct API key.{Style.RESET_ALL}")
        sys.exit(1) # Exit if there are configuration errors

    # Inject FFmpeg
    try:
        ffmpeg_bin = get_ffmpeg_bin()
        ffmpeg_dir = str(Path(ffmpeg_bin).parent)
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
    except Exception:
        pass

    while True:
        print("\nChoose Mode:")
        print("  [1] Repurpose Video (URL -> Clips)")
        print("  [2] Generate New (Topic -> AI Video)")
        print("  [3] Reddit Story (Scrape Story -> TTS Overlay)")
        print("  [q] Quit")

        choice = input("Select > ").strip().lower()

        if choice == 'q':
            break

        if choice == '1':
            from src.pipelines import repurpose
            await repurpose.run_pipeline()

        elif choice == '2':
            from src.pipelines import generate
            await generate.run_pipeline()

        elif choice == '3':
            from src.pipelines import reddit
            print("\n" + "="*50)
            print("REDDIT STORY MODE")
            print("="*50)
            bg_path = input("Background video path (e.g., gameplay.mp4): ").strip()
            if not Path(bg_path).exists():
                print(f"{Fore.RED}ERROR: File not found: {bg_path}{Style.RESET_ALL}")
                continue
            subreddit = input("Subreddit (default: TrueOffMyChest): ").strip() or "TrueOffMyChest"
            reddit.run_reddit_pipeline(background_source=bg_path, subreddit=subreddit)

        else:
            print("Invalid choice.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
