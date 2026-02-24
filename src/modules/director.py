"""
director.py - The Dynamic Vision Engine (Spatial Reprojection)
================================================================
Handles 16:9 → 9:16 intelligent cropping:
1. Face detection + Active Speaker (lip movement variance)
2. Kalman Filter for cinematic smooth panning
3. Fallback: Letterbox + Blur for multi-speaker or screen-share
"""

import cv2
import numpy as np
from collections import deque
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import (
    TARGET_WIDTH, TARGET_HEIGHT,
    FACE_SAMPLE_RATE, KALMAN_PROCESS_NOISE,
)
from src.utils.logger import log


# ── MediaPipe Setup ────────────────────────────
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    HAS_MEDIAPIPE = True
except (ImportError, AttributeError):
    log("DIRECTOR", "MediaPipe not available. Using OpenCV fallback.", "WARN")
    HAS_MEDIAPIPE = False
    mp_face_mesh = None


class CameraKalmanFilter:
    """
    1D Kalman Filter for smoothing crop X-coordinate.
    Simulates a virtual gimbal for cinematic camera movement.
    """

    def __init__(self, process_noise: float = KALMAN_PROCESS_NOISE):
        self.x = np.array([0.0, 0.0])       # [position, velocity]
        self.P = np.eye(2) * 1000
        self.F = np.array([[1, 1], [0, 1]])  # State transition
        self.H = np.array([[1, 0]])           # Observation
        self.R = np.array([[5.0]])            # Measurement noise
        self.Q = np.eye(2) * process_noise

    def update(self, measurement: float) -> float:
        """Feed a face-center X measurement; returns smoothed X."""
        x_pred = self.F @ self.x
        P_pred = self.F @ self.P @ self.F.T + self.Q
        y = measurement - self.H @ x_pred
        S = self.H @ P_pred @ self.H.T + self.R
        K = P_pred @ self.H.T @ np.linalg.inv(S)
        self.x = x_pred + K.flatten() * y.flatten()[0]
        self.P = (np.eye(2) - K @ self.H) @ P_pred
        return float(self.x[0])


class ActiveSpeakerDetector:
    """
    Enhanced Active Speaker Detection using multi-signal scoring.

    Combines 3 signals to determine who is speaking:
    1. Lip variance (HIGH = speaking) — primary signal
    2. Face area (LARGER = more prominent / closer to camera)
    3. Face position stability (STABLE = intentionally on camera vs. moving through)

    This prevents false positives from people gesturing but not speaking.
    """
    UPPER_LIP = 13
    LOWER_LIP = 14

    # Weights for multi-signal scoring
    LIP_WEIGHT = 0.60     # Lip movement is the strongest signal
    AREA_WEIGHT = 0.25    # Larger face = more prominent
    STABLE_WEIGHT = 0.15  # Stable position = intentional framing

    def __init__(self, history_window: int = 15):
        self.lip_history = {}
        self.position_history = {}
        self.history_window = history_window

    def get_lip_openness(self, face_landmarks, frame_h: int) -> float:
        upper = face_landmarks.landmark[self.UPPER_LIP]
        lower = face_landmarks.landmark[self.LOWER_LIP]
        return abs(lower.y - upper.y) * frame_h

    def update_and_pick(self, faces_data: list) -> dict | None:
        if not faces_data:
            return None
        if len(faces_data) == 1:
            return faces_data[0]

        # Update histories
        for face in faces_data:
            fid = face["id"]
            if fid not in self.lip_history:
                self.lip_history[fid] = deque(maxlen=self.history_window)
                self.position_history[fid] = deque(maxlen=self.history_window)
            self.lip_history[fid].append(face["lip_openness"])
            self.position_history[fid].append(face["center_x"])

        # Score each face on 3 signals
        scores = {}
        max_area = max(f.get("face_area", 1) for f in faces_data) or 1

        for face in faces_data:
            fid = face["id"]

            # Signal 1: Lip movement variance (high = speaking)
            lip_hist = list(self.lip_history.get(fid, []))
            lip_var = np.var(lip_hist) if len(lip_hist) >= 3 else 0
            lip_score = min(lip_var / 5.0, 1.0)  # Normalize to 0-1

            # Signal 2: Face area prominence (larger = closer)
            area_score = face.get("face_area", 0) / max_area

            # Signal 3: Position stability (low variance = stable framing)
            pos_hist = list(self.position_history.get(fid, []))
            pos_var = np.var(pos_hist) if len(pos_hist) >= 3 else 1.0
            stable_score = max(0, 1.0 - (pos_var / 100.0))  # Invert: low var = high score

            # Weighted combination
            scores[fid] = (
                lip_score * self.LIP_WEIGHT +
                area_score * self.AREA_WEIGHT +
                stable_score * self.STABLE_WEIGHT
            )

        best_face = max(faces_data, key=lambda f: scores.get(f["id"], 0))
        return best_face


def analyze_scene(video_path: str, start: float, end: float,
                  layout_type: str = "talking_head") -> dict:
    """
    Analyze a video segment and calculate crop coordinates.

    Modes:
    - Face: Track active speaker with Kalman-filtered panning
    - Screen: Letterbox + Blur (fit content, blurred bg)
    - Fallback: If faces too far apart → letterbox

    Returns:
        dict with mode, crop_data, frame_count, source dimensions, fps
    """
    log("DIRECTOR", f"Analyzing [{start:.1f}s - {end:.1f}s] (layout: {layout_type})...")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    source_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_frame = int(start * fps)
    end_frame = int(end * fps)
    total_frames = end_frame - start_frame

    if layout_type == "screen_share":
        cap.release()
        log("DIRECTOR", "Screen Share → Letterbox+Blur", "OK")
        # Just center the video, maybe blur background
        return _screen_result(total_frames, source_w, source_h, fps)

    if layout_type == "gameplay":
        cap.release()
        log("DIRECTOR", "Gameplay → Center Crop", "OK")
        # Center crop 9:16 (Zoomed in to fill screen)
        # This is better for Minecraft/Gameplay than screen_share (which adds black bars/blur)
        return _gameplay_result(total_frames, source_w, source_h, fps)

    # ── Face Mode ──────────────────────────────
    crop_data, multi_speaker_spread, face_x_coords = _analyze_faces(
        cap, start_frame, end_frame, source_w, source_h, fps
    )
    cap.release()

    # Fallback: if no faces OR faces spread too wide
    if not crop_data or multi_speaker_spread:
        reason = "faces spread too wide" if multi_speaker_spread else "no faces detected"
        if multi_speaker_spread and face_x_coords:
            # K-Means detected 2 distinct speaker positions → split-screen
            log("DIRECTOR", "Multiple speakers detected → Split Screen", "OK")
            return _split_screen_result(face_x_coords, total_frames, source_w, source_h, fps)
        elif not crop_data and layout_type != "screen_share":
            log("DIRECTOR", "No faces detected. Falling back to Gameplay (Center Crop).", "WARN")
            return _gameplay_result(total_frames, source_w, source_h, fps)
        else:
            log("DIRECTOR", f"Fallback → Letterbox+Blur ({reason})", "WARN")
            return _screen_result(total_frames, source_w, source_h, fps)

    log("DIRECTOR", f"Face tracking: {len(crop_data)} keyframes", "OK")
    return {
        "mode": "face",
        "crop_data": crop_data,
        "frame_count": total_frames,
        "source_width": source_w,
        "source_height": source_h,
        "fps": fps,
    }



def _gameplay_result(total_frames, source_w, source_h, fps):
    """
    Returns a static center crop that FILLS the 9:16 screen.
    Useful for Minecraft, Subway Surfers, etc.
    """
    # Target 9:16 aspect ratio
    target_aspect = 9 / 16
    
    # We want to crop a 9:16 area from the center of the source
    # If source is 16:9 (1920x1080), we crop a 608x1080 patch?
    # No, usually we want to zoom in to fill height, then crop width.
    # OR if source is landscape, we want to crop the center to 9:16.
    
    # Example: 1920x1080 source.
    # We want final 1080x1920? No, that's upscaling.
    # We want to crop a 9:16 region.
    # If we keep full height 1080, width would be 1080 * (9/16) = 607.5.
    # Then we scale 607x1080 up to 1080x1920.
    
    crop_h = source_h
    crop_w = int(crop_h * target_aspect)
    
    # Clamp just in case
    if crop_w > source_w:
        crop_w = source_w
        crop_h = int(crop_w / target_aspect)
        
    start_x = (source_w - crop_w) // 2
    
    # Create static crop data for all frames
    # Format: [(frame_idx, center_x), ...]
    # Director expects center_x.
    center_x = source_w // 2
    
    # But wait, director returns "crop_data" which is a list of (frame, center_x).
    # The Editor uses this to build the crop filter.
    # Editor logic: crop=crop_w:crop_h:(center_x - crop_w/2):0
    
    # So we just need to return center_x for every frame.
    
    # Opt: Just return 2 keyframes (start, end) and let interpolation handle it?
    # Or just one point? _interpolate_crop_path handles it.
    
    return {
        "mode": "gameplay",
        "crop_data": [(0, center_x), (total_frames, center_x)],
        "frame_count": total_frames,
        "source_width": source_w,
        "source_height": source_h,
        "fps": fps,
        "crop_w": crop_w,
        "crop_h": crop_h
    }


def _screen_result(total_frames, source_w, source_h, fps):
    return {
        "mode": "screen",
        "crop_data": [],
        "frame_count": total_frames,
        "source_width": source_w,
        "source_height": source_h,
        "fps": fps,
    }


def _analyze_faces(cap, start_frame, end_frame, source_w, source_h, fps):
    """
    Run face detection, pick active speaker, smooth with Kalman.
    Returns (crop_path, multi_speaker_spread_flag).
    """
    kalman = CameraKalmanFilter()
    speaker_det = ActiveSpeakerDetector()
    crop_w = int(source_h * (9 / 16))

    raw_points = []
    all_face_x_coords = []  # Collect all face X positions for K-Means split-screen detection
    spread_count = 0
    total_analyzed = 0

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    # ── Fallback Setup (OpenCV) ──
    face_cascade = None
    if not HAS_MEDIAPIPE:
        try:
            path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(path)
        except Exception:
            pass

    # ── Main Loop ──
    # If MediaPipe exists, use context manager. If not, use dummy loop.
    
    if HAS_MEDIAPIPE:
        face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=4,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
    else:
        face_mesh = None

    try:
        for frame_idx in range(end_frame - start_frame):
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % FACE_SAMPLE_RATE != 0:
                continue

            total_analyzed += 1
            
            best_cx = None

            if HAS_MEDIAPIPE and face_mesh:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                if results.multi_face_landmarks:
                    faces_data = []
                    for i, face_lm in enumerate(results.multi_face_landmarks):
                        # Calculate features
                        nose = face_lm.landmark[1]
                        center_x = int(nose.x * source_w)
                        lip_open = speaker_det.get_lip_openness(face_lm, source_h)
                        xs = [lm.x for lm in face_lm.landmark]
                        face_width = (max(xs) - min(xs)) * source_w

                        faces_data.append({
                            "id": i,
                            "center_x": center_x,
                            "lip_openness": lip_open,
                            "width": face_width
                        })

                        # Collect face X positions for split-screen analysis
                        all_face_x_coords.append(center_x)

                    # Active Speaker Logic
                    active = speaker_det.update_and_pick(faces_data)
                    if active:
                        best_cx = active["center_x"]
            
            elif face_cascade:
                # OpenCV Fallback
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                if len(faces) > 0:
                    # Pick largest face
                    max_area = 0
                    for (x, y, w, h) in faces:
                        area = w * h
                        face_cx = x + w // 2
                        all_face_x_coords.append(face_cx)
                        if area > max_area:
                            max_area = area
                            best_cx = face_cx

            # Kalman Update
            if best_cx is not None:
                smoothed_x = kalman.update(best_cx)
                raw_points.append((frame_idx, int(smoothed_x)))
            elif raw_points:
                # Coast with last predictions
                raw_points.append((frame_idx, raw_points[-1][1]))
            else:
                # Default to center
                raw_points.append((frame_idx, source_w // 2))

    finally:
        if face_mesh:
            face_mesh.close()

    # Post-process: interpolate gaps
    full_path = _interpolate_crop_path(raw_points, end_frame - start_frame)

    # Detect multi-speaker spread using K-Means clustering
    multi_spread = _should_split_screen(all_face_x_coords, source_w)
    return full_path, multi_spread, all_face_x_coords


def _interpolate_crop_path(keyframes: list, total_frames: int) -> list:
    """Linearly interpolate keyframes to get per-frame crop X."""
    if not keyframes:
        return []
    if len(keyframes) == 1:
        return [(i, keyframes[0][1]) for i in range(total_frames)]

    kf_idx = [k[0] for k in keyframes]
    kf_val = [k[1] for k in keyframes]
    all_idx = list(range(total_frames))
    interp = np.interp(all_idx, kf_idx, kf_val)
    return [(i, int(x)) for i, x in zip(all_idx, interp)]


def _should_split_screen(face_x_coords: list, frame_width: int) -> bool:
    """
    Use 1D K-Means clustering to detect 2 distinct speaker positions.
    Only triggers split-screen when:
    - Cluster centers are separated by >30% of frame width
    - Each cluster has low internal spread (speakers staying in their lanes)
    """
    if len(face_x_coords) < 20:
        return False

    try:
        from sklearn.cluster import KMeans

        X = np.array(face_x_coords).reshape(-1, 1)
        kmeans = KMeans(n_clusters=2, n_init=10, random_state=42).fit(X)
        centers = sorted(kmeans.cluster_centers_.flatten())

        distance = centers[1] - centers[0]
        normalized_dist = distance / frame_width

        # Check that each cluster has low spread (speakers aren't wandering)
        cluster_stds = []
        for label in [0, 1]:
            cluster_points = X[kmeans.labels_ == label]
            if len(cluster_points) > 0:
                cluster_stds.append(float(np.std(cluster_points)))
            else:
                return False  # Empty cluster = not 2 real speakers

        avg_std = np.mean(cluster_stds)

        # Criteria: separated by >30% AND each speaker stays in their lane (<15% std)
        is_split = normalized_dist > 0.30 and avg_std < frame_width * 0.15
        if is_split:
            log("DIRECTOR", f"K-Means: 2 speakers detected (sep={normalized_dist:.2f}, std={avg_std:.0f})")
        return is_split

    except ImportError:
        log("DIRECTOR", "scikit-learn not available for split-screen detection", "WARN")
        return False
    except Exception as e:
        log("DIRECTOR", f"Split-screen detection failed: {e}", "WARN")
        return False


def _split_screen_result(face_x_coords: list, total_frames, source_w, source_h, fps):
    """
    Build split-screen result with two face center positions from K-Means clusters.
    """
    try:
        from sklearn.cluster import KMeans

        X = np.array(face_x_coords).reshape(-1, 1)
        kmeans = KMeans(n_clusters=2, n_init=10, random_state=42).fit(X)
        centers = sorted(kmeans.cluster_centers_.flatten())
        left_center = int(centers[0])
        right_center = int(centers[1])
    except Exception:
        # Fallback: divide into thirds
        left_center = source_w // 3
        right_center = 2 * source_w // 3

    return {
        "mode": "split_screen",
        "face_centers": [left_center, right_center],
        "crop_data": [],
        "frame_count": total_frames,
        "source_width": source_w,
        "source_height": source_h,
        "fps": fps,
    }


def get_screen_layout_filter(source_w: int, source_h: int) -> str:
    """
    FFmpeg filter for "Letterbox + Blur" layout.
    Background: blurred video; Foreground: scaled content centered.
    """
    scale_factor = TARGET_WIDTH / source_w
    scaled_h = int(source_h * scale_factor)
    y_offset = (TARGET_HEIGHT - scaled_h) // 2

    return (
        f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},gblur=sigma=30[bg];"
        f"[0:v]scale={TARGET_WIDTH}:{scaled_h}[fg];"
        f"[bg][fg]overlay=0:{y_offset}"
    )
