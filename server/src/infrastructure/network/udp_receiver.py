"""Kiha Server — UDP Frame Receiver (Placeholder)."""

import asyncio
import logging

from domain.models.base import Frame

logger = logging.getLogger(__name__)


class UdpReceiver:
    """Async UDP server that receives JPEG frames from ESP32 glasses.

    Handles the custom packet format:
    [frame_id: 4B] [timestamp: 4B] [fragment_info: 2B] [HMAC: 32B] [payload: variable]
    """

    HEADER_SIZE = 42  # 4 + 4 + 2 + 32 bytes

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._transport: asyncio.DatagramTransport | None = None

    async def start(self) -> None:
        """Start the UDP receiver server."""
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _FrameProtocol(self._on_frame_received),
            local_addr=(self._host, self._port),
        )
        logger.error("UDP receiver started on %s:%d", self._host, self._port)

    async def stop(self) -> None:
        """Stop the UDP receiver server."""
        if self._transport:
            self._transport.close()
            logger.error("UDP receiver stopped")

    async def _on_frame_received(self, frame: Frame) -> None:
        """Handle a received frame. Override in subclass or inject handler."""
        # TODO: Refactor - Push frame to ZeroMQ queue for processing
        logger.error("Frame received: id=%d", frame.frame_id)


class _FrameProtocol(asyncio.DatagramProtocol):
    """Low-level UDP datagram protocol for frame reception."""

    def __init__(
        self,
        callback: object,  # Using object to avoid complex callable typing
    ) -> None:
        self._callback = callback

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle incoming UDP datagram."""
        if len(data) < UdpReceiver.HEADER_SIZE:
            logger.error("Dropped undersized packet from %s", addr)
            return

        # TODO: Refactor - Parse header fields and verify HMAC
        logger.error("Datagram received from %s (%d bytes)", addr, len(data))
