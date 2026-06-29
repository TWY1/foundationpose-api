import logging
import os
import time
from typing import Optional, List, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import trimesh as _trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False
    logger.warning("trimesh not available — cannot load CAD models")

try:
    import torch
    import pyrender
    from estimater import FoundationPose as FPose
    from learning.training.predict_score import ScorePredictor
    from learning.training.predict_pose_refine import PoseRefinePredictor
    HAS_FOUNDATIONPOSE = True
except ImportError:
    HAS_FOUNDATIONPOSE = False
    logger.warning("FoundationPose not available, using mock mode")


def _rot_to_quat(R: np.ndarray):
    trace = R[0, 0] + R[1, 1] + R[2, 2]
    if trace > 0:
        s = 0.5 / np.sqrt(trace + 1.0)
        return [(R[2, 1] - R[1, 2]) * s, (R[0, 2] - R[2, 0]) * s,
                (R[1, 0] - R[0, 1]) * s, 0.25 / s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        return [(0.25 * s), (R[0, 1] + R[1, 0]) / s,
                (R[0, 2] + R[2, 0]) / s, (R[2, 1] - R[1, 2]) / s]
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        return [(R[0, 1] + R[1, 0]) / s, (0.25 * s),
                (R[1, 2] + R[2, 1]) / s, (R[0, 2] - R[2, 0]) / s]
    else:
        s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        return [(R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s,
                (0.25 * s), (R[1, 0] - R[0, 1]) / s]


class PoseEstimator:
    def __init__(self, weights_dir: str = "/app/weights"):
        self.weights_dir = weights_dir
        self.scorer = None
        self.refiner = None
        self.glctx = None
        self.device = None
        self.objects: Dict[str, Any] = {}
        self.sessions: Dict[str, object] = {}

    def load_models(self):
        if not HAS_FOUNDATIONPOSE:
            logger.info("No FoundationPose modules — running in mock mode")
            return

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        logger.info(f"CUDA version: {torch.version.cuda}")

        scorer_path = os.path.join(self.weights_dir, "2024-01-11-20-02-45")
        refiner_path = os.path.join(self.weights_dir, "2023-10-28-18-33-37")

        if not os.path.isdir(scorer_path):
            logger.warning(f"Scorer weights not found at {scorer_path}")
        if not os.path.isdir(refiner_path):
            logger.warning(f"Refiner weights not found at {refiner_path}")

        self.scorer = ScorePredictor()
        self.refiner = PoseRefinePredictor()
        logger.info("Scorer and refiner loaded successfully")

    def load_object(self, object_id: str, mesh_path: str) -> bool:
        if not HAS_TRIMESH:
            logger.error("trimesh not installed — cannot load CAD models")
            return False
        try:
            mesh = _trimesh.load(mesh_path)
            if mesh.is_empty:
                raise ValueError("Empty mesh")
            self.objects[object_id] = mesh
            logger.info(f"Loaded {object_id}: {mesh_path} ({len(mesh.vertices)} vertices)")
            return True
        except Exception as e:
            logger.error(f"Failed to load mesh {mesh_path}: {e}")
            return False

    def remove_object(self, object_id: str):
        self.objects.pop(object_id, None)
        self.sessions.pop(object_id, None)

    def list_objects(self) -> List[str]:
        return list(self.objects.keys())

    def predict(
        self,
        object_id: str,
        rgb: np.ndarray,
        depth: np.ndarray,
        mask: np.ndarray,
        fx: float, fy: float, cx: float, cy: float,
        tracking_mode: bool = False,
        refiner_iterations: int = 5,
    ) -> dict:
        start = time.time()

        if object_id not in self.objects:
            return {"success": False, "error_message": f"Object '{object_id}' not loaded"}

        mesh = self.objects[object_id]
        K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=float)

        if HAS_FOUNDATIONPOSE:
            try:
                return self._predict_foundationpose(
                    object_id, mesh, K, rgb, depth, mask,
                    tracking_mode, refiner_iterations, start,
                )
            except Exception as e:
                logger.error(f"FoundationPose error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error_message": str(e),
                    "processing_time_ms": round((time.time() - start) * 1000, 2),
                }
        else:
            return self._predict_mock(object_id, start)

    def _predict_foundationpose(
        self, object_id, mesh, K, rgb, depth, mask,
        tracking_mode, refiner_iterations, start,
    ):
        is_first = not tracking_mode or object_id not in self.sessions

        if is_first:
            model_pts = np.asarray(mesh.vertices)
            model_normals = np.asarray(mesh.vertex_normals)
            if len(model_normals) == 0:
                model_normals = np.zeros_like(model_pts)

            pose_est = FPose(
                model_pts=model_pts,
                model_normals=model_normals,
                mesh=mesh,
                scorer=self.scorer,
                refiner=self.refiner,
                glctx=self.glctx,
                debug=0,
            )
            self.sessions[object_id] = pose_est
        else:
            pose_est = self.sessions[object_id]

        if is_first:
            pose = pose_est.register(
                K=K, rgb=rgb,
                depth=depth.astype(np.float32),
                ob_mask=(mask > 0).astype(np.uint8),
                iteration=refiner_iterations,
            )
            mode = "register"
        else:
            pose = pose_est.track_one(
                rgb=rgb, depth=depth.astype(np.float32),
                K=K, iteration=refiner_iterations,
            )
            mode = "track"

        elapsed = round((time.time() - start) * 1000, 2)
        logger.info(f"Pose {mode} in {elapsed}ms")

        return self._format_response(pose, pose.tolist(), mode, elapsed)

    def _predict_mock(self, object_id, start):
        elapsed = round((time.time() - start) * 1000, 2)
        z = 0.3 + (hash(object_id) % 100) / 100.0
        pose = np.eye(4)
        pose[:3, 3] = [0.0, 0.0, z]
        return self._format_response(pose, pose.tolist(), "mock", elapsed)

    @staticmethod
    def _format_response(pose_mat, pose_list, mode, elapsed_ms):
        rot = pose_mat[:3, :3]
        quat = _rot_to_quat(rot)
        return {
            "success": True,
            "pose_matrix": pose_list,
            "ros_pose": {
                "position": {
                    "x": float(pose_mat[0, 3]),
                    "y": float(pose_mat[1, 3]),
                    "z": float(pose_mat[2, 3]),
                },
                "orientation": {
                    "x": float(quat[0]),
                    "y": float(quat[1]),
                    "z": float(quat[2]),
                    "w": float(quat[3]),
                },
            },
            "mode": mode,
            "processing_time_ms": elapsed_ms,
        }

    def is_ready(self) -> bool:
        if HAS_FOUNDATIONPOSE:
            return (self.scorer is not None) and (self.refiner is not None)
        return True

    def get_device(self) -> Optional[str]:
        return self.device if HAS_FOUNDATIONPOSE else None
