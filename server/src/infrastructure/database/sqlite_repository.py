"""Kiha Server — SQLite Repository.

Kalici hafiza veritabani. Tum sahne kayitlarini,
nesne tespitlerini, iliskileri ve chat gecmisini saklar.

FTS5 ile Turkce tam metin arama destekler.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


# ── Veri siniflar ─────────────────────────────────────────────────────────────

@dataclass
class ObjectData:
    """Frame icerisinde tespit edilen tek bir nesne."""
    yolo_label: str
    confidence: float
    bbox_x_min: float
    bbox_y_min: float
    bbox_x_max: float
    bbox_y_max: float
    turkish_name: str = ""
    color: str = ""
    location_desc: str = ""
    material: str = ""
    state: str = ""


@dataclass
class SearchResult:
    """FTS5 veya SQL arama sonucu."""
    frame_id: int
    device_id: str
    captured_at: str
    vlm_description: str
    rank: float = 0.0
    jpeg_path: str = ""
    scene_type: str = ""
    yolo_labels: str = ""


@dataclass
class ObjectSighting:
    """Bir nesnenin belirli bir andaki gorunumu."""
    object_id: int
    yolo_label: str
    turkish_name: str
    color: str
    location_desc: str
    confidence: float
    detected_at: str
    frame_id: int
    jpeg_path: str
    scene_type: str
    vlm_description: str


# ── Schema DDL ────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Cihazlar
CREATE TABLE IF NOT EXISTS devices (
    device_id   TEXT PRIMARY KEY,
    name        TEXT DEFAULT 'Kiha Glass v1',
    created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    last_seen   TEXT
);

-- Frame metadata
CREATE TABLE IF NOT EXISTS frames (
    frame_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT NOT NULL REFERENCES devices(device_id),
    captured_at TEXT NOT NULL,
    jpeg_path   TEXT,
    width       INTEGER DEFAULT 640,
    height      INTEGER DEFAULT 480,
    jpeg_size   INTEGER
);
CREATE INDEX IF NOT EXISTS idx_frames_device_time ON frames(device_id, captured_at DESC);

-- Sahne analizi
CREATE TABLE IF NOT EXISTS scenes (
    scene_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id        INTEGER NOT NULL UNIQUE REFERENCES frames(frame_id),
    scene_type      TEXT,
    lighting        TEXT,
    vlm_description TEXT,
    yolo_labels     TEXT,
    inference_ms    REAL,
    analyzed_at     TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now'))
);
CREATE INDEX IF NOT EXISTS idx_scenes_frame ON scenes(frame_id);

-- Nesneler
CREATE TABLE IF NOT EXISTS objects (
    object_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id        INTEGER NOT NULL REFERENCES frames(frame_id),
    scene_id        INTEGER REFERENCES scenes(scene_id),
    yolo_label      TEXT NOT NULL,
    confidence      REAL NOT NULL,
    bbox_x_min      REAL,
    bbox_y_min      REAL,
    bbox_x_max      REAL,
    bbox_y_max      REAL,
    turkish_name    TEXT,
    color           TEXT,
    location_desc   TEXT,
    material        TEXT,
    state           TEXT,
    detected_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_objects_label ON objects(yolo_label, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_objects_turkish ON objects(turkish_name, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_objects_frame ON objects(frame_id);

-- Kisiler
CREATE TABLE IF NOT EXISTS people (
    person_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id   INTEGER NOT NULL UNIQUE REFERENCES objects(object_id),
    frame_id    INTEGER NOT NULL REFERENCES frames(frame_id),
    activity    TEXT,
    pose        TEXT,
    detected_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_people_frame ON people(frame_id);

-- Mekansal iliskiler
CREATE TABLE IF NOT EXISTS spatial_relations (
    relation_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id        INTEGER NOT NULL REFERENCES frames(frame_id),
    subject_id      INTEGER NOT NULL REFERENCES objects(object_id),
    predicate       TEXT NOT NULL,
    object_ref_id   INTEGER NOT NULL REFERENCES objects(object_id),
    confidence      REAL DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_relations_frame ON spatial_relations(frame_id);

-- Aktiviteler
CREATE TABLE IF NOT EXISTS activities (
    activity_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id       TEXT NOT NULL REFERENCES devices(device_id),
    start_frame_id  INTEGER NOT NULL REFERENCES frames(frame_id),
    end_frame_id    INTEGER,
    activity_type   TEXT NOT NULL,
    description     TEXT,
    started_at      TEXT NOT NULL,
    ended_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_activities_device ON activities(device_id, started_at DESC);

-- Chat
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id  TEXT PRIMARY KEY,
    device_id   TEXT NOT NULL,
    created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id  TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES chat_sessions(session_id),
    role        TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content     TEXT NOT NULL,
    referenced_frames TEXT,
    confidence  REAL,
    created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id, created_at);

-- FTS5 tam metin arama
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    frame_id UNINDEXED,
    device_id UNINDEXED,
    captured_at UNINDEXED,
    vlm_description,
    object_names,
    object_details,
    yolo_labels,
    content='',
    tokenize='unicode61 remove_diacritics 2'
);
"""


class KihaDatabase:
    """SQLite tabanli kalici hafiza sistemi.

    Tum sahne kayitlarini, nesne tespitlerini,
    mekansal iliskileri ve chat gecmisini yonetir.
    """

    def __init__(self, db_path: str, frames_dir: str) -> None:
        self._db_path = db_path
        self._frames_dir = frames_dir
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Veritabanina baglan ve schema olustur."""
        # Dizinleri olustur
        os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
        os.makedirs(self._frames_dir, exist_ok=True)

        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row

        # Performans ayarlari
        await self._db.execute("PRAGMA journal_mode = WAL")
        await self._db.execute("PRAGMA synchronous = NORMAL")
        await self._db.execute("PRAGMA cache_size = -64000")
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.execute("PRAGMA busy_timeout = 5000")

        # Schema olustur
        await self._db.executescript(SCHEMA_SQL)
        await self._db.commit()

        logger.info("KihaDatabase baglandi: %s", self._db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            logger.info("KihaDatabase kapatildi")

    # ── Cihaz ─────────────────────────────────────────────────────────────────

    async def ensure_device(self, device_id: str) -> None:
        """Cihaz yoksa olustur."""
        await self._db.execute(
            "INSERT OR IGNORE INTO devices (device_id) VALUES (?)",
            (device_id,),
        )
        await self._db.execute(
            "UPDATE devices SET last_seen = ? WHERE device_id = ?",
            (datetime.now().isoformat(), device_id),
        )
        await self._db.commit()

    # ── Frame kaydetme ────────────────────────────────────────────────────────

    async def save_frame(
        self,
        device_id: str,
        frame_bytes: bytes,
        captured_at: str | None = None,
        width: int = 640,
        height: int = 480,
    ) -> tuple[int, str]:
        """Frame'i diske yaz ve metadata'yi kaydet.

        Returns: (frame_id, jpeg_path)
        """
        await self.ensure_device(device_id)

        if not captured_at:
            captured_at = datetime.now().isoformat()

        # Once frame_id al
        cursor = await self._db.execute(
            """INSERT INTO frames (device_id, captured_at, width, height, jpeg_size)
               VALUES (?, ?, ?, ?, ?)""",
            (device_id, captured_at, width, height, len(frame_bytes)),
        )
        frame_id = cursor.lastrowid

        # JPEG'i diske yaz
        device_dir = os.path.join(self._frames_dir, device_id)
        os.makedirs(device_dir, exist_ok=True)
        jpeg_path = os.path.join(device_dir, f"{frame_id}.jpg")

        with open(jpeg_path, "wb") as f:
            f.write(frame_bytes)

        # Path'i guncelle
        await self._db.execute(
            "UPDATE frames SET jpeg_path = ? WHERE frame_id = ?",
            (jpeg_path, frame_id),
        )
        await self._db.commit()

        return frame_id, jpeg_path

    # ── Sahne analizi kaydetme ────────────────────────────────────────────────

    async def save_scene(
        self,
        frame_id: int,
        scene_type: str,
        vlm_description: str,
        yolo_labels: list[str],
        inference_ms: float = 0.0,
        lighting: str = "",
    ) -> int:
        """Sahne analizini kaydet. Returns: scene_id."""
        cursor = await self._db.execute(
            """INSERT INTO scenes (frame_id, scene_type, lighting, vlm_description, yolo_labels, inference_ms)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (frame_id, scene_type, lighting, vlm_description, json.dumps(yolo_labels), inference_ms),
        )
        await self._db.commit()
        return cursor.lastrowid

    # ── Nesne kaydetme ────────────────────────────────────────────────────────

    async def save_objects(
        self,
        frame_id: int,
        scene_id: int,
        objects: list[ObjectData],
        detected_at: str | None = None,
    ) -> list[int]:
        """Tespit edilen nesneleri toplu kaydet. Returns: object_id listesi."""
        if not detected_at:
            detected_at = datetime.now().isoformat()

        object_ids = []
        for obj in objects:
            cursor = await self._db.execute(
                """INSERT INTO objects
                   (frame_id, scene_id, yolo_label, confidence,
                    bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max,
                    turkish_name, color, location_desc, material, state, detected_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    frame_id, scene_id, obj.yolo_label, obj.confidence,
                    obj.bbox_x_min, obj.bbox_y_min, obj.bbox_x_max, obj.bbox_y_max,
                    obj.turkish_name, obj.color, obj.location_desc,
                    obj.material, obj.state, detected_at,
                ),
            )
            object_ids.append(cursor.lastrowid)

            # Kisi ise people tablosuna da ekle
            if obj.yolo_label == "person":
                await self._db.execute(
                    """INSERT INTO people (object_id, frame_id, detected_at)
                       VALUES (?, ?, ?)""",
                    (cursor.lastrowid, frame_id, detected_at),
                )

        await self._db.commit()
        return object_ids

    # ── Mekansal iliskiler ────────────────────────────────────────────────────

    async def save_relations(
        self,
        frame_id: int,
        relations: list[tuple[int, str, int]],
    ) -> None:
        """Mekansal iliskileri kaydet.
        relations: [(subject_object_id, predicate, object_ref_object_id), ...]
        """
        for subject_id, predicate, object_ref_id in relations:
            await self._db.execute(
                """INSERT INTO spatial_relations (frame_id, subject_id, predicate, object_ref_id)
                   VALUES (?, ?, ?, ?)""",
                (frame_id, subject_id, predicate, object_ref_id),
            )
        await self._db.commit()

    # ── FTS5 index guncelleme ─────────────────────────────────────────────────

    async def update_fts(
        self,
        frame_id: int,
        device_id: str,
        captured_at: str,
        vlm_description: str,
        objects: list[ObjectData],
        yolo_labels: list[str],
    ) -> None:
        """FTS5 indeksine sahne bilgilerini ekle."""
        object_names = " ".join(
            o.turkish_name for o in objects if o.turkish_name
        )
        object_details = " ".join(
            f"{o.color} {o.turkish_name} {o.location_desc}".strip()
            for o in objects if o.turkish_name
        )

        await self._db.execute(
            """INSERT INTO memory_fts
               (frame_id, device_id, captured_at, vlm_description, object_names, object_details, yolo_labels)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(frame_id), device_id, captured_at,
                vlm_description, object_names, object_details,
                " ".join(yolo_labels),
            ),
        )
        await self._db.commit()

    # ── Arama metodlari ──────────────────────────────────────────────────────

    async def search_by_text(
        self,
        device_id: str,
        query: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """FTS5 ile tam metin arama."""
        # FTS5 icin ozel karakterleri temizle
        clean_query = " ".join(
            w for w in query.split()
            if len(w) > 1 and w.isalpha()
        )
        if not clean_query:
            return []

        try:
            # OR ile birden fazla kelime ara
            fts_query = " OR ".join(clean_query.split())

            rows = await self._db.execute_fetchall(
                """SELECT frame_id, device_id, captured_at, vlm_description, rank
                   FROM memory_fts
                   WHERE memory_fts MATCH ? AND device_id = ?
                   ORDER BY rank
                   LIMIT ?""",
                (fts_query, device_id, limit),
            )

            results = []
            for row in rows:
                # Frame bilgilerini al
                frame_row = await self._db.execute_fetchall(
                    "SELECT jpeg_path FROM frames WHERE frame_id = ?",
                    (int(row[0]),),
                )
                jpeg_path = frame_row[0][0] if frame_row else ""

                scene_row = await self._db.execute_fetchall(
                    "SELECT scene_type, yolo_labels FROM scenes WHERE frame_id = ?",
                    (int(row[0]),),
                )
                scene_type = scene_row[0][0] if scene_row else ""
                yolo_labels = scene_row[0][1] if scene_row else ""

                results.append(SearchResult(
                    frame_id=int(row[0]),
                    device_id=row[1],
                    captured_at=row[2],
                    vlm_description=row[3] or "",
                    rank=row[4],
                    jpeg_path=jpeg_path,
                    scene_type=scene_type,
                    yolo_labels=yolo_labels,
                ))

            return results

        except Exception as exc:
            logger.error("FTS5 arama hatasi: %s", exc)
            return []

    async def find_object_last_seen(
        self,
        device_id: str,
        yolo_label: str,
    ) -> ObjectSighting | None:
        """Bir nesnenin en son goruldugu yeri bul."""
        rows = await self._db.execute_fetchall(
            """SELECT o.object_id, o.yolo_label, o.turkish_name, o.color,
                      o.location_desc, o.confidence, o.detected_at,
                      f.frame_id, f.jpeg_path,
                      s.scene_type, s.vlm_description
               FROM objects o
               JOIN frames f ON o.frame_id = f.frame_id
               LEFT JOIN scenes s ON o.scene_id = s.scene_id
               WHERE o.yolo_label = ? AND f.device_id = ?
               ORDER BY o.detected_at DESC
               LIMIT 1""",
            (yolo_label, device_id),
        )

        if not rows:
            return None

        r = rows[0]
        return ObjectSighting(
            object_id=r[0], yolo_label=r[1], turkish_name=r[2] or "",
            color=r[3] or "", location_desc=r[4] or "",
            confidence=r[5], detected_at=r[6],
            frame_id=r[7], jpeg_path=r[8] or "",
            scene_type=r[9] or "", vlm_description=r[10] or "",
        )

    async def get_recent_descriptions(
        self,
        device_id: str,
        limit: int = 15,
    ) -> str:
        """Son N sahne aciklamasini birlestir — VLM context icin."""
        rows = await self._db.execute_fetchall(
            """SELECT s.vlm_description, f.captured_at, f.frame_id
               FROM scenes s
               JOIN frames f ON s.frame_id = f.frame_id
               WHERE f.device_id = ?
               ORDER BY f.captured_at DESC
               LIMIT ?""",
            (device_id, limit),
        )

        if not rows:
            return "Henuz kayit yok."

        lines = []
        for row in rows:
            desc = row[0] or "Aciklama yok"
            time_str = row[1][:19] if row[1] else "?"
            frame_id = row[2]
            lines.append(f"[{time_str} | Frame #{frame_id}] {desc}")

        return "\n".join(lines)

    async def get_snapshot_count(self, device_id: str) -> int:
        """Bir cihazin toplam sahne sayisi."""
        rows = await self._db.execute_fetchall(
            """SELECT COUNT(*) FROM scenes s
               JOIN frames f ON s.frame_id = f.frame_id
               WHERE f.device_id = ?""",
            (device_id,),
        )
        return rows[0][0] if rows else 0

    # ── Frame okuma ───────────────────────────────────────────────────────────

    async def get_frame_jpeg_bytes(self, frame_id: int) -> bytes | None:
        """Frame JPEG bytes'ini diskten oku."""
        rows = await self._db.execute_fetchall(
            "SELECT jpeg_path FROM frames WHERE frame_id = ?",
            (frame_id,),
        )
        if not rows or not rows[0][0]:
            return None

        jpeg_path = rows[0][0]
        if not os.path.exists(jpeg_path):
            return None

        with open(jpeg_path, "rb") as f:
            return f.read()

    async def get_frame_jpeg_path(self, frame_id: int) -> str | None:
        rows = await self._db.execute_fetchall(
            "SELECT jpeg_path FROM frames WHERE frame_id = ?",
            (frame_id,),
        )
        return rows[0][0] if rows and rows[0][0] else None

    # ── Chat gecmisi ──────────────────────────────────────────────────────────

    async def save_chat_message(
        self,
        session_id: str,
        device_id: str,
        message_id: str,
        role: str,
        content: str,
        referenced_frames: list[int] | None = None,
        confidence: float | None = None,
    ) -> None:
        # Session yoksa olustur
        await self._db.execute(
            "INSERT OR IGNORE INTO chat_sessions (session_id, device_id) VALUES (?, ?)",
            (session_id, device_id),
        )
        await self._db.execute(
            """INSERT INTO chat_messages
               (message_id, session_id, role, content, referenced_frames, confidence)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                message_id, session_id, role, content,
                json.dumps(referenced_frames or []),
                confidence,
            ),
        )
        await self._db.commit()

    # ── Temizlik ──────────────────────────────────────────────────────────────

    async def cleanup_old_frames(self, keep_days: int = 7) -> int:
        """Eski frame ve iliskili verileri sil."""
        cutoff = datetime.now().isoformat()[:10]  # basitlestirilmis
        # TODO: implement full cleanup with date arithmetic
        return 0
