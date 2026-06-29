import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import cv2
    HAS_YOLO = False
    try:
        from ultralytics import YOLO as YOLOModel
        HAS_YOLO = True
    except ImportError:
        pass
except ImportError:
    HAS_YOLO = False


class Detector:
    def __init__(self, model_path: str = "/app/data/yolo/yolov8n.pt"):
        self.model_path = model_path
        self.model = None
        if HAS_YOLO:
            try:
                self.model = YOLOModel(model_path)
                logger.info(f"YOLO model loaded from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load YOLO model: {e}")

    def is_available(self) -> bool:
        return HAS_YOLO and self.model is not None

    def detect(
        self,
        image: np.ndarray,
        conf_threshold: float = 0.5,
        classes: Optional[List[int]] = None,
    ) -> List[dict]:
        if not self.is_available():
            return []

        results = self.model(
            image,
            conf=conf_threshold,
            classes=classes,
            verbose=False,
        )

        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for box, cls_id, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                x1, y1, x2, y2 = map(int, box.tolist())
                class_name = self.model.names[int(cls_id)]
                detection = {
                    "bbox": [x1, y1, x2, y2],
                    "class_id": int(cls_id),
                    "class_name": class_name,
                    "confidence": float(conf),
                    "mask": None,
                }
                if r.masks is not None:
                    detection["mask"] = r.masks.data[int(cls_id)].cpu().numpy()
                detections.append(detection)

        return detections

    def detect_books(self, image: np.ndarray, conf_threshold: float = 0.5) -> List[dict]:
        return self.detect(image, conf_threshold=conf_threshold, classes=None)
