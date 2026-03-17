"""Kiha Server — Chat Routes."""

import base64
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field

from domain.models.base import Frame
from infrastructure.ai.frame_search_service import FrameSearchService
from infrastructure.ai.inference_engine import YoloInferenceEngine
from infrastructure.ai.scene_memory import SceneMemory
from infrastructure.network.websocket_handler import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# ── Module-level singletons ───────────────────────────────────────────────────
_scene_memory = SceneMemory()
_frame_store: dict[int, bytes] = {}   # frame_id → JPEG bytes
_yolo_engine: YoloInferenceEngine | None = None
_vlm_service = None
_ws_manager = ConnectionManager()
_frame_counter = 0
_MAX_STORED_FRAMES = 500


def _get_yolo() -> YoloInferenceEngine:
    global _yolo_engine
    if _yolo_engine is None:
        _yolo_engine = YoloInferenceEngine(model_path="yolov8n.pt", device="cpu")
    return _yolo_engine


def _get_vlm():
    """VLM servisini döndür.

    Öncelik sırası:
    1. Ollama (yerel, OLLAMA_URL tanımlıysa veya varsayılan port'ta çalışıyorsa)
    2. Gemini (GEMINI_API_KEY varsa)
    3. None (yedek mod: koordinat + bağlam yanıtı)
    """
    global _vlm_service
    if _vlm_service is None:
        # 1. Ollama (tercihli)
        try:
            from infrastructure.ai.ollama_vision import OllamaVisionService
            ollama_url   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
            ollama_model = os.getenv("OLLAMA_MODEL", "llava:7b")
            _vlm_service = OllamaVisionService(model=ollama_model, base_url=ollama_url)
            return _vlm_service
        except Exception as exc:
            logger.error("Ollama init failed: %s", exc)

        # 2. Gemini yedek
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            try:
                from infrastructure.ai.gemini_vision import GeminiVisionService
                _vlm_service = GeminiVisionService(api_key=api_key)
            except Exception as exc:
                logger.error("Gemini init failed: %s", exc)
    return _vlm_service


def _get_search() -> FrameSearchService:
    return FrameSearchService(scene_memory=_scene_memory)


# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """Incoming chat request from the mobile app."""

    session_id: str = Field(description="Chat session identifier")
    device_id: str = Field(description="Associated glasses device ID")
    message: str = Field(min_length=1, max_length=1000, description="User question")


class ChatResponse(BaseModel):
    """Chat response returned to the mobile app."""

    session_id: str
    message_id: str
    content: str
    referenced_frames: list[int] = Field(default_factory=list)
    confidence: float | None = None
    frame_thumbnail_b64: str | None = None   # base64 JPEG of most relevant frame


# ── Core pipeline helper ──────────────────────────────────────────────────────
async def _build_response(
    session_id: str,
    device_id: str,
    message: str,
) -> ChatResponse:
    """Parse question → search SceneMemory → VLM location → ChatResponse."""
    search_svc = _get_search()
    result = search_svc.search_with_context(device_id=device_id, query=message)

    # Resolve thumbnail for the most recent matching frame
    thumbnail_b64: str | None = None
    frame_bytes: bytes | None = None
    if result.found and result.last_sighting:
        frame_bytes = _frame_store.get(result.last_sighting.frame_id)
        if frame_bytes:
            thumbnail_b64 = base64.b64encode(frame_bytes).decode()

    # Generate natural-language response
    if result.found and result.last_sighting and frame_bytes:
        vlm = _get_vlm()
        if vlm:
            label = result.last_sighting.label
            time_str = FrameSearchService._format_time(result.last_sighting.timestamp)
            try:
                vlm_answer = await vlm.ask_about_image(
                    image_bytes=frame_bytes,
                    question=(
                        f"Bu fotoğrafta '{label}' nerede? "
                        f"Sadece 1 kısa cümleyle konum ve renk söyle. "
                        f"Örnek format: 'Kişi odanın ortasında, beyaz duvarın önünde duruyor.' "
                        f"Başka hiçbir şey yazma, sadece o 1 cümleyi yaz."
                    ),
                )
                content = f"🔍 {vlm_answer}\n(En son görülme: {time_str})"
            except Exception as exc:
                logger.error("VLM error: %s", exc)
                content = search_svc.generate_response_text(message, device_id)
        else:
            content = search_svc.generate_response_text(message, device_id)
    else:
        content = search_svc.generate_response_text(message, device_id)

    return ChatResponse(
        session_id=session_id,
        message_id=f"msg_{session_id}_{len(result.frame_ids)}",
        content=content,
        referenced_frames=result.frame_ids,
        confidence=0.85 if result.found else 0.2,
        frame_thumbnail_b64=thumbnail_b64,
    )


# ── REST endpoints ────────────────────────────────────────────────────────────
@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest) -> ChatResponse:
    """Ask the AI a question about recorded footage.

    Examples:
    - 'Anahtarlarımı nereye koydum?'
    - 'Ocağın altını kapattım mı?'
    - 'Telefonumu en son nerede gördüm?'
    """
    return await _build_response(
        session_id=request.session_id,
        device_id=request.device_id,
        message=request.message,
    )


@router.post("/frame/{device_id}")
async def ingest_frame(device_id: str, raw_request: Request) -> dict:
    """Receive a raw JPEG frame, run YOLOv8, store results.

    Content-Type: image/jpeg
    Body: raw JPEG bytes
    """
    global _frame_counter

    frame_bytes = await raw_request.body()
    if not frame_bytes:
        return {"status": "error", "message": "Empty body"}

    _frame_counter += 1
    frame_id = _frame_counter

    engine = _get_yolo()
    frame = Frame(
        frame_id=frame_id,
        timestamp=datetime.now(),
        device_id=device_id,
        data=frame_bytes,
    )

    try:
        result = await engine.run_inference(frame)
    except Exception as exc:
        logger.error("Inference error frame %d: %s", frame_id, exc)
        return {"status": "error", "frame_id": frame_id, "message": str(exc)}

    _scene_memory.add_inference_result(device_id, result)

    # Store frame bytes (bounded FIFO)
    _frame_store[frame_id] = frame_bytes
    if len(_frame_store) > _MAX_STORED_FRAMES:
        oldest = next(iter(_frame_store))
        del _frame_store[oldest]

    labels = [d.label for d in result.detections]
    logger.error(
        "Frame %d ingested for device '%s': %s",
        frame_id, device_id, labels,
    )

    return {
        "status": "ok",
        "frame_id": frame_id,
        "detections": len(result.detections),
        "labels": labels,
        "inference_ms": result.inference_time_ms,
    }


@router.get("/frames/{frame_id}")
async def get_frame(frame_id: int) -> Response:
    """Return JPEG bytes for a stored frame by ID."""
    frame_bytes = _frame_store.get(frame_id)
    if frame_bytes is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frame not found")
    return Response(content=frame_bytes, media_type="image/jpeg")


# ── WebSocket endpoint ────────────────────────────────────────────────────────
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
    """WebSocket endpoint for real-time chat.

    Expected message format (JSON):
    {
        "message": "Anahtarım nerede?",
        "device_id": "glasses_01",
        "session_id": "optional_session_id"
    }

    Response format (JSON):
    {
        "session_id": "...",
        "message_id": "...",
        "content": "Anahtar kırmızı masanın üstünde...",
        "referenced_frames": [42, 38],
        "confidence": 0.85,
        "frame_thumbnail_b64": "<base64 jpeg or null>"
    }
    """
    await _ws_manager.connect(client_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                message = data.get("message", "")
                device_id = data.get("device_id", "default")
                session_id = data.get("session_id", client_id)
            except (json.JSONDecodeError, KeyError):
                message = raw
                device_id = "default"
                session_id = client_id

            if not message.strip():
                continue

            resp = await _build_response(session_id, device_id, message)
            await _ws_manager.send_to_client(client_id, resp.model_dump_json())

    except WebSocketDisconnect:
        _ws_manager.disconnect(client_id)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, str]:
    """Retrieve a chat session by ID."""
    return {"session_id": session_id, "status": "ok"}
