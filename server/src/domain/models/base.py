"""Kiha Server — Domain Data Models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DeviceStatus(StrEnum):
    """Connection status of a Kiha Glass device."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PAIRING = "pairing"


class ConnectionQuality(StrEnum):
    """Quality level of the device connection."""

    STABLE = "stable"
    WEAK = "weak"
    CRITICAL = "critical"


class Frame(BaseModel):
    """A single video frame received from the glasses."""

    frame_id: int = Field(description="Unique frame identifier")
    timestamp: datetime = Field(description="Frame capture timestamp")
    device_id: str = Field(description="Source device identifier")
    data: bytes = Field(description="JPEG-encoded frame data")
    width: int = Field(default=640, description="Frame width in pixels")
    height: int = Field(default=480, description="Frame height in pixels")


class InferenceResult(BaseModel):
    """Result of AI inference on a single frame."""

    frame_id: int = Field(description="Processed frame identifier")
    timestamp: datetime = Field(description="Inference completion timestamp")
    detections: list["Detection"] = Field(default_factory=list)
    inference_time_ms: float = Field(description="Inference duration in milliseconds")


class Detection(BaseModel):
    """A single object detection within a frame."""

    label: str = Field(description="Detected object class name")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence score")
    bbox: "BoundingBox" = Field(description="Bounding box coordinates")


class BoundingBox(BaseModel):
    """Bounding box for a detected object (normalized 0-1)."""

    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)


class DeviceInfo(BaseModel):
    """Smart glasses device information."""

    device_id: str = Field(description="Unique device identifier")
    name: str = Field(default="Kiha Glass v1")
    firmware_version: str = Field(default="1.0.0")
    battery_level: int = Field(ge=0, le=100, description="Battery percentage")
    status: DeviceStatus = Field(default=DeviceStatus.DISCONNECTED)
    connection_quality: ConnectionQuality = Field(default=ConnectionQuality.STABLE)
    uptime_seconds: int = Field(default=0, description="Active time in seconds")
    last_seen: datetime | None = Field(default=None)


class ChatMessage(BaseModel):
    """A single message in the chat conversation."""

    id: str = Field(description="Unique message identifier")
    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message text content")
    timestamp: datetime = Field(default_factory=datetime.now)
    referenced_frames: list[int] = Field(
        default_factory=list,
        description="Frame IDs referenced in the AI response",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="AI confidence score for the response",
    )


class ChatSession(BaseModel):
    """A chat session between the user and the AI."""

    session_id: str = Field(description="Unique session identifier")
    device_id: str = Field(description="Associated device identifier")
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
