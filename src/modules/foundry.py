
import os
import torch
import gc
from diffusers import StableVideoDiffusionPipeline, AutoPipelineForText2Image
from diffusers.utils import export_to_video
from config import USE_LOCAL_GENERATION, GPU_VRAM_LIMIT, TEMP_DIR
from src.modules.utils import log

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

class LocalFoundry:
    def __init__(self):
        self.img_pipe = None
        self.vid_pipe = None
        
    def load_img_model(self):
        if not self.img_pipe:
            log("FOUNDRY", "Loading SDXL Turbo (Image Model)...")
            self.img_pipe = AutoPipelineForText2Image.from_pretrained(
                "stabilityai/sdxl-turbo", torch_dtype=DTYPE, variant="fp16"
            ).to(DEVICE)

    def load_vid_model(self):
        if not self.vid_pipe:
            log("FOUNDRY", "Loading SVD-XT (Video Model)...")
            self.vid_pipe = StableVideoDiffusionPipeline.from_pretrained(
                "stabilityai/stable-video-diffusion-img2vid-xt", torch_dtype=DTYPE, variant="fp16"
            ).to(DEVICE)
            # Enable slicing for low VRAM
            if GPU_VRAM_LIMIT < 16:
                self.vid_pipe.enable_model_cpu_offload()

    def generate_scene(self, prompt, output_path):
        log("FOUNDRY", f"Generating scene: {prompt[:30]}...")
        
        # 1. Generate Image (Strict Serial Load)
        self.load_img_model()
        style_prompt = f"cinematic film still, 8k, highly detailed, {prompt}, dark moody lighting"
        
        image = self.img_pipe(prompt=style_prompt, num_inference_steps=1, guidance_scale=0.0).images[0]
        image = image.resize((576, 1024))
        
        # 2. FLUSH VRAM (Critical)
        del self.img_pipe
        self.img_pipe = None
        self.clear_vram()
        
        # 3. Generate Video
        self.load_vid_model()
        frames = self.vid_pipe(
            image, 
            decode_chunk_size=2, 
            generator=torch.manual_seed(42), 
            motion_bucket_id=180, # Maximized motion for 0.75s cuts
            noise_aug_strength=0.1
        ).frames[0]
        
        # 4. Save & Final Flush
        # fps=6 -> ~4.16s duration (25 frames)
        # We need >4.0s for the flash cut filter
        export_to_video(frames, output_path, fps=6) 
        log("FOUNDRY", f"Saved video: {output_path}", "OK")
        
        del self.vid_pipe
        self.vid_pipe = None
        self.clear_vram()
        
        return output_path

    def clear_vram(self):
        gc.collect()
        torch.cuda.empty_cache()

# Singleton
foundry = LocalFoundry()
