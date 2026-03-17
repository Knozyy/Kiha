"""Kiha Server — Frame Processing Service."""

from typing import Protocol

from domain.models.base import Frame, InferenceResult


class InferenceEngineProtocol(Protocol):
    """Interface for AI inference engine implementations."""

    async def run_inference(self, frame: Frame) -> InferenceResult:
        """Run object detection on a single frame."""
        ...


class FrameService:
    """Core business logic for frame processing.

    This service is framework-agnostic and depends only on domain models
    and abstract protocols.
    """

    def __init__(self, inference_engine: InferenceEngineProtocol) -> None:
        self._inference_engine = inference_engine

    async def process_frame(self, frame: Frame) -> InferenceResult:
        """Decode, validate, and run inference on a received frame."""
        self._validate_frame(frame)
        result = await self._inference_engine.run_inference(frame)
        return result

    def _validate_frame(self, frame: Frame) -> None:
        """Validate frame integrity before processing."""
        if not frame.data:
            from domain.exceptions import FrameDecodeError
            raise FrameDecodeError("Empty frame data received")

        if len(frame.data) < 2 or frame.data[:2] != b"\xff\xd8":
            from domain.exceptions import FrameDecodeError
            raise FrameDecodeError("Invalid JPEG header")
