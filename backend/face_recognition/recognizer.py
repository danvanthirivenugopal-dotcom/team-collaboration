import os
import cv2
import numpy as np
import logging
import tempfile
from pathlib import Path
from backend import config
from backend.database.db import get_db

logger = logging.getLogger("faceai.recognizer")

# ─────────────────────────────────────────────────────────────────────────────
# DeepFace configuration
# ─────────────────────────────────────────────────────────────────────────────
DEEPFACE_MODEL    = "ArcFace"    # Primary model: 512-dim ArcFace embeddings
DEEPFACE_FALLBACK = "Facenet512" # Fallback if primary model download fails
DEEPFACE_DETECTOR = "ssd" # Face detector: highly robust for multi-face without OOM
DEEPFACE_ALIGN    = True         # Face alignment improves accuracy

# Active model (will be set to fallback if primary weights fail)
_active_model = DEEPFACE_MODEL

# Cosine similarity threshold for positive identification
COSINE_THRESHOLD = config.COSINE_SIMILARITY_THRESHOLD  # default 0.55

# Global lazy-load flag for DeepFace warmup
_deepface_warmed_up = False
_insightface_app = None  # Global InsightFace app for multi-face detection

def _get_deepface():
    """Lazily import DeepFace to avoid startup time hit."""
    try:
        import os
        os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
        from deepface import DeepFace
        return DeepFace
    except ImportError as e:
        logger.error(f"DeepFace not installed: {e}")
        raise RuntimeError("DeepFace is not installed. Run: pip install deepface tf-keras")


def load_trained_model() -> None:
    """Warm up DeepFace model on startup — downloads weights if missing."""
    global _deepface_warmed_up, _active_model
    if _deepface_warmed_up:
        return
    try:
        DeepFace = _get_deepface()
        # Try primary model (ArcFace)
        try:
            DeepFace.build_model(DEEPFACE_MODEL)
            _active_model = DEEPFACE_MODEL
            logger.info(f"DeepFace '{DEEPFACE_MODEL}' model ready.")
        except Exception as primary_err:
            logger.warning(f"Primary model '{DEEPFACE_MODEL}' failed ({primary_err}). Trying fallback '{DEEPFACE_FALLBACK}'…")
            DeepFace.build_model(DEEPFACE_FALLBACK)
            _active_model = DEEPFACE_FALLBACK
            logger.info(f"DeepFace fallback model '{DEEPFACE_FALLBACK}' loaded.")
        _deepface_warmed_up = True
    except Exception as e:
        logger.error(f"DeepFace warmup failed: {e}")


def get_image_embedding(img: np.ndarray) -> np.ndarray | None:
    """
    Extract the face embedding vector for the dominant (largest) face in the image
    using DeepFace with the configured model.

    Returns:
        np.ndarray of shape (embedding_dim,) or None if no face is detected.
    """
    if img is None:
        return None

    try:
        DeepFace = _get_deepface()

        # Convert image from BGR to RGB for DeepFace represent compatibility
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        representations = DeepFace.represent(
            img_path=img_rgb,
            model_name=_active_model,
            detector_backend=DEEPFACE_DETECTOR,
            align=DEEPFACE_ALIGN,
            enforce_detection=False,
        )

        if not representations:
            return None

        if isinstance(representations, dict):
            representations = [representations]

        best = None
        best_area = 0
        for rep in representations:
            region = rep.get("facial_area", {})
            w = region.get("w", 1)
            h = region.get("h", 1)
            area = w * h
            if area > best_area:
                best_area = area
                best = rep

        if best is None or best.get("embedding") is None:
            return None

        return np.array(best["embedding"], dtype=np.float32)

    except Exception as e:
        logger.error(f"DeepFace embedding extraction failed: {e}")
        return None


def get_image_embeddings_all(img: np.ndarray) -> list[tuple[np.ndarray, list[int]]] | None:
    """
    Detect all faces and extract DeepFace embeddings.
    Uses the exact same extraction pipeline as get_image_embedding for 100% compatibility.
    """
    if img is None or img.size == 0:
        return None

    try:
        DeepFace = _get_deepface()
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        representations = DeepFace.represent(
            img_path=img_rgb,
            model_name=_active_model,
            detector_backend=DEEPFACE_DETECTOR,
            align=DEEPFACE_ALIGN,
            enforce_detection=False,
        )

        if not representations:
            return None
            
        if isinstance(representations, dict):
            representations = [representations]

        results = []
        for rep in representations:
            if rep.get("embedding") is None:
                continue
                
            emb = np.array(rep["embedding"], dtype=np.float32)
            
            region = rep.get("facial_area", {})
            x = region.get("x", 0)
            y = region.get("y", 0)
            w = region.get("w", 0)
            h = region.get("h", 0)
            
            # Basic validation of face box
            if w <= 0 or h <= 0:
                continue
                
            results.append((emb, [x, y, x + w, y + h]))

        logger.info(f"DeepFace: detected {len(results)} faces")
        return results if results else None

    except Exception as e:
        logger.error(f"DeepFace multi-face extraction failed: {e}")
        return None

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b + 1e-8))


def check_face_quality(
    img: np.ndarray,
    bbox: tuple | list | None = None,
    keypoints: list | None = None,
    detection_confidence: float | None = None
) -> tuple[bool, str]:
    """
    Reject poor enrollment images:
    - blur
    - low/high lighting
    - small face
    - low confidence
    - excessive head angle
    - possible occlusion
    """
    if img is None:
        return False, "Empty image."

    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    except Exception:
        return False, "Failed to analyze image format."

    # 1. Lighting check
    brightness = float(np.mean(gray))
    if brightness < 45:
        return False, f"Low lighting detected. Brightness score: {brightness:.1f}. Please move to better light."
    if brightness > 225:
        return False, f"Too much light detected. Brightness score: {brightness:.1f}. Reduce glare."

    # 2. Blur check
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if blur_score < 45:
        return False, f"Face image is blurry. Blur score: {blur_score:.1f}. Keep camera steady."

    # 3. Face size check
    if bbox is not None and len(bbox) == 4:
        x, y, w, h = bbox
        face_ratio = (w * h) / float(img.shape[0] * img.shape[1])

        if face_ratio < 0.08:
            return False, f"Face too far from camera. Face coverage: {face_ratio*100:.1f}%."

        if face_ratio > 0.75:
            return False, "Face too close to camera. Move slightly back."

        face_crop = gray[max(0, y):max(0, y) + h, max(0, x):max(0, x) + w]

        if face_crop.size > 0:
            face_brightness = float(np.mean(face_crop))
            face_contrast = float(np.std(face_crop))

            if face_contrast < 18:
                return False, "Face has very low contrast. Improve lighting and remove shadows."

    # 4. YOLO / detector confidence check
    if detection_confidence is not None and detection_confidence < 0.50:
        return False, f"Low face detection confidence: {detection_confidence:.2f}. Please face the camera clearly."

    # 5. Head angle / occlusion check using 5 keypoints
    if keypoints and len(keypoints) >= 5:
        try:
            left_eye = keypoints[0][:2]
            right_eye = keypoints[1][:2]
            nose = keypoints[2][:2]
            left_mouth = keypoints[3][:2]
            right_mouth = keypoints[4][:2]

            points = [left_eye, right_eye, nose, left_mouth, right_mouth]

            # Missing landmark means possible occlusion: mask, sunglasses, covered face
            for px, py in points:
                if px <= 1 or py <= 1:
                    return False, "Face landmarks are not clear. Remove mask, sunglasses, or obstruction."

            eye_distance = abs(right_eye[0] - left_eye[0])
            if eye_distance < 25:
                return False, "Face angle is not clear. Look straight at the camera."

            nose_to_left = abs(nose[0] - left_eye[0])
            nose_to_right = abs(nose[0] - right_eye[0])
            side_ratio = nose_to_left / (nose_to_right + 1e-6)

            if side_ratio > 1.9 or side_ratio < 0.52:
                return False, "Excessive head rotation detected. Look straight at the camera."

            eye_y_diff = abs(left_eye[1] - right_eye[1])
            if eye_y_diff > eye_distance * 0.25:
                return False, "Face is tilted. Keep your head straight."

            mouth_width = abs(right_mouth[0] - left_mouth[0])
            if mouth_width < eye_distance * 0.35:
                return False, "Possible mouth/mask occlusion detected. Remove mask or obstruction."

        except Exception:
            return False, "Could not verify face landmarks clearly. Try again."

    return True, ""

def analyze_spoof_risk(img: np.ndarray, bbox: tuple | list | None = None) -> tuple[bool, str]:
    """
    Basic anti-spoofing checks:
    - printed photo / flat image texture
    - screen replay glare
    - reflection highlights
    - weak depth/texture consistency
    """

    if img is None or img.size == 0:
        return False, "Invalid image for spoof analysis."

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Reflection / screen glare check
    bright_pixels = np.sum(gray > 245)
    bright_ratio = bright_pixels / gray.size

    if bright_ratio > 0.08:
        return False, "Possible screen replay or strong reflection detected. Reduce glare and avoid showing photos from another device."

    # Printed photo / screen texture check using edge density
    edges = cv2.Canny(gray, 80, 160)
    edge_density = np.sum(edges > 0) / edges.size

    if edge_density < 0.015:
        return False, "Face appears too flat. Possible printed photo spoof detected."

    if edge_density > 0.22:
        return False, "Unnatural texture detected. Possible screen/photo replay attack."

    # Face crop depth/texture consistency
    if bbox is not None and len(bbox) == 4:
        x, y, w, h = bbox
        face_crop = gray[max(0, y):max(0, y) + h, max(0, x):max(0, x) + w]

        if face_crop.size > 0:
            face_std = float(np.std(face_crop))
            if face_std < 18:
                return False, "Face texture is too uniform. Possible flat photo spoof."

            lap = cv2.Laplacian(face_crop, cv2.CV_64F)
            depth_score = float(np.var(lap))

            if depth_score < 20:
                return False, "Weak depth consistency detected. Please use a real live face."

    return True, ""

def verify_liveness_from_poses(pose_images: list[np.ndarray]) -> tuple[bool, str]:
    """
    Multi-frame liveness check using 5 enrollment poses.
    Rejects static printed/photo replay by checking:
    - face size movement
    - brightness variation
    - image difference between poses
    """

    if len(pose_images) < 5:
        return False, "All 5 live face poses are required."

    gray_images = []

    for img in pose_images:
        if img is None or img.size == 0:
            return False, "Invalid pose image during liveness check."

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 160))
        gray_images.append(gray)

    diffs = []

    for i in range(len(gray_images) - 1):
        diff = cv2.absdiff(gray_images[i], gray_images[i + 1])
        score = float(np.mean(diff))
        diffs.append(score)

    avg_motion = float(np.mean(diffs))

    if avg_motion < 4.5:
        return False, "Weak live movement detected. Please move your real head, not a static photo."

    brightness_values = [float(np.mean(g)) for g in gray_images]
    brightness_variation = max(brightness_values) - min(brightness_values)

    if brightness_variation < 2.0:
        return False, "Very low frame variation detected. Possible photo or screen replay."

    return True, ""

def train_recognizer() -> None:
    """
    Pre-extract and cache DeepFace embeddings for all registered users.
    Reads pose_*.jpg files from uploads/enrollments/<user_id>/ and saves
    embeddings as embeddings.npy for fast cosine-similarity lookup at scan time.
    """
    logger.info("Pre-caching DeepFace embeddings for all enrolled users...")
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name 
                    FROM users 
                """)
            users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to query users for embedding training: {e}")
        return

    for user in users:
        user_id = user["id"]
        enroll_dir = config.UPLOAD_DIR / "enrollments" / str(user_id)
        if not enroll_dir.exists():
            continue

        pose_files = list(enroll_dir.glob("pose_*.jpg"))
        if not pose_files:
            npy_path = enroll_dir / "embeddings.npy"
            if npy_path.exists():
                logger.info(f"Embeddings cached for user {user_id} ({user['name']}), no new poses.")
            else:
                logger.warning(f"No pose files found for user {user_id} ({user['name']})")
            continue

        user_embeddings = {}
        for file in pose_files:
            pose_name = file.stem.replace("pose_", "")
            img = cv2.imread(str(file))
            if img is None:
                continue
            emb = get_image_embedding(img)
            if emb is not None:
                user_embeddings[pose_name] = emb.tolist()

        if user_embeddings:
            np.save(str(enroll_dir / "embeddings.npy"), user_embeddings)

            # Privacy: delete raw enrollment face images after embeddings are saved
            for pose_file in pose_files:
                try:
                    pose_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete raw pose image {pose_file}: {e}")

            logger.info(
                f"Cached {len(user_embeddings)} DeepFace embeddings for user {user_id} "
                f"({user['name']}) and deleted raw pose images."
            )
        else:
            logger.warning(f"No faces extracted for user {user_id}")


def train_lbph() -> None:
    """Alias kept for backward compatibility — calls train_recognizer()."""
    train_recognizer()


def _try_generate_embeddings(user_id: int, enroll_dir: Path) -> bool:
    """
    Attempt to generate embeddings.npy on-the-fly when it's missing.
    Tries pose files first, then falls back to profile image.
    Returns True if embeddings were successfully generated.
    """
    npy_path = enroll_dir / "embeddings.npy"
    user_embeddings = {}

    # Try pose files first
    pose_files = list(enroll_dir.glob("pose_*.jpg"))
    if pose_files:
        for file in pose_files:
            pose_name = file.stem.replace("pose_", "")
            img = cv2.imread(str(file))
            if img is None:
                continue
            emb = get_image_embedding(img)
            if emb is not None:
                user_embeddings[pose_name] = emb.tolist()

    # Fallback: try user's profile image from uploads folders
    if not user_embeddings:
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT profile_image FROM users WHERE id = %s", (user_id,))
                    row = cursor.fetchone()
            if row and row.get("profile_image"):
                profile_filename = row["profile_image"]
                for folder in ["users", "admins", "registered"]:
                    profile_path = config.UPLOAD_DIR / folder / profile_filename
                    if profile_path.exists():
                        img = cv2.imread(str(profile_path))
                        if img is not None:
                            emb = get_image_embedding(img)
                            if emb is not None:
                                user_embeddings["profile"] = emb.tolist()
                                logger.info(f"Generated embedding from profile image for user {user_id}")
                        break
        except Exception as e:
            logger.error(f"Failed to generate embedding from profile image for user {user_id}: {e}")

    if user_embeddings:
        enroll_dir.mkdir(parents=True, exist_ok=True)
        np.save(str(npy_path), user_embeddings)
        logger.info(f"On-the-fly generated {len(user_embeddings)} embeddings for user {user_id}")
        return True

    return False


def predict_face(color_img: np.ndarray, organization_id: int = 1) -> tuple[int, float] | None:
    """
    Predict identity for the dominant face in an image by comparing its
    DeepFace embedding against all approved users' cached embeddings.

    Returns:
        (user_id, cosine_similarity) or None
    """
    scan_emb = get_image_embedding(color_img)
    if scan_emb is None:
        logger.info("predict_face: No face detected or embedding failed.")
        return None

    best_user_id = -1
    best_sim = -1.0

    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name 
                    FROM users 
                    WHERE organization_id = %s
                """, (organization_id,))
                users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to query approved users: {e}")
        return None

    for user in users:
        user_id = user["id"]
        enroll_dir = config.UPLOAD_DIR / "enrollments" / str(user_id)
        npy_path = enroll_dir / "embeddings.npy"

        # Fallback: generate embeddings on-the-fly if missing
        if not npy_path.exists():
            if enroll_dir.exists():
                _try_generate_embeddings(user_id, enroll_dir)
            if not npy_path.exists():
                continue

        try:
            user_embs_dict = np.load(str(npy_path), allow_pickle=True).item()
            for pose, emb_list in user_embs_dict.items():
                emb = np.array(emb_list, dtype=np.float32)
                sim = _cosine_similarity(scan_emb, emb)
                if sim > best_sim:
                    best_sim = sim
                    best_user_id = user_id
        except Exception as e:
            logger.error(f"Error reading embeddings for user {user_id}: {e}")

    if best_user_id != -1 and best_sim >= COSINE_THRESHOLD:
        logger.info(f"predict_face matched user_id={best_user_id}, sim={best_sim:.4f}")
        return best_user_id, best_sim

    logger.info(f"predict_face: no valid match. best_user_id={best_user_id}, best_sim={best_sim:.4f}")
    return None

def _filter_duplicate_face_boxes(face_results: list[tuple[np.ndarray, list[int]]]) -> list[tuple[np.ndarray, list[int]]]:
    """
    Remove duplicate overlapping face boxes.
    Sometimes DeepFace returns multiple boxes for the same face.
    """
    if not face_results:
        return []

    filtered = []

    for emb, box in face_results:
        x1, y1, x2, y2 = box
        area = max(1, (x2 - x1) * (y2 - y1))

        duplicate = False

        for _, kept_box in filtered:
            kx1, ky1, kx2, ky2 = kept_box

            ix1 = max(x1, kx1)
            iy1 = max(y1, ky1)
            ix2 = min(x2, kx2)
            iy2 = min(y2, ky2)

            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            kept_area = max(1, (kx2 - kx1) * (ky2 - ky1))
            iou = inter / float(area + kept_area - inter)

            if iou > 0.45:
                duplicate = True
                break

        if not duplicate:
            filtered.append((emb, box))

    return filtered


def predict_multiple_faces(color_img: np.ndarray, organization_id: int = 1) -> list[dict]:
    """
    Predict identities for ALL faces detected in the image.

    Returns:
        list of dicts: {"user_id": int, "similarity": float, "bbox": [x1, y1, x2, y2]}
    """
    face_results = get_image_embeddings_all(color_img)
    if not face_results:
        return []

    face_results = _filter_duplicate_face_boxes(face_results)

    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name 
                    FROM users 
                    WHERE organization_id = %s
                """, (organization_id,))
                users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to query approved users for multi-face prediction: {e}")
        return []

    predictions = []
    for scan_emb, bbox in face_results:
        best_user_id = -1
        best_sim = -1.0

        for user in users:
            user_id = user["id"]
            enroll_dir = config.UPLOAD_DIR / "enrollments" / str(user_id)
            npy_path = enroll_dir / "embeddings.npy"

            # Fallback: generate embeddings on-the-fly if missing
            if not npy_path.exists():
                if enroll_dir.exists():
                    _try_generate_embeddings(user_id, enroll_dir)
                if not npy_path.exists():
                    continue

            try:
                user_embs_dict = np.load(str(npy_path), allow_pickle=True).item()
                for pose, emb_list in user_embs_dict.items():
                    emb = np.array(emb_list, dtype=np.float32)
                    sim = _cosine_similarity(scan_emb, emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_user_id = user_id
            except Exception as e:
                logger.error(f"Error reading embeddings for user {user_id}: {e}")

        if best_user_id != -1 and best_sim >= COSINE_THRESHOLD:
            predictions.append({
                "user_id": best_user_id,
                "similarity": best_sim,
                "bbox": bbox,
            })
        else:
            predictions.append({
                "user_id": -1,
                "similarity": best_sim,
                "bbox": bbox,
            })

    return predictions


def verify_faces_deepface(img1: np.ndarray, img2: np.ndarray) -> dict:
    """
    Directly verify if two face images belong to the same person using DeepFace.verify().
    Useful for duplicate-face checks during enrollment.

    Returns:
        {"verified": bool, "distance": float, "threshold": float, "similarity": float}
    """
    try:
        DeepFace = _get_deepface()
        result = DeepFace.verify(
            img1_path=img1,
            img2_path=img2,
            model_name=_active_model,
            detector_backend=DEEPFACE_DETECTOR,
            align=DEEPFACE_ALIGN,
            enforce_detection=False,
        )
        dist = result.get("distance", 1.0)
        sim = max(0.0, 1.0 - dist)
        return {
            "verified": result.get("verified", False),
            "distance": dist,
            "threshold": result.get("threshold", 0.68),
            "similarity": sim,
        }
    except Exception as e:
        logger.error(f"DeepFace.verify failed: {e}")
        return {"verified": False, "distance": 1.0, "threshold": 0.68, "similarity": 0.0}


def verify_structural_correlation(user_id: int, scan_gray_face: np.ndarray) -> bool:
    """Stub kept for legacy API compatibility."""
    return True
