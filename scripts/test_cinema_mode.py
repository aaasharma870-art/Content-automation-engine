import requests
import json
import time
import sys

# Ensure requests is installed or handle error? 
# Assuming user environment has requests (very common). 
# If not, I'd need to install it, but I can't easily pip install in user env without asking.
# I'll assume it's there or use urllib if needed. 
# actually user might not have requests installed in the windows environment where I run python?
# I'll use standard library urllib to be safe.

import urllib.request
import urllib.error

def post_json(url, data):
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        print(e.read().decode('utf-8'))
        raise
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
        raise

JOB_ID = "test-cinema-" + str(int(time.time()))
BRAND_ID = "test-brand"

print(f"1. Calling AI Pipeline for Job {JOB_ID}...")
ai_url = "http://localhost:8000/api/v1/pipeline/produce"
ai_payload = {
    "job_id": JOB_ID,
    "brand_id": BRAND_ID,
    "mood": "cinematic_emotional",
    "topic": "perseverance",
    "include_corpus": True,
    "target_duration_sec": 30
}

try:
    data = post_json(ai_url, ai_payload)
    print("   AI Success!")
except Exception as e:
    print(f"   AI Failed: {e}")
    sys.exit(1)

payload = data['payload']
print("\n2. Constructing Render Request...")

render_req = {
    "job_id": JOB_ID,
    "brand_id": BRAND_ID,
    "script": {
        "hook": "Cinema Mode Test",
        "body": payload['caption'],
        "cta": "Follow for more"
    },
    "art_urls": [], # No art provided by pipeline?
    "audio_url": payload.get('audio_url') or "", 
    "brand_profile": {
        "palette": ["#000000", "#FFFFFF"],
        "font_family": "Montserrat",
        "motion_profile": "smooth"
    },
    "platform": "instagram",
    "target_duration_seconds": payload['target_duration_seconds'],
    "visual_family": payload['visual_family'],
    "text_lines": payload['text_lines'],
    "music_url": payload.get('music_url'),
    "attribution": payload.get('attribution'),
    "color_grade": payload.get('color_grade'),
    "zoom_style": payload.get('zoom_style'),
    "pacing": payload.get('pacing'),
    "text_animation": payload.get('text_animation'),
    "music_volume": payload.get('music_volume')
}

print(f"3. Calling Renderer for Job {JOB_ID}...")
render_url = "http://localhost:8001/api/v1/render"

try:
    r_data = post_json(render_url, render_req)
    print(f"   Render Success! Video URL: {r_data.get('video_url')}")
except Exception as e:
    print(f"   Render Failed: {e}")
    sys.exit(1)
