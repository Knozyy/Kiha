"""Kiha Server — Scene Memory (v2).

Her frame icin zengin sahne aciklamasi kaydeder.
Frame geldiginde VLM ile analiz edilir, sonuc indekslenir.
Kullanici soru sordugunuda kayitlarda aranir.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SceneSnapshot:
    """Tek bir frame'in zengin analiz sonucu."""

    frame_id: int
    timestamp: datetime
    device_id: str
    yolo_labels: list[str]          # ["person", "chair", "cup"]
    description: str                 # "Bir kisi kahverengi masanin yaninda oturuyor..."
    objects_detail: list[str]        # ["kirmizi kupa masanin ustunde", "anahtar kanepede"]

    def matches_query(self, query: str) -> float:
        """Basit keyword eslestirme skoru (0-1).
        Kullanici sorusundaki kelimeler aciklamada ne kadar geciyorsa o kadar yuksek skor."""
        query_words = query.lower().split()
        if not query_words:
            return 0.0

        searchable = f"{self.description} {' '.join(self.objects_detail)} {' '.join(self.yolo_labels)}".lower()

        matched = sum(1 for w in query_words if len(w) > 2 and w in searchable)
        return matched / len(query_words)


class SceneMemory:
    """Frame bazli sahne hafizasi.

    Her frame icin:
    - YOLO label listesi (hizli filtre)
    - VLM aciklamasi (zengin, dogal dil)
    - Nesne detaylari (renkler, konumlar, iliskiler)
    """

    def __init__(self, max_snapshots: int = 1000) -> None:
        # device_id -> list[SceneSnapshot] (kronolojik, yenisi sonda)
        self._snapshots: dict[str, list[SceneSnapshot]] = {}
        self._max_snapshots = max_snapshots

    def add_snapshot(self, snapshot: SceneSnapshot) -> None:
        """Yeni sahne kaydi ekle."""
        device_id = snapshot.device_id
        if device_id not in self._snapshots:
            self._snapshots[device_id] = []

        self._snapshots[device_id].append(snapshot)

        # FIFO — eski kayitlari sil
        if len(self._snapshots[device_id]) > self._max_snapshots:
            self._snapshots[device_id].pop(0)

        logger.info(
            "Snapshot #%d kaydedildi: %s — %d nesne",
            snapshot.frame_id,
            snapshot.description[:80],
            len(snapshot.yolo_labels),
        )

    def search(self, device_id: str, query: str, limit: int = 5) -> list[SceneSnapshot]:
        """Kullanici sorusuna en uygun snapshot'lari bul.

        En guncelden eskiye sirayla kontrol eder.
        Hem YOLO label hem de aciklama metni uzerinde arar.
        """
        snapshots = self._snapshots.get(device_id, [])
        if not snapshots:
            return []

        # Skor hesapla — en guncelden eskiye
        scored: list[tuple[float, SceneSnapshot]] = []
        for snap in reversed(snapshots):
            score = snap.matches_query(query)
            # Yeni kayitlara bonus (zamana gore azalan)
            recency_bonus = 0.1 if snap == snapshots[-1] else 0.0
            scored.append((score + recency_bonus, snap))

        # Skora gore sirala, esitlikte yeni olan once
        scored.sort(key=lambda x: x[0], reverse=True)

        # En az 0.1 skor olanlar
        results = [snap for score, snap in scored if score > 0.05]
        return results[:limit]

    def get_recent(self, device_id: str, limit: int = 10) -> list[SceneSnapshot]:
        """En son N snapshot'i getir (yeniden eskiye)."""
        snapshots = self._snapshots.get(device_id, [])
        return list(reversed(snapshots[-limit:]))

    def get_all_descriptions(self, device_id: str, limit: int = 20) -> str:
        """Son N snapshot'in aciklamalarini birlestir — LLM'e context olarak gonderilir."""
        recent = self.get_recent(device_id, limit)
        if not recent:
            return "Henuz kayit yok."

        lines = []
        for snap in recent:
            time_str = snap.timestamp.strftime("%H:%M:%S")
            lines.append(f"[{time_str} | Frame #{snap.frame_id}] {snap.description}")

        return "\n".join(lines)

    def get_snapshot_count(self, device_id: str) -> int:
        return len(self._snapshots.get(device_id, []))

    def clear_device(self, device_id: str) -> None:
        if device_id in self._snapshots:
            del self._snapshots[device_id]
