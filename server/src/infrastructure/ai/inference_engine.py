"""Kiha Server — YOLOv8 AI Inference Engine.

Real implementation using ultralytics YOLOv8 for object detection.
Supports both ONNX Runtime and PyTorch backends.
"""

import asyncio
import logging
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from domain.exceptions import FrameDecodeError, InferenceTimeoutError
from domain.models.base import BoundingBox, Detection, Frame, InferenceResult
from domain.services.frame_service import InferenceEngineProtocol

logger = logging.getLogger(__name__)

# YOLO COCO class names (80 classes)
YOLO_CLASSES: dict[int, str] = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
    20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
    25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
    30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite",
    34: "baseball bat", 35: "baseball glove", 36: "skateboard",
    37: "surfboard", 38: "tennis racket", 39: "bottle", 40: "wine glass",
    41: "cup", 42: "fork", 43: "knife", 44: "spoon", 45: "bowl",
    46: "banana", 47: "apple", 48: "sandwich", 49: "orange", 50: "broccoli",
    51: "carrot", 52: "hot dog", 53: "pizza", 54: "donut", 55: "cake",
    56: "chair", 57: "couch", 58: "potted plant", 59: "bed",
    60: "dining table", 61: "toilet", 62: "tv", 63: "laptop", 64: "mouse",
    65: "remote", 66: "keyboard", 67: "cell phone", 68: "microwave",
    69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator", 73: "book",
    74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear",
    78: "hair drier", 79: "toothbrush",
}


class YoloInferenceEngine:
    """YOLOv8-based object detection engine.

    Implements InferenceEngineProtocol.
    Uses ultralytics for model loading and inference.
    Target: < 5ms/frame with TensorRT on GPU.
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        device: str = "cpu",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        max_detections: int = 50,
        inference_timeout_seconds: float = 10.0,
    ) -> None:
        self._model_path = model_path
        self._device = device
        self._confidence_threshold = confidence_threshold
        self._iou_threshold = iou_threshold
        self._max_detections = max_detections
        self._inference_timeout = inference_timeout_seconds
        self._model: YOLO | None = None

    def load_model(self) -> None:
        """Load the YOLO model into memory.

        Call this during application startup (lifespan).
        Downloads yolov8n.pt automatically if not found.
        """
        model_file = Path(self._model_path)
        if not model_file.exists():
            logger.error(
                "Model file not found at %s, downloading yolov8n.pt...",
                self._model_path,
            )
            self._model_path = "yolov8n.pt"

        self._model = YOLO(self._model_path)
        logger.error(
            "YOLO model loaded: %s (device: %s)",
            self._model_path,
            self._device,
        )

    async def run_inference(self, frame: Frame) -> InferenceResult:
        """Run YOLOv8 object detection on a single frame.

        1. Decode JPEG bytes → numpy array (OpenCV)
        2. Run YOLO prediction
        3. Convert results to domain Detection models
        4. Measure and report inference time
        """
        if self._model is None:
            self.load_model()
            if self._model is None:
                raise InferenceTimeoutError("Model failed to load")

        # Decode JPEG frame
        image = self._decode_frame(frame)

        # Run inference in thread pool (YOLO is sync/blocking)
        start_time = time.perf_counter()

        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(
                    self._predict,
                    image,
                ),
                timeout=self._inference_timeout,
            )
        except TimeoutError as err:
            raise InferenceTimeoutError(
                f"Inference timed out after {self._inference_timeout}s"
            ) from err

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Convert YOLO results to domain models
        detections = self._parse_results(results, frame.width, frame.height)

        logger.error(
            "Frame %d: %d detections in %.1fms",
            frame.frame_id,
            len(detections),
            elapsed_ms,
        )

        from datetime import datetime

        return InferenceResult(
            frame_id=frame.frame_id,
            timestamp=datetime.now(),
            detections=detections,
            inference_time_ms=round(elapsed_ms, 2),
        )

    def _decode_frame(self, frame: Frame) -> np.ndarray:
        """Decode JPEG bytes to numpy array using OpenCV."""
        if not frame.data:
            raise FrameDecodeError("Empty frame data")

        # JPEG magic bytes check
        if len(frame.data) < 2 or frame.data[:2] != b"\xff\xd8":
            raise FrameDecodeError("Invalid JPEG header (expected FF D8)")

        np_array = np.frombuffer(frame.data, dtype=np.uint8)
        image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if image is None:
            raise FrameDecodeError("OpenCV failed to decode JPEG frame")

        return image

    def _predict(self, image: np.ndarray) -> list[object]:
        """Run YOLO prediction (blocking — called via asyncio.to_thread)."""
        if self._model is None:
            raise InferenceTimeoutError("Model not loaded")

        results = self._model.predict(
            source=image,
            conf=self._confidence_threshold,
            iou=self._iou_threshold,
            max_det=self._max_detections,
            device=self._device,
            verbose=False,
        )
        return results  # type: ignore[return-value]

    def _parse_results(
        self,
        results: list[object],
        frame_width: int,
        frame_height: int,
    ) -> list[Detection]:
        """Convert YOLO results to domain Detection models."""
        detections: list[Detection] = []

        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                # Extract class, confidence, and bbox
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()

                label = YOLO_CLASSES.get(cls_id, f"class_{cls_id}")

                # Normalize bbox to 0-1 range
                x_min = max(0.0, min(1.0, xyxy[0] / frame_width))
                y_min = max(0.0, min(1.0, xyxy[1] / frame_height))
                x_max = max(0.0, min(1.0, xyxy[2] / frame_width))
                y_max = max(0.0, min(1.0, xyxy[3] / frame_height))

                detections.append(Detection(
                    label=label,
                    confidence=round(conf, 4),
                    bbox=BoundingBox(
                        x_min=round(x_min, 4),
                        y_min=round(y_min, 4),
                        x_max=round(x_max, 4),
                        y_max=round(y_max, 4),
                    ),
                ))

        return detections


# Protocol compliance verification
_engine: InferenceEngineProtocol = YoloInferenceEngine(
    model_path="yolov8n.pt",
    device="cpu",
)
