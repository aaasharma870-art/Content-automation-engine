
import sys
import asyncio
from pathlib import Path
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from config import LLM_PROVIDER, OPENAI_API_KEY, GOOGLE_API_KEY

def print_banner():
    print(Fore.CYAN + Style.BRIGHT + """
    ╔══════════════════════════════════════════════════════╗
    ║             AUTOSHORTS UNIFIED LAUNCHER             ║
    ║             v2.0 (Visual Polish Build)              ║
    ╚══════════════════════════════════════════════════════╝
    """ + Style.RESET_ALL)

def check_config():
    """Verify API keys before starting."""
    errors = []
    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        errors.append("Missing OPENAI_API_KEY in .env")
    elif LLM_PROVIDER == "gemini" and not GOOGLE_API_KEY:
        errors.append("Missing GOOGLE_API_KEY in .env")
        
    if errors:
        print(Fore.RED + "\nConfiguration Errors:")
        for e in errors:
            print(f"  ❌ {e}")
        print(Style.RESET_ALL)
        sys.exit(1)

async def main():
    print_banner()
    check_config()
    
    while True:
        print("\nSelect Mode:")
        print(f"{Fore.YELLOW}[1]{Style.RESET_ALL} Repurpose Video (URL -> Viral Shorts)")
        print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Generate New (Topic -> AI Story)")
        print(f"{Fore.RED}[q]{Style.RESET_ALL} Quit")
        
        choice = input("\n> ").strip().lower()
        
        if choice == 'q':
            print("Exiting...")
            break
            
        elif choice == '1':
            from pipelines import repurpose
            print(f"\n{Fore.CYAN}--- Mode 1: YT Clipper ---{Style.RESET_ALL}")
            url = input("Enter YouTube URL (leave blank to check queue.txt): ").strip()
            if url:
                await repurpose.run_pipeline(url)
            else:
                # Run queue processing
                await repurpose.run_pipeline()
                
        elif choice == '2':
            from pipelines import generate
            print(f"\n{Fore.CYAN}--- Mode 2: Story Generator ---{Style.RESET_ALL}")
            # The generate pipeline asks for topic internally if None passed
            await generate.run_pipeline()
            
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
