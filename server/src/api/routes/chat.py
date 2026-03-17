"""Kiha Server — Chat Routes (v3 — SQLite).

Mimari:
1. Frame gelir → YOLOv8 + VLM analiz → SQLite'a zengin kayit
2. Soru gelir → FTS5 arama → VLM cevap → fotograf + metin don
"""

import base64
import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field

from domain.models.base import Frame
from infrastructure.ai.inference_engine import YoloInferenceEngine
from infrastructure.ai.vlm_output_parser import parse_vlm_output, YOLO_TO_TURKISH
from infrastructure.database.sqlite_repository import KihaDatabase, ObjectData
from infrastructure.network.websocket_handler import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# ── Singletons ────────────────────────────────────────────────────────────────
_yolo_engine: YoloInferenceEngine | None = None
_vlm_service = None
_ws_manager = ConnectionManager()

# Sahne degisiklik takibi
_last_yolo_labels: dict[str, set[str]] = {}
_last_vlm_call: dict[str, float] = {}
_VLM_MIN_INTERVAL = 3.0


def _get_yolo() -> YoloInferenceEngine:
    global _yolo_engine
    if _yolo_engine is None:
        _yolo_engine = YoloInferenceEngine(model_path="yolov8n.pt", device="cpu")
    return _yolo_engine


def _get_vlm():
    """VLM servisini dondur. Oncelik: Groq > Gemini > Ollama."""
    global _vlm_service
    if _vlm_service is None:
        from config.settings import get_settings
        settings = get_settings()

        if settings.groq_api_key:
            try:
                from infrastructure.ai.groq_vision import GroqVisionService
                _vlm_service = GroqVisionService(api_key=settings.groq_api_key)
                logger.info("VLM: Groq initialized")
                return _vlm_service
            except Exception as exc:
                logger.error("Groq init failed: %s", exc)

        if settings.gemini_api_key:
            try:
                from infrastructure.ai.gemini_vision import GeminiVisionService
                _vlm_service = GeminiVisionService(api_key=settings.gemini_api_key)
                logger.info("VLM: Gemini initialized")
                return _vlm_service
            except Exception as exc:
                logger.error("Gemini init failed: %s", exc)

        try:
            from infrastructure.ai.ollama_vision import OllamaVisionService
            _vlm_service = OllamaVisionService(
                model=settings.ollama_model,
                base_url=settings.ollama_url,
            )
            logger.info("VLM: Ollama initialized")
        except Exception as exc:
            logger.error("VLM: Hicbir servis baslatilamadi: %s", exc)
    return _vlm_service


def _get_db(request: Request) -> KihaDatabase:
    """Request'ten DB instance al."""
    return request.app.state.db


# ── Request / Response ────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    device_id: str
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    content: str
    referenced_frames: list[int] = Field(default_factory=list)
    confidence: float | None = None
    frame_thumbnail_b64: str | None = None


# ── Proaktif Sahne Analizi ────────────────────────────────────────────────────
async def _analyze_and_store(
    db: KihaDatabase,
    device_id: str,
    frame_id: int,
    frame_bytes: bytes,
    yolo_labels: list[str],
    detections: list,
    inference_ms: float,
) -> None:
    """Frame'i VLM ile analiz et, sonuclari SQLite'a kaydet."""

    current_labels = set(yolo_labels)
    prev_labels = _last_yolo_labels.get(device_id, set())
    last_call = _last_vlm_call.get(device_id, 0)
    now = time.time()

    scene_changed = current_labels != prev_labels
    enough_time = (now - last_call) >= _VLM_MIN_INTERVAL

    captured_at = datetime.now().isoformat()
    vlm = _get_vlm()

    # VLM analizi gerekli mi?
    vlm_description = ""
    parsed_objects: list[ObjectData] = []

    if vlm and (scene_changed or enough_time):
        try:
            vlm_description = await vlm.ask_about_image(
                image_bytes=frame_bytes,
                question=(
                    "Bu goruntudeki sahneyi analiz et. "
                    "Her nesnenin rengini, konumunu ve yakinindaki diger nesneleri belirt. "
                    "Turkce yaz, kisa ve net ol. Ornek format:\n"
                    "- Kirmizi anahtar kahverengi masanin ustunde\n"
                    "- Siyah telefon kanepanin sol kosesinde\n"
                    "Sadece gorduklerini listele."
                ),
            )
            _last_yolo_labels[device_id] = current_labels
            _last_vlm_call[device_id] = now
            logger.info("Frame #%d VLM analizi: %s", frame_id, vlm_description[:100])

        except Exception as exc:
            logger.error("VLM analiz hatasi frame #%d: %s", frame_id, exc)
            vlm_description = f"Sahnede: {', '.join(yolo_labels)}"
    else:
        vlm_description = f"Sahnede: {', '.join(yolo_labels) if yolo_labels else 'bos'}"

    # VLM ciktisini parse et
    parsed = parse_vlm_output(vlm_description, yolo_labels)

    # Sahneyi kaydet
    scene_id = await db.save_scene(
        frame_id=frame_id,
        scene_type=parsed.scene_type,
        vlm_description=parsed.description,
        yolo_labels=yolo_labels,
        inference_ms=inference_ms,
    )

    # Nesneleri kaydet — YOLO detection + VLM zenginlestirme
    objects_to_save: list[ObjectData] = []

    for det in detections:
        bbox = det.bbox
        tr_name = YOLO_TO_TURKISH.get(det.label, det.label)

        # VLM'den gelen zengin bilgiyi bul
        color = ""
        location_desc = ""
        for pobj in parsed.objects:
            if pobj.yolo_label == det.label or pobj.turkish_name == tr_name:
                color = pobj.color
                location_desc = pobj.location_desc
                break

        objects_to_save.append(ObjectData(
            yolo_label=det.label,
            confidence=det.confidence,
            bbox_x_min=bbox.x_min,
            bbox_y_min=bbox.y_min,
            bbox_x_max=bbox.x_max,
            bbox_y_max=bbox.y_max,
            turkish_name=tr_name,
            color=color,
            location_desc=location_desc,
        ))

    if objects_to_save:
        await db.save_objects(frame_id, scene_id, objects_to_save, captured_at)

    # FTS5 indeksini guncelle
    await db.update_fts(
        frame_id=frame_id,
        device_id=device_id,
        captured_at=captured_at,
        vlm_description=parsed.description,
        objects=objects_to_save,
        yolo_labels=yolo_labels,
    )


# ── Akilli Soru Cevaplama ─────────────────────────────────────────────────────
async def _build_response(
    db: KihaDatabase,
    session_id: str,
    device_id: str,
    message: str,
) -> ChatResponse:
    """Kullanici sorusunu DB'de ara, VLM ile cevapla."""

    snapshot_count = await db.get_snapshot_count(device_id)
    if snapshot_count == 0:
        return ChatResponse(
            session_id=session_id,
            message_id=f"msg_{session_id}_empty",
            content="Henuz kayit yok. Once kamerayi acip kayit yapin, sonra soru sorun.",
            referenced_frames=[],
            confidence=0.0,
        )

    # 1. FTS5 ile ara
    results = await db.search_by_text(device_id, message, limit=5)

    # 2. Sonuc yoksa YOLO label ile dene
    if not results:
        from infrastructure.ai.query_parser import QueryParser
        parser = QueryParser()
        parsed = parser.parse(message)
        for label in parsed.target_labels:
            sighting = await db.find_object_last_seen(device_id, label)
            if sighting:
                frame_bytes = await db.get_frame_jpeg_bytes(sighting.frame_id)
                thumbnail_b64 = base64.b64encode(frame_bytes).decode() if frame_bytes else None

                content = (
                    f"{sighting.turkish_name or sighting.yolo_label}"
                    f"{' (' + sighting.color + ')' if sighting.color else ''}"
                    f" en son {sighting.detected_at[:19]} tarihinde goruldu."
                    f"{' Konum: ' + sighting.location_desc if sighting.location_desc else ''}"
                )

                return ChatResponse(
                    session_id=session_id,
                    message_id=f"msg_{session_id}_label",
                    content=content,
                    referenced_frames=[sighting.frame_id],
                    confidence=sighting.confidence,
                    frame_thumbnail_b64=thumbnail_b64,
                )

    # 3. Context olustur
    context = await db.get_recent_descriptions(device_id, limit=15)

    # 4. En iyi sonucun fotografini al
    best_frame_id = results[0].frame_id if results else None
    thumbnail_b64: str | None = None
    frame_bytes: bytes | None = None

    if best_frame_id:
        frame_bytes = await db.get_frame_jpeg_bytes(best_frame_id)
        if frame_bytes:
            thumbnail_b64 = base64.b64encode(frame_bytes).decode()

    # Hicbir sonuc yoksa en son frame'i al
    if not frame_bytes:
        rows = await db._db.execute_fetchall(
            "SELECT frame_id FROM frames WHERE device_id = ? ORDER BY captured_at DESC LIMIT 1",
            (device_id,),
        )
        if rows:
            latest_id = rows[0][0]
            frame_bytes = await db.get_frame_jpeg_bytes(latest_id)
            if frame_bytes:
                thumbnail_b64 = base64.b64encode(frame_bytes).decode()
                best_frame_id = latest_id

    frame_ids = [r.frame_id for r in results] if results else ([best_frame_id] if best_frame_id else [])

    # 5. VLM ile cevapla
    vlm = _get_vlm()
    if vlm and frame_bytes:
        try:
            answer = await vlm.ask_about_image(
                image_bytes=frame_bytes,
                question=(
                    f"Kullanici soruyor: \"{message}\"\n\n"
                    f"Son kayitlar:\n{context}\n\n"
                    f"Bu bilgilere ve gorsele dayanarak kullanicinin sorusunu Turkce cevapla. "
                    f"Kisa, net ve yardimci ol. 1-2 cumle yeterli. "
                    f"Eger cevabi bilmiyorsan 'Bu bilgiye kayitlarda rastlamadim' de."
                ),
            )
            content = answer.strip()
        except Exception as exc:
            logger.error("Cevap VLM hatasi: %s", exc)
            content = _fallback_from_results(results)
    elif vlm and not frame_bytes:
        # Frame yok ama context var
        try:
            answer = await vlm.ask_about_image(
                image_bytes=b"",
                question=(
                    f"Kullanici soruyor: \"{message}\"\n\n"
                    f"Son kayitlar:\n{context}\n\n"
                    f"Bu kayitlara dayanarak cevapla. Turkce, kisa ve net."
                ),
            )
            content = answer.strip()
        except Exception:
            content = _fallback_from_results(results)
    else:
        content = _fallback_from_results(results)

    return ChatResponse(
        session_id=session_id,
        message_id=f"msg_{session_id}_{snapshot_count}",
        content=content,
        referenced_frames=frame_ids,
        confidence=0.8 if results else 0.3,
        frame_thumbnail_b64=thumbnail_b64,
    )


def _fallback_from_results(results: list) -> str:
    """VLM calismadigi durumda sonuclardan cevap olustur."""
    if not results:
        return "Bu konuda kayitlarda bir bilgi bulunamadi."
    best = results[0]
    return f"En ilgili kayit: {best.vlm_description}"


# ── REST Endpoints ────────────────────────────────────────────────────────────

@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest, raw_request: Request) -> ChatResponse:
    db = _get_db(raw_request)
    return await _build_response(db, request.session_id, request.device_id, request.message)


@router.post("/frame/{device_id}")
async def ingest_frame(device_id: str, raw_request: Request) -> dict:
    """Frame al, YOLOv8 + VLM analiz et, SQLite'a kaydet."""
    db = _get_db(raw_request)
    frame_bytes = await raw_request.body()
    if not frame_bytes:
        return {"status": "error", "message": "Empty body"}

    # YOLOv8
    engine = _get_yolo()
    frame = Frame(
        frame_id=0,  # gecici, DB autoincrement verecek
        timestamp=datetime.now(),
        device_id=device_id,
        data=frame_bytes,
    )

    try:
        result = await engine.run_inference(frame)
    except Exception as exc:
        logger.error("YOLO hatasi: %s", exc)
        return {"status": "error", "message": str(exc)}

    labels = [d.label for d in result.detections]

    # Frame'i SQLite + diske kaydet
    frame_id, jpeg_path = await db.save_frame(device_id, frame_bytes)

    # Proaktif VLM analizi + DB kayit
    await _analyze_and_store(
        db=db,
        device_id=device_id,
        frame_id=frame_id,
        frame_bytes=frame_bytes,
        yolo_labels=labels,
        detections=result.detections,
        inference_ms=result.inference_time_ms,
    )

    logger.info("Frame #%d: %s → %s", frame_id, labels, jpeg_path)

    return {
        "status": "ok",
        "frame_id": frame_id,
        "detections": len(result.detections),
        "labels": labels,
        "inference_ms": result.inference_time_ms,
    }


@router.get("/frames/{frame_id}")
async def get_frame(frame_id: int, raw_request: Request) -> Response:
    db = _get_db(raw_request)
    frame_bytes = await db.get_frame_jpeg_bytes(frame_id)
    if frame_bytes is None:
        raise HTTPException(status_code=404, detail="Frame not found")
    return Response(content=frame_bytes, media_type="image/jpeg")


@router.get("/memory/{device_id}")
async def get_memory(device_id: str, raw_request: Request) -> dict:
    """Debug: DB'deki tum sahne kayitlarini gor."""
    db = _get_db(raw_request)
    desc = await db.get_recent_descriptions(device_id, limit=20)
    count = await db.get_snapshot_count(device_id)
    return {
        "device_id": device_id,
        "total_snapshots": count,
        "descriptions": desc,
    }


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
    await _ws_manager.connect(client_id, websocket)
    db = websocket.app.state.db
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

            resp = await _build_response(db, session_id, device_id, message)
            await _ws_manager.send_to_client(client_id, resp.model_dump_json())

    except WebSocketDisconnect:
        _ws_manager.disconnect(client_id)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, str]:
    return {"session_id": session_id, "status": "ok"}
