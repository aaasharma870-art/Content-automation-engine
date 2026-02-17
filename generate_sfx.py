
from pydub import AudioSegment
from pydub.generators import WhiteNoise
import os

# Create directory
os.makedirs("assets/sfx/transitions", exist_ok=True)

# Generate a 0.5s "Whoosh" (White Noise with fade)
whoosh = WhiteNoise().to_audio_segment(duration=500, volume=-20.0)
whoosh = whoosh.fade_in(100).fade_out(300)

output_path = "assets/sfx/transitions/soft_whoosh.wav"
whoosh.export(output_path, format="wav")
print(f"Created placeholder SFX: {output_path}")
