from pydantic import BaseModel, Field
from typing import Optional, List


class CameraIntrinsics(BaseModel):
    fx: float
    fy: float
    cx: float
    cy: float


class PoseMatrix(BaseModel):
    rotation: List[List[float]]
    translation: List[float]


class PredictRequest(BaseModel):
    object_id: str
    image_base64: str
    depth_base64: Optional[str] = None
    mask_base64: Optional[str] = None
    intrinsics: CameraIntrinsics
    tracking_mode: bool = False
    refiner_iterations: int = 5


class PredictResponse(BaseModel):
    status: str
    pose_matrix: Optional[List[List[float]]] = None
    confidence: Optional[float] = None
    mode: Optional[str] = None
    processing_time_ms: float
    error_message: Optional[str] = None


class DetectAndPoseRequest(BaseModel):
    image_base64: str
    depth_base64: Optional[str] = None
    intrinsics: CameraIntrinsics
    conf_threshold: float = 0.5


class DetectAndPoseResponse(BaseModel):
    status: str
    detections: List[dict]
    total_processing_time_ms: float


class ObjectUploadResponse(BaseModel):
    object_id: str
    status: str
    message: str


class ObjectInfo(BaseModel):
    object_id: str
    mesh_file: str
    vertices: int
    faces: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    scorer_loaded: bool
    refiner_loaded: bool
    yolo_available: bool
    objects_loaded: List[str]
    device: Optional[str] = None
