"""Kiha Server — Device Status Routes."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/device", tags=["device"])


class DeviceStatusResponse(BaseModel):
    """Device status returned to the mobile app."""

    device_id: str
    name: str = "Kiha Glass v1"
    battery_level: int = Field(ge=0, le=100)
    is_connected: bool
    connection_quality: str
    firmware_version: str = "1.0.0"
    uptime_seconds: int = 0


@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(device_id: str) -> DeviceStatusResponse:
    """Get the current status of a Kiha Glass device.

    Returns battery level, connection quality, firmware version etc.
    """
    # TODO: Refactor - Wire up actual device registry
    return DeviceStatusResponse(
        device_id=device_id,
        name="Kiha Glass v1",
        battery_level=78,
        is_connected=True,
        connection_quality="stable",
        firmware_version="1.0.0",
        uptime_seconds=4980,
    )


@router.post("/{device_id}/pair")
async def pair_device(device_id: str) -> dict[str, str]:
    """Initiate device pairing process."""
    # TODO: Refactor - Implement PSK-based pairing
    return {"device_id": device_id, "status": "pairing_initiated"}
