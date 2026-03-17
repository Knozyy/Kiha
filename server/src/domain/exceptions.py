"""Kiha Server — Domain Exceptions."""


class KihaBaseError(Exception):
    """Base exception for all Kiha domain errors."""

    def __init__(self, message: str, code: str = "KIHA_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class FrameDecodeError(KihaBaseError):
    """Raised when a received frame cannot be decoded."""

    def __init__(self, message: str = "Frame could not be decoded") -> None:
        super().__init__(message=message, code="FRAME_DECODE_ERROR")


class InferenceTimeoutError(KihaBaseError):
    """Raised when AI inference exceeds the time limit."""

    def __init__(self, message: str = "Inference timed out") -> None:
        super().__init__(message=message, code="INFERENCE_TIMEOUT")


class DeviceAuthenticationError(KihaBaseError):
    """Raised when device PSK authentication fails."""

    def __init__(self, message: str = "Device authentication failed") -> None:
        super().__init__(message=message, code="DEVICE_AUTH_ERROR")


class DeviceNotFoundError(KihaBaseError):
    """Raised when a device is not found in the registry."""

    def __init__(self, device_id: str) -> None:
        super().__init__(
            message=f"Device not found: {device_id}",
            code="DEVICE_NOT_FOUND",
        )


class ChatSessionError(KihaBaseError):
    """Raised when a chat session encounters an error."""

    def __init__(self, message: str = "Chat session error") -> None:
        super().__init__(message=message, code="CHAT_SESSION_ERROR")


class StorageQuotaExceededError(KihaBaseError):
    """Raised when frame storage quota is exceeded."""

    def __init__(self, message: str = "Storage quota exceeded") -> None:
        super().__init__(message=message, code="STORAGE_QUOTA_EXCEEDED")
