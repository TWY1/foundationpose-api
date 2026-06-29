import base64
import os
import uuid
import time as _time
import logging
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from schemas.schemas import (
    PredictRequest,
    PredictResponse,
    DetectAndPoseRequest,
    DetectAndPoseResponse,
    ObjectUploadResponse,
    ObjectInfo,
    HealthResponse,
)
from models.pose_estimator import PoseEstimator
from models.detector import Detector

logger = logging.getLogger(__name__)

router = APIRouter()
estimator = PoseEstimator()
detector = Detector()

DATA_DIR = Path(os.getenv("FOUNDATIONPOSE_DATA", "/app/data"))
OBJECTS_DIR = DATA_DIR / "objects"
OUTPUT_DIR = DATA_DIR / "output"
YOLO_DIR = DATA_DIR / "yolo"
OBJECTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
YOLO_DIR.mkdir(parents=True, exist_ok=True)


def decode_b64(b64_str: str, flag: int = cv2.IMREAD_COLOR) -> np.ndarray:
    try:
        data = base64.b64decode(b64_str)
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, flag)
        if img is None:
            raise ValueError("Empty or invalid image data")
        return img
    except Exception as e:
        raise ValueError(f"Failed to decode base64: {e}")


def encode_b64(img: np.ndarray, ext: str = ".png") -> str:
    _, buf = cv2.imencode(ext, img)
    return base64.b64encode(buf.tobytes()).decode()


# ── Health ────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        service="FoundationPose",
        version="1.0.0",
        scorer_loaded=estimator.is_ready(),
        refiner_loaded=estimator.is_ready(),
        yolo_available=detector.is_available(),
        objects_loaded=estimator.list_objects(),
        device=estimator.get_device(),
    )


# ── Object Management ─────────────────────────────────────────

@router.post("/objects/upload", response_model=ObjectUploadResponse)
async def upload_object(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in (".obj", ".stl", ".ply", ".glb", ".gltf"):
        raise HTTPException(400, f"Unsupported format: {ext}")

    object_id = str(uuid.uuid4())[:8]
    save_path = OBJECTS_DIR / f"{object_id}{ext}"
    save_path.write_bytes(await file.read())

    ok = estimator.load_object(object_id, str(save_path))
    if not ok:
        save_path.unlink(missing_ok=True)
        raise HTTPException(400, "Failed to load mesh – file may be corrupt")

    mesh = estimator.objects[object_id]
    return ObjectUploadResponse(
        object_id=object_id,
        status="loaded",
        message=f"Mesh: {save_path.name}, {len(mesh.vertices)} vertices",
    )


@router.delete("/objects/{object_id}")
async def delete_object(object_id: str):
    estimator.remove_object(object_id)
    for p in OBJECTS_DIR.glob(f"{object_id}.*"):
        p.unlink()
    return {"status": "removed", "object_id": object_id}


@router.get("/objects", response_model=List[ObjectInfo])
async def list_objects():
    infos = []
    for oid, mesh in estimator.objects.items():
        path = next(OBJECTS_DIR.glob(f"{oid}.*"), None)
        infos.append(ObjectInfo(
            object_id=oid,
            mesh_file=path.name if path else "unknown",
            vertices=len(mesh.vertices),
            faces=len(mesh.faces),
        ))
    return infos


# ── Pose Estimation ───────────────────────────────────────────

@router.post("/predict", response_model=PredictResponse)
async def predict_json(req: PredictRequest):
    if req.object_id not in estimator.objects:
        raise HTTPException(404, f"Object '{req.object_id}' not found — upload first")

    try:
        rgb = decode_b64(req.image_base64, cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

        depth = None
        if req.depth_base64:
            d = decode_b64(req.depth_base64, cv2.IMREAD_UNCHANGED)
            depth = d.astype(np.float32) / 1000.0

        mask = None
        if req.mask_base64:
            mask = decode_b64(req.mask_base64, cv2.IMREAD_GRAYSCALE)
    except ValueError as e:
        raise HTTPException(400, str(e))

    result = estimator.predict(
        object_id=req.object_id, rgb=rgb, depth=depth, mask=mask,
        fx=req.intrinsics.fx, fy=req.intrinsics.fy,
        cx=req.intrinsics.cx, cy=req.intrinsics.cy,
        tracking_mode=req.tracking_mode,
        refiner_iterations=req.refiner_iterations,
    )

    return PredictResponse(
        status="success" if result["success"] else "error",
        pose_matrix=result.get("pose_matrix"),
        mode=result.get("mode"),
        processing_time_ms=result.get("processing_time_ms", 0),
        error_message=result.get("error_message"),
    )


@router.post("/predict/upload", response_model=PredictResponse)
async def predict_upload(
    object_id: str = Form(...),
    file: UploadFile = File(...),
    depth_file: Optional[UploadFile] = File(None),
    mask_file: Optional[UploadFile] = File(None),
    fx: float = Form(...), fy: float = Form(...),
    cx: float = Form(...), cy: float = Form(...),
    tracking_mode: bool = Form(False),
    refiner_iterations: int = Form(5),
):
    if object_id not in estimator.objects:
        raise HTTPException(404, f"Object '{object_id}' not found")

    rgb = cv2.cvtColor(
        cv2.imdecode(np.frombuffer(await file.read(), np.uint8), cv2.IMREAD_COLOR),
        cv2.COLOR_BGR2RGB,
    )

    depth = None
    if depth_file:
        d = cv2.imdecode(np.frombuffer(await depth_file.read(), np.uint8), cv2.IMREAD_UNCHANGED)
        depth = d.astype(np.float32) / 1000.0

    mask = None
    if mask_file:
        mask = cv2.imdecode(np.frombuffer(await mask_file.read(), np.uint8), cv2.IMREAD_GRAYSCALE)

    result = estimator.predict(
        object_id=object_id, rgb=rgb, depth=depth, mask=mask,
        fx=fx, fy=fy, cx=cx, cy=cy,
        tracking_mode=tracking_mode,
        refiner_iterations=refiner_iterations,
    )

    return PredictResponse(
        status="success" if result["success"] else "error",
        pose_matrix=result.get("pose_matrix"),
        mode=result.get("mode"),
        processing_time_ms=result.get("processing_time_ms", 0),
        error_message=result.get("error_message"),
    )


# ── Detect + Pose Pipeline ────────────────────────────────────

@router.post("/detect-and-pose", response_model=DetectAndPoseResponse)
async def detect_and_pose(req: DetectAndPoseRequest):
    t0 = _time.time()

    if not detector.is_available():
        raise HTTPException(400, "YOLO not available – model not loaded")

    try:
        rgb = decode_b64(req.image_base64, cv2.IMREAD_COLOR)
        rgb_rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

        depth = None
        if req.depth_base64:
            d = decode_b64(req.depth_base64, cv2.IMREAD_UNCHANGED)
            depth = d.astype(np.float32) / 1000.0
    except ValueError as e:
        raise HTTPException(400, str(e))

    dets = detector.detect(rgb_rgb, conf_threshold=req.conf_threshold)

    results = []
    for det in dets:
        x1, y1, x2, y2 = det["bbox"]
        mask_det = np.zeros((rgb.shape[0], rgb.shape[1]), dtype=np.uint8)
        mask_det[y1:y2, x1:x2] = 255

        obj_name = f"detected_{det['class_name']}_{det['class_id']}"
        if obj_name not in estimator.objects:
            _make_dummy_box_mesh(obj_name, x2 - x1, y2 - y1)
            estimator.load_object(obj_name, str(OBJECTS_DIR / f"{obj_name}.obj"))

        pose = estimator.predict(
            object_id=obj_name, rgb=rgb_rgb, depth=depth, mask=mask_det,
            fx=req.intrinsics.fx, fy=req.intrinsics.fy,
            cx=req.intrinsics.cx, cy=req.intrinsics.cy,
            tracking_mode=False,
        )

        results.append({
            **det,
            "pose": pose.get("pose_matrix"),
            "pose_processing_ms": pose.get("processing_time_ms"),
        })

    elapsed = round((_time.time() - t0) * 1000, 2)
    return DetectAndPoseResponse(
        status="success",
        detections=results,
        total_processing_time_ms=elapsed,
    )


def _make_dummy_box_mesh(obj_name: str, w: int, h: int):
    import trimesh
    aspect = max(w, 1) / max(h, 1)
    depth_dim = 0.03
    box = trimesh.creation.box(extents=[aspect * 0.1, 0.1, depth_dim])
    path = OBJECTS_DIR / f"{obj_name}.obj"
    box.export(str(path))
