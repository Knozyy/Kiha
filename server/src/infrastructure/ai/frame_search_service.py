"""Kiha Server — Frame Search Service.

Implements FrameSearchProtocol using SceneMemory and QueryParser.
Bridges the user's Turkish questions to stored object detections.
"""

import logging
from datetime import datetime

from domain.services.chat_service import FrameSearchProtocol
from infrastructure.ai.query_parser import QueryParser
from infrastructure.ai.scene_memory import SceneMemory, SceneRecord

logger = logging.getLogger(__name__)


class FrameSearchResult:
    """Enriched search result with context for response generation."""

    def __init__(
        self,
        frame_ids: list[int],
        records: list[SceneRecord],
        query_type: str,
        matched_labels: list[str],
    ) -> None:
        self.frame_ids = frame_ids
        self.records = records
        self.query_type = query_type
        self.matched_labels = matched_labels

    @property
    def found(self) -> bool:
        """Whether any results were found."""
        return len(self.records) > 0

    @property
    def last_sighting(self) -> SceneRecord | None:
        """Most recent matching record."""
        if self.records:
            return self.records[0]
        return None


class FrameSearchService:
    """Search through recorded frames using natural language queries.

    Implements FrameSearchProtocol for integration with ChatService.

    Pipeline:
    1. Parse Turkish query → YOLO labels (QueryParser)
    2. Search SceneMemory for matching detections
    3. Return matching frame IDs with context
    """

    def __init__(
        self,
        scene_memory: SceneMemory,
        query_parser: QueryParser | None = None,
    ) -> None:
        self._scene_memory = scene_memory
        self._query_parser = query_parser or QueryParser()

    async def search_frames(
        self,
        device_id: str,
        query: str,
    ) -> list[int]:
        """Search frames by natural language query.

        Implements FrameSearchProtocol.
        Returns a list of matching frame IDs (most recent first).
        """
        result = self.search_with_context(device_id, query)
        return result.frame_ids

    def search_with_context(
        self,
        device_id: str,
        query: str,
        limit: int = 10,
    ) -> FrameSearchResult:
        """Search with full context (for richer response generation).

        Returns FrameSearchResult with records, matched labels, etc.
        """
        parsed = self._query_parser.parse(query)

        logger.error(
            "Query parsed: '%s' → labels=%s, type=%s",
            query,
            parsed.target_labels,
            parsed.query_type,
        )

        all_records: list[SceneRecord] = []

        for label in parsed.target_labels:
            records = self._scene_memory.search_by_object(
                device_id=device_id,
                label=label,
                limit=limit,
            )
            all_records.extend(records)

        # Deduplicate and sort by timestamp (most recent first)
        seen_frames: set[int] = set()
        unique_records: list[SceneRecord] = []
        for record in sorted(all_records, key=lambda r: r.timestamp, reverse=True):
            if record.frame_id not in seen_frames:
                seen_frames.add(record.frame_id)
                unique_records.append(record)

        frame_ids = [r.frame_id for r in unique_records[:limit]]

        logger.error(
            "Search result: %d frames found for query '%s'",
            len(frame_ids),
            query,
        )

        return FrameSearchResult(
            frame_ids=frame_ids,
            records=unique_records[:limit],
            query_type=parsed.query_type,
            matched_labels=parsed.target_labels,
        )

    def generate_response_text(
        self,
        query: str,
        device_id: str,
    ) -> str:
        """Generate a Turkish natural language response for the query.

        Combines search results with response templates.
        """
        result = self.search_with_context(device_id, query)
        parsed = self._query_parser.parse(query)

        if not result.found:
            return self._no_result_response(parsed.target_labels)

        last = result.last_sighting
        if last is None:
            return self._no_result_response(parsed.target_labels)

        # Build response based on query type
        if parsed.query_type == "location":
            return self._location_response(last, result)
        elif parsed.query_type == "action_check":
            return self._action_check_response(last, result)
        elif parsed.query_type == "time":
            return self._time_response(last, result)
        else:
            return self._general_response(last, result)

    def _location_response(
        self,
        last: SceneRecord,
        result: FrameSearchResult,
    ) -> str:
        """Build location-based response."""
        position = self._describe_position(last.x_center, last.y_center)
        time_str = self._format_time(last.timestamp)
        confidence_pct = int(last.confidence * 100)

        return (
            f"🔍 '{last.label}' en son {time_str} tarihinde "
            f"görüntünün {position} kısmında tespit edildi. "
            f"(Güven: %{confidence_pct}) "
            f"Toplam {len(result.records)} kayıt bulundu."
        )

    def _action_check_response(
        self,
        last: SceneRecord,
        result: FrameSearchResult,
    ) -> str:
        """Build action check response (e.g., 'Did I turn off the stove?')."""
        time_str = self._format_time(last.timestamp)

        return (
            f"⚠️ '{last.label}' en son {time_str} tarihinde tespit edildi. "
            f"Kare ID: {last.frame_id}. "
            f"Bu nesne görünür durumda — lütfen kontrol edin."
        )

    def _time_response(
        self,
        last: SceneRecord,
        result: FrameSearchResult,
    ) -> str:
        """Build time-based response."""
        time_str = self._format_time(last.timestamp)

        if result.records and len(result.records) > 1:
            first = result.records[-1]
            first_time = self._format_time(first.timestamp)
            return (
                f"🕐 '{last.label}' ilk olarak {first_time} ve "
                f"en son {time_str} tarihinde görüldü. "
                f"Toplam {len(result.records)} kez tespit edildi."
            )

        return (
            f"🕐 '{last.label}' en son {time_str} tarihinde görüldü."
        )

    def _general_response(
        self,
        last: SceneRecord,
        result: FrameSearchResult,
    ) -> str:
        """Build general response."""
        time_str = self._format_time(last.timestamp)
        position = self._describe_position(last.x_center, last.y_center)

        return (
            f"'{last.label}' ile ilgili {len(result.records)} kayıt bulundu. "
            f"En son {time_str} tarihinde görüntünün {position} kısmında "
            f"tespit edildi."
        )

    def _no_result_response(self, labels: list[str]) -> str:
        """Response when no results found."""
        if labels:
            labels_str = ", ".join(f"'{lbl}'" for lbl in labels)
            return (
                f"❌ {labels_str} ile ilgili kayıtlarda herhangi bir "
                f"tespit bulunamadı. Gözlüğünüzün aktif olduğundan "
                f"ve kayıt yapıldığından emin misiniz?"
            )
        return (
            "❌ Sorunuzu anlayamadım. Lütfen aradığınız nesneyi "
            "daha açık belirtin. Örneğin: 'Anahtarlarımı nereye koydum?'"
        )

    @staticmethod
    def _describe_position(x: float, y: float) -> str:
        """Describe position in Turkish based on normalized coords."""
        horizontal = "sol" if x < 0.33 else ("orta" if x < 0.66 else "sağ")
        vertical = "üst" if y < 0.33 else ("orta" if y < 0.66 else "alt")

        if horizontal == "orta" and vertical == "orta":
            return "merkez"
        return f"{vertical}-{horizontal}"

    @staticmethod
    def _format_time(dt: datetime) -> str:
        """Format datetime in Turkish-friendly style."""
        return dt.strftime("%d.%m.%Y %H:%M:%S")


# Protocol compliance verification
def _verify_protocol() -> None:
    """Verify FrameSearchService implements FrameSearchProtocol."""
    _service: FrameSearchProtocol = FrameSearchService(
        scene_memory=SceneMemory(),
    )
