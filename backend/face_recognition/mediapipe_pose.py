import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pathlib import Path
import logging
from typing import Optional, Tuple

logger = logging.getLogger("faceai.mediapipe_pose")

MODEL_PATH = Path(__file__).resolve().parents[2] / "data" / "mediapipe" / "face_landmarker.task"

_landmarker = None


def init_landmarker() -> None:
    global _landmarker

    if _landmarker is not None:
        return

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"MediaPipe model not found: {MODEL_PATH}. "
            "Download face_landmarker.task and place it inside data/mediapipe/"
        )

    try:
        base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1
        )
        _landmarker = vision.FaceLandmarker.create_from_options(options)
        logger.info("MediaPipe FaceLandmarker initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize MediaPipe FaceLandmarker: {e}")
        raise


def get_landmarker():
    global _landmarker

    if _landmarker is None:
        init_landmarker()

    return _landmarker


def get_face_bbox(landmarks, img_w: int, img_h: int) -> Tuple[int, int, int, int]:
    if not landmarks:
        return 0, 0, 0, 0

    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    x = int(x_min * img_w)
    y = int(y_min * img_h)
    w = int((x_max - x_min) * img_w)
    h = int((y_max - y_min) * img_h)

    margin_w = int(w * 0.15)
    margin_h = int(h * 0.15)

    x_out = max(0, x - margin_w)
    y_out = max(0, y - margin_h)
    w_out = min(img_w - x_out, w + 2 * margin_w)
    h_out = min(img_h - y_out, h + 2 * margin_h)

    return x_out, y_out, w_out, h_out


def classify_pose_from_landmarks(landmarks) -> str:
    if landmarks is None or len(landmarks) < 363:
        return "front"

    le_x = (landmarks[33].x + landmarks[133].x) / 2.0
    le_y = (landmarks[33].y + landmarks[133].y) / 2.0

    re_x = (landmarks[263].x + landmarks[362].x) / 2.0
    re_y = (landmarks[263].y + landmarks[362].y) / 2.0

    n_x, n_y = landmarks[1].x, landmarks[1].y
    lm_x, lm_y = landmarks[61].x, landmarks[61].y
    rm_x, rm_y = landmarks[291].x, landmarks[291].y

    d_left = abs(n_x - le_x)
    d_right = abs(n_x - re_x)
    ratio = d_left / (d_right + 1e-6)

    eye_y_avg = (le_y + re_y) / 2.0
    mouth_y_avg = (lm_y + rm_y) / 2.0
    face_h = mouth_y_avg - eye_y_avg

    if face_h <= 0:
        face_h = 1.0

    v_ratio = (n_y - eye_y_avg) / face_h

    if ratio > 1.35:
        return "right"
    if ratio < 0.70:
        return "left"
    if v_ratio < 0.40:
        return "up"
    if v_ratio > 0.58:
        return "down"

    return "front"


def detect_single_face_pose(img: np.ndarray) -> Optional[Tuple[Tuple[int, int, int, int], str]]:
    if img is None:
        return None

    try:
        landmarker = get_landmarker()
        img_h, img_w = img.shape[:2]

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        result = landmarker.detect(mp_image)

        if not result.face_landmarks:
            return None

        landmarks = result.face_landmarks[0]
        bbox = get_face_bbox(landmarks, img_w, img_h)
        pose_str = classify_pose_from_landmarks(landmarks)

        return bbox, pose_str

    except Exception as e:
        logger.error(f"Error in MediaPipe pose detection: {e}")
        return None