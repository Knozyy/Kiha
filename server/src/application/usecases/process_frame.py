"""Kiha Server — Process Frame Use Case."""

from domain.models.base import Frame, InferenceResult
from domain.services.frame_service import FrameService
from infrastructure.database.frame_repository import FrameRepositoryProtocol


class ProcessFrameUseCase:
    """Orchestrates the frame processing pipeline.

    1. Receive frame from UDP
    2. Run AI inference
    3. Store results
    """

    def __init__(
        self,
        frame_service: FrameService,
        frame_repository: FrameRepositoryProtocol,
    ) -> None:
        self._frame_service = frame_service
        self._frame_repository = frame_repository

    async def execute(self, frame: Frame) -> InferenceResult:
        """Process a single frame end-to-end."""
        # Run inference
        result = await self._frame_service.process_frame(frame)

        # Persist frame metadata and inference result
        await self._frame_repository.save_frame_metadata(frame)
        await self._frame_repository.save_inference_result(result)

        return result
