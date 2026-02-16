"""
director.py - The Dynamic Vision Engine (Active Speaker Detection)
===================================================================
This is the "Secret Sauce" module. It handles:
1. Face detection + Active Speaker logic (lip movement variance)
2. Kalman Filter smoothing for cinematic camera panning
3. Adaptive layout: Face Mode vs Screen Mode (Fit & Blur)

Analyzes video frames using MediaPipe Face Mesh to build a smooth
crop path that follows the active speaker without jitter.
"""

import cv2
import numpy as np
import mediapipe as mp
from collections import deque
from colorama import Fore, Style

from config import (
    TARGET_WIDTH, TARGET_HEIGHT,
    FACE_SAMPLE_RATE, SMOOTHING_WINDOW,
    KALMAN_PROCESS_NOISE,
)


# ── MediaPipe Setup ────────────────────────────
mp_face_mesh = mp.solutions.face_mesh


# ── Kalman Filter for smooth camera panning ────
class CameraKalmanFilter:
    """
    1D Kalman Filter for smoothing the X-coordinate of the crop window.
    This acts like a "virtual gimbal" - the camera glides instead of jumping.
    """
    
    def __init__(self, process_noise: float = KALMAN_PROCESS_NOISE):
        # State: [position, velocity]
        self.x = np.array([0.0, 0.0])  # state vector
        self.P = np.eye(2) * 1000      # covariance (high initial uncertainty)
        self.F = np.array([[1, 1],      # state transition
                           [0, 1]])
        self.H = np.array([[1, 0]])      # observation model
        self.R = np.array([[5.0]])       # measurement noise
        self.Q = np.eye(2) * process_noise  # process noise
    
    def update(self, measurement: float) -> float:
        """Feed a new face-center X measurement; returns smoothed X."""
        # Predict
        x_pred = self.F @ self.x
        P_pred = self.F @ self.P @ self.F.T + self.Q
        
        # Update
        y = measurement - self.H @ x_pred
        S = self.H @ P_pred @ self.H.T + self.R
        K = P_pred @ self.H.T @ np.linalg.inv(S)
        
        self.x = x_pred + K.flatten() * y.flatten()[0]
        self.P = (np.eye(2) - K @ self.H) @ P_pred
        
        return float(self.x[0])


class ActiveSpeakerDetector:
    """
    Detects which face is the "Active Speaker" by measuring lip movement.
    Uses MediaPipe Face Mesh landmarks for upper/lower lip distance variance.
    """
    
    # MediaPipe Face Mesh landmark indices for lips
    UPPER_LIP = 13    # Top center of upper lip
    LOWER_LIP = 14    # Bottom center of lower lip
    
    def __init__(self, history_window: int = 15):
        self.lip_history = {}  # face_id -> deque of lip distances
        self.history_window = history_window
    
    def get_lip_openness(self, face_landmarks, frame_h: int) -> float:
        """Calculate normalized lip opening distance."""
        upper = face_landmarks.landmark[self.UPPER_LIP]
        lower = face_landmarks.landmark[self.LOWER_LIP]
        distance = abs(lower.y - upper.y) * frame_h
        return distance
    
    def update_and_pick(self, faces_data: list) -> dict | None:
        """
        Given a list of detected faces, determine who is speaking.
        
        Args:
            faces_data: List of dicts with 'id', 'center_x', 'lip_openness', 'bbox_area'
            
        Returns:
            The face dict of the most likely active speaker, or None
        """
        if not faces_data:
            return None
        
        if len(faces_data) == 1:
            return faces_data[0]
        
        # Update lip movement history for each face
        for face in faces_data:
            fid = face["id"]
            if fid not in self.lip_history:
                self.lip_history[fid] = deque(maxlen=self.history_window)
            self.lip_history[fid].append(face["lip_openness"])
        
        # The "Active Speaker" has the highest lip movement VARIANCE
        # (A nodding listener has low variance; a talker has HIGH variance)
        best_face = None
        best_variance = -1
        
        for face in faces_data:
            fid = face["id"]
            history = self.lip_history.get(fid, deque())
            if len(history) >= 3:
                variance = np.var(list(history))
            else:
                variance = 0
            
            if variance > best_variance:
                best_variance = variance
                best_face = face
        
        return best_face


def analyze_scene(video_path: str, start: float, end: float, layout_type: str = "talking_head") -> dict:
    """
    Analyze a video segment and calculate crop coordinates.
    
    This is the main entry point for the Director module. It decides:
    - Face Mode: Track active speaker with smooth panning
    - Screen Mode: Use center crop or Fit & Blur
    
    Args:
        video_path: Path to the source video file
        start: Clip start time in seconds
        end: Clip end time in seconds
        layout_type: "talking_head" or "screen_share" (from brain.py)
        
    Returns:
        dict with:
            - mode: "face" or "screen"
            - crop_data: List of (frame_idx, x_center) for face mode
            - frame_count: Total frames in the segment
            - source_width: Original video width
            - source_height: Original video height
    """
    print(f"{Fore.YELLOW}[DIRECTOR]{Style.RESET_ALL} Analyzing scene [{start:.1f}s - {end:.1f}s] "
          f"(requested layout: {layout_type})...")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    source_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    start_frame = int(start * fps)
    end_frame = int(end * fps)
    total_frames = end_frame - start_frame
    
    # ── If explicitly "screen_share", use Screen Mode ─
    if layout_type == "screen_share":
        cap.release()
        print(f"{Fore.GREEN}[DIRECTOR]{Style.RESET_ALL} ✓ Screen Share mode (no face tracking)")
        return {
            "mode": "screen",
            "crop_data": [],
            "frame_count": total_frames,
            "source_width": source_w,
            "source_height": source_h,
            "fps": fps,
        }
    
    # ── Face Mode: Detect and track ────────────
    crop_data = _analyze_faces(cap, start_frame, end_frame, source_w, source_h, fps)
    cap.release()
    
    # If we found zero faces, fallback to Screen Mode
    if not crop_data:
        print(f"{Fore.YELLOW}[DIRECTOR]{Style.RESET_ALL} No faces detected - falling back to center crop")
        return {
            "mode": "screen",
            "crop_data": [],
            "frame_count": total_frames,
            "source_width": source_w,
            "source_height": source_h,
            "fps": fps,
        }
    
    print(f"{Fore.GREEN}[DIRECTOR]{Style.RESET_ALL} ✓ Face tracking: {len(crop_data)} keyframes")
    
    return {
        "mode": "face",
        "crop_data": crop_data,
        "frame_count": total_frames,
        "source_width": source_w,
        "source_height": source_h,
        "fps": fps,
    }


def _analyze_faces(cap, start_frame: int, end_frame: int,
                   source_w: int, source_h: int, fps: float) -> list:
    """
    Run face detection on sampled frames, pick active speaker,
    and smooth the result with a Kalman Filter.
    
    Returns list of (frame_index_relative, smoothed_x_center) tuples.
    """
    kalman = CameraKalmanFilter()
    speaker_detector = ActiveSpeakerDetector()
    
    # The 9:16 crop width from the source
    # If source is 1920x1080, crop_w = 1080 * (9/16) = 607
    crop_w = int(source_h * (9 / 16))
    
    raw_points = []  # (relative_frame_idx, raw_x_center)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=4,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as face_mesh:
        
        for frame_idx in range(end_frame - start_frame):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Only analyze every Nth frame for performance
            if frame_idx % FACE_SAMPLE_RATE != 0:
                continue
            
            # Convert BGR -> RGB for MediaPipe
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            
            if not results.multi_face_landmarks:
                continue
            
            # ── Extract face data ──────────────
            faces_data = []
            for i, face_lm in enumerate(results.multi_face_landmarks):
                # Get face bounding box center (approximate from nose tip)
                nose = face_lm.landmark[1]
                center_x = int(nose.x * source_w)
                
                # Get lip openness for active speaker detection
                lip_open = speaker_detector.get_lip_openness(face_lm, source_h)
                
                # Approximate bounding box area using face width
                xs = [lm.x for lm in face_lm.landmark]
                face_width = (max(xs) - min(xs)) * source_w
                
                faces_data.append({
                    "id": i,
                    "center_x": center_x,
                    "lip_openness": lip_open,
                    "bbox_area": face_width * face_width,  # rough area
                })
            
            # ── Pick the active speaker ────────
            active = speaker_detector.update_and_pick(faces_data)
            if active:
                raw_points.append((frame_idx, active["center_x"]))
    
    if not raw_points:
        return []
    
    # ── Apply Kalman Filter smoothing ──────────
    smoothed_points = []
    kalman.x[0] = raw_points[0][1]  # Initialize with first measurement
    
    for frame_idx, raw_x in raw_points:
        smooth_x = kalman.update(raw_x)
        
        # Clamp the crop window within frame boundaries
        half_crop = crop_w // 2
        smooth_x = max(half_crop, min(source_w - half_crop, smooth_x))
        
        smoothed_points.append((frame_idx, int(smooth_x)))
    
    # ── Interpolate between sampled frames ─────
    # Build a full frame-by-frame crop path
    full_path = _interpolate_crop_path(smoothed_points, end_frame - start_frame)
    
    return full_path


def _interpolate_crop_path(keyframes: list, total_frames: int) -> list:
    """
    Linearly interpolate between keyframe X positions to get
    a crop coordinate for EVERY frame.
    
    Args:
        keyframes: List of (frame_idx, x_center) tuples
        total_frames: Total number of frames in the segment
        
    Returns:
        List of (frame_idx, x_center) for every frame
    """
    if not keyframes:
        return []
    
    if len(keyframes) == 1:
        return [(i, keyframes[0][1]) for i in range(total_frames)]
    
    # Extract arrays for numpy interpolation
    kf_indices = [k[0] for k in keyframes]
    kf_values = [k[1] for k in keyframes]
    
    # Interpolate for all frames
    all_indices = list(range(total_frames))
    interpolated = np.interp(all_indices, kf_indices, kf_values)
    
    return [(i, int(x)) for i, x in zip(all_indices, interpolated)]


def get_screen_layout_filter(source_w: int, source_h: int) -> str:
    """
    Generate the FFmpeg filter string for "Fit & Blur" screen share layout.
    
    This creates a background that is a blurred version of the video,
    with the original video scaled and centered on top.
    
    Output: 1080x1920 (9:16 vertical)
    """
    # Scale the original to fit width (1080)
    scale_factor = TARGET_WIDTH / source_w
    scaled_h = int(source_h * scale_factor)
    
    # The blurred background fills the full 1080x1920
    # The content sits centered vertically
    y_offset = (TARGET_HEIGHT - scaled_h) // 2
    
    filter_str = (
        # Layer 1: Blurred background (fill entire frame)
        f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},gblur=sigma=30[bg];"
        # Layer 2: Scaled content
        f"[0:v]scale={TARGET_WIDTH}:{scaled_h}[fg];"
        # Overlay content on blurred background
        f"[bg][fg]overlay=0:{y_offset}"
    )
    
    return filter_str
