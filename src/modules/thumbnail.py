"""
thumbnail.py - AI Thumbnail Selection
========================================
Scans rendered video frames, scores them on visual aesthetics
using edge density, brightness, contrast, and face presence,
then extracts the most attractive frame as a thumbnail.

Uses OpenCV image quality heuristics (no external CNN required)
to score frames — this runs on CPU in seconds.
"""

import os
import subprocess
from pathlib import Path

import cv2
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import THUMBNAIL_FRAME_COUNT, PROCESSED_DIR
from src.utils.logger import log


def extract_best_thumbnail(video_path: str, output_path: str = None) -> str:
    """
    Scan a rendered video for the most visually appealing frame
    and save it as a JPEG thumbnail.

    Scoring heuristics:
    1. Sharpness (Laplacian variance) — sharp > blurry
    2. Brightness (mean luminance) — well-lit > dark
    3. Contrast (std luminance) — dynamic > flat
    4. Face presence bonus — faces are inherently engaging
    5. Rule of thirds — subjects near power points score higher
    6. Color vibrancy (saturation mean) — vivid > washed out

    Args:
        video_path: Path to rendered .mp4
        output_path: Optional output path (defaults to video_path.thumbnail.jpg)

    Returns:
        Path to saved thumbnail JPEG
    """
    if output_path is None:
        output_path = str(Path(video_path).with_suffix(".thumbnail.jpg"))

    log("THUMBNAIL", f"Scanning {THUMBNAIL_FRAME_COUNT} frames for best thumbnail...")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < 1:
        raise RuntimeError("Video has no frames")

    # Sample frames evenly across the video
    step = max(1, total_frames // THUMBNAIL_FRAME_COUNT)
    candidates = []

    # Load face detector (Haar cascade — lightweight, CPU-only)
    face_cascade = None
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if os.path.exists(cascade_path):
        face_cascade = cv2.CascadeClassifier(cascade_path)

    for i in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            continue

        score = _score_frame(frame, face_cascade)
        candidates.append((i, score, frame))

    cap.release()

    if not candidates:
        raise RuntimeError("No valid frames found for thumbnail")

    # Pick the frame with the highest score
    candidates.sort(key=lambda x: x[1], reverse=True)
    best_idx, best_score, best_frame = candidates[0]

    log("THUMBNAIL", f"Best frame: #{best_idx} (score: {best_score:.1f})")

    # Save as high-quality JPEG
    cv2.imwrite(output_path, best_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    file_size = os.path.getsize(output_path) / 1024
    log("THUMBNAIL", f"Thumbnail saved: {Path(output_path).name} ({file_size:.0f} KB)", "OK")

    return output_path


def _score_frame(frame: np.ndarray, face_cascade=None) -> float:
    """
    Score a single frame on visual aesthetics.

    Returns a composite score (0-100+).
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 1. Sharpness (Laplacian variance) — higher = sharper
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = min(laplacian.var() / 500.0, 1.0)  # Normalize

    # 2. Brightness (mean luminance, penalty for extremes)
    brightness = gray.mean() / 255.0
    brightness_score = 1.0 - abs(brightness - 0.45) * 2  # Peak at ~115

    # 3. Contrast (std of luminance)
    contrast = min(gray.std() / 80.0, 1.0)

    # 4. Color vibrancy (mean saturation in HSV)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    saturation = min(hsv[:, :, 1].mean() / 128.0, 1.0)

    # 5. Face presence bonus
    face_score = 0.0
    if face_cascade is not None:
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.3, minNeighbors=3, minSize=(w // 10, h // 10)
        )
        if len(faces) > 0:
            # Bonus for faces, extra if face is well-positioned
            face_score = 0.3
            for (fx, fy, fw, fh) in faces:
                face_cx = (fx + fw / 2) / w
                face_cy = (fy + fh / 2) / h
                # Rule of thirds bonus (near 1/3 or 2/3 positions)
                thirds_x = min(abs(face_cx - 0.33), abs(face_cx - 0.67), abs(face_cx - 0.5))
                thirds_y = min(abs(face_cy - 0.33), abs(face_cy - 0.67))
                if thirds_x < 0.15 and thirds_y < 0.15:
                    face_score += 0.15  # Well-composed face

    # Weighted composite
    score = (
        sharpness * 25 +
        brightness_score * 20 +
        contrast * 20 +
        saturation * 15 +
        face_score * 100 +
        # Anti-black-frame: heavily penalize very dark frames
        (0 if brightness < 0.05 else 10)
    )

    return score
