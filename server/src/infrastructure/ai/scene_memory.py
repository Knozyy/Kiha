"""Kiha Server — Scene Memory.

In-memory storage of detected objects with timestamps.
Enables answering questions like 'Where did I put my keys?'
by maintaining a chronological record of object sightings.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from domain.models.base import Detection, InferenceResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SceneRecord:
    """A single observation of an object in a frame.

    Records what was seen, when, and where in the frame.
    """

    frame_id: int
    timestamp: datetime
    label: str
    confidence: float
    x_center: float  # Normalized center position (0-1)
    y_center: float  # Normalized center position (0-1)
    area: float  # Normalized bbox area (0-1), indicates proximity


@dataclass
class ObjectTimeline:
    """Chronological history of a single object class.

    Tracks every time a specific object (e.g., 'keys', 'phone')
    was seen by the glasses.
    """

    label: str
    sightings: list[SceneRecord] = field(default_factory=list)

    @property
    def last_seen(self) -> SceneRecord | None:
        """Return the most recent sighting."""
        if not self.sightings:
            return None
        return self.sightings[-1]

    @property
    def first_seen(self) -> SceneRecord | None:
        """Return the earliest sighting."""
        if not self.sightings:
            return None
        return self.sightings[0]

    @property
    def total_sightings(self) -> int:
        """Return the total number of sightings."""
        return len(self.sightings)


class SceneMemory:
    """Central memory store for all detected objects.

    Maintains a per-device, per-object timeline of sightings.
    Designed for efficient querying by object label or time range.

    Current implementation: in-memory dict.
    Production: will be backed by Redis for persistence and TTL.
    """

    def __init__(self, max_records_per_object: int = 10000) -> None:
        # device_id → label → ObjectTimeline
        self._memory: dict[str, dict[str, ObjectTimeline]] = defaultdict(dict)
        self._max_records = max_records_per_object
        self._total_records = 0

    def add_inference_result(
        self,
        device_id: str,
        result: InferenceResult,
    ) -> int:
        """Store all detections from an inference result.

        Returns the number of new records added.
        """
        added = 0
        device_memory = self._memory[device_id]

        for detection in result.detections:
            record = self._detection_to_record(
                frame_id=result.frame_id,
                timestamp=result.timestamp,
                detection=detection,
            )

            label = detection.label.lower()
            if label not in device_memory:
                device_memory[label] = ObjectTimeline(label=label)

            timeline = device_memory[label]
            timeline.sightings.append(record)

            # Enforce max records limit (FIFO eviction)
            if len(timeline.sightings) > self._max_records:
                timeline.sightings.pop(0)

            added += 1

        self._total_records += added
        return added

    def search_by_object(
        self,
        device_id: str,
        label: str,
        limit: int = 10,
    ) -> list[SceneRecord]:
        """Find all sightings of a specific object.

        Returns the most recent sightings first, up to `limit`.
        """
        label_lower = label.lower()
        device_memory = self._memory.get(device_id, {})

        # Exact match
        timeline = device_memory.get(label_lower)
        if timeline:
            return list(reversed(timeline.sightings[-limit:]))

        # Partial match (e.g., 'key' matches 'keyboard' too)
        results: list[SceneRecord] = []
        for stored_label, tl in device_memory.items():
            if label_lower in stored_label or stored_label in label_lower:
                results.extend(tl.sightings[-limit:])

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]

    def get_last_seen(
        self,
        device_id: str,
        label: str,
    ) -> SceneRecord | None:
        """Get the most recent sighting of an object.

        This directly answers 'Where did I last see my X?'
        """
        results = self.search_by_object(device_id, label, limit=1)
        if results:
            return results[0]
        return None

    def search_by_time_range(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        label_filter: str | None = None,
    ) -> list[SceneRecord]:
        """Find all detections within a time range.

        Optionally filter by object label.
        """
        device_memory = self._memory.get(device_id, {})
        results: list[SceneRecord] = []

        for stored_label, timeline in device_memory.items():
            if label_filter and label_filter.lower() not in stored_label:
                continue

            for record in timeline.sightings:
                if start_time <= record.timestamp <= end_time:
                    results.append(record)

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results

    def get_all_objects(self, device_id: str) -> list[str]:
        """List all unique object labels seen by a device."""
        device_memory = self._memory.get(device_id, {})
        return list(device_memory.keys())

    def get_object_summary(
        self,
        device_id: str,
    ) -> dict[str, int]:
        """Get a summary of all objects and their sighting counts."""
        device_memory = self._memory.get(device_id, {})
        return {
            label: timeline.total_sightings
            for label, timeline in device_memory.items()
        }

    def clear_device(self, device_id: str) -> None:
        """Clear all memory for a specific device."""
        if device_id in self._memory:
            del self._memory[device_id]

    @property
    def total_records(self) -> int:
        """Total records across all devices."""
        return self._total_records

    @staticmethod
    def _detection_to_record(
        frame_id: int,
        timestamp: datetime,
        detection: Detection,
    ) -> SceneRecord:
        """Convert a Detection to a SceneRecord with center point and area."""
        bbox = detection.bbox
        x_center = (bbox.x_min + bbox.x_max) / 2
        y_center = (bbox.y_min + bbox.y_max) / 2
        area = (bbox.x_max - bbox.x_min) * (bbox.y_max - bbox.y_min)

        return SceneRecord(
            frame_id=frame_id,
            timestamp=timestamp,
            label=detection.label.lower(),
            confidence=detection.confidence,
            x_center=round(x_center, 4),
            y_center=round(y_center, 4),
            area=round(area, 6),
        )
