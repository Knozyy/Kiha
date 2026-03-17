"""Kiha Server — Domain package."""

from domain.exceptions import (
    ChatSessionError,
    DeviceAuthenticationError,
    DeviceNotFoundError,
    FrameDecodeError,
    InferenceTimeoutError,
    KihaBaseError,
    StorageQuotaExceededError,
)

__all__ = [
    "ChatSessionError",
    "DeviceAuthenticationError",
    "DeviceNotFoundError",
    "FrameDecodeError",
    "InferenceTimeoutError",
    "KihaBaseError",
    "StorageQuotaExceededError",
]
