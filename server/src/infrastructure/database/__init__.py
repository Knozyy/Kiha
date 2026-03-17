"""Kiha Server — Database infrastructure package."""

from infrastructure.database.frame_repository import (
    FrameRepository,
    FrameRepositoryProtocol,
)

__all__ = ["FrameRepository", "FrameRepositoryProtocol"]
