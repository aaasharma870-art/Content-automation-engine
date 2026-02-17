
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pipelines import repurpose

async def main():
    url = "https://www.youtube.com/watch?v=An306Mqzb7E"
    print(f"Triggering repurpose pipeline for: {url}")
    await repurpose.run_pipeline(url)

if __name__ == "__main__":
    asyncio.run(main())
