"""Kiha Server — Frame Repository (PostgreSQL)."""

from typing import Protocol

from domain.models.base import Frame, InferenceResult


class FrameRepositoryProtocol(Protocol):
    """Interface for frame data persistence."""

    async def save_frame_metadata(self, frame: Frame) -> None:
        """Save frame metadata to database."""
        ...

    async def save_inference_result(self, result: InferenceResult) -> None:
        """Save inference result to database."""
        ...

    async def get_recent_frames(
        self,
        device_id: str,
        limit: int = 100,
    ) -> list[Frame]:
        """Retrieve recent frames for a device."""
        ...

    async def search_by_label(
        self,
        device_id: str,
        label: str,
    ) -> list[InferenceResult]:
        """Search inference results by detected object label."""
        ...


class FrameRepository:
    """PostgreSQL-backed frame data repository.

    Implements FrameRepositoryProtocol using asyncpg.
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        # TODO: Refactor - Initialize asyncpg connection pool

    async def save_frame_metadata(self, frame: Frame) -> None:
        """Save frame metadata to PostgreSQL."""
        # TODO: Refactor - Implement actual DB insert
        pass

    async def save_inference_result(self, result: InferenceResult) -> None:
        """Save inference result to PostgreSQL."""
        # TODO: Refactor - Implement actual DB insert
        pass

    async def get_recent_frames(
        self,
        device_id: str,
        limit: int = 100,
    ) -> list[Frame]:
        """Retrieve recent frames for a device from PostgreSQL."""
        # TODO: Refactor - Implement actual DB query
        return []

    async def search_by_label(
        self,
        device_id: str,
        label: str,
    ) -> list[InferenceResult]:
        """Search inference results by label from PostgreSQL."""
        # TODO: Refactor - Implement actual DB query with full-text search
        return []
