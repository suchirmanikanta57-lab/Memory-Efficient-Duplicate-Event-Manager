"""Event-stream duplicate detector built on the Bloom Filter.

Identity policy: an event is identified by its ID string, matched
CASE-SENSITIVELY after stripping leading/trailing whitespace. Empty or missing
IDs are rejected (``InvalidEventError``); they are never merged into one event.
A positive result is only ever labelled POSSIBLE_DUPLICATE.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .bloom_filter import BloomFilter, optimal_hash_count

NEW_EVENT = "NEW_EVENT"
POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
SUPPORTED_MEMORY_KIB = (1, 2, 4, 8)


class InvalidEventError(ValueError):
    """Empty, non-string, or otherwise unusable event ID."""


class CsvFormatError(ValueError):
    """Malformed CSV input."""


def memory_budget_to_bits(memory_bytes: int) -> int:
    """Logical bit-array size for a byte budget: m = bytes * 8."""
    if isinstance(memory_bytes, bool) or not isinstance(memory_bytes, int) or memory_bytes <= 0:
        raise ValueError(f"memory budget must be a positive integer number of bytes, got {memory_bytes!r}")
    return memory_bytes * 8


def normalize_event_id(raw: object) -> str:
    """Strip whitespace; reject non-strings and empty IDs. Case is preserved."""
    if not isinstance(raw, str):
        raise InvalidEventError(f"event ID must be a string, got {type(raw).__name__}")
    event_id = raw.strip()
    if not event_id:
        raise InvalidEventError("event ID is empty or whitespace only")
    return event_id


@dataclass(frozen=True)
class EventResult:
    """Outcome of processing one event (counters are values after this event)."""

    event_id: str
    classification: str
    might_have_been_seen: bool
    inserted: bool
    event_count: int
    possible_duplicate_count: int
    occupancy: float
    estimated_false_positive_rate: float


class EventDetector:
    """Classify events as NEW_EVENT or POSSIBLE_DUPLICATE using a Bloom Filter."""

    def __init__(self, bloom_filter: BloomFilter) -> None:
        self.bloom_filter = bloom_filter
        self.event_count = 0
        self.possible_duplicate_count = 0
        self.skipped_rows = 0

    @classmethod
    def from_memory_budget(
        cls, memory_bytes: int, expected_items: int, num_hashes: int | None = None
    ) -> "EventDetector":
        """Build a detector whose logical bit array is exactly ``memory_bytes`` bytes."""
        bits = memory_budget_to_bits(memory_bytes)
        if num_hashes is None:
            num_hashes = optimal_hash_count(bits, expected_items)
        return cls(BloomFilter(expected_items, bit_array_size=bits, num_hashes=num_hashes))

    def process_event(self, event_id: str) -> EventResult:
        """Query the filter; insert only if probably new."""
        key = normalize_event_id(event_id)
        possibly_seen = self.bloom_filter.might_contain(key)
        if not possibly_seen:
            self.bloom_filter.add(key)
        self.event_count += 1
        if possibly_seen:
            self.possible_duplicate_count += 1
        return EventResult(
            event_id=key,
            classification=POSSIBLE_DUPLICATE if possibly_seen else NEW_EVENT,
            might_have_been_seen=possibly_seen,
            inserted=not possibly_seen,
            event_count=self.event_count,
            possible_duplicate_count=self.possible_duplicate_count,
            occupancy=self.bloom_filter.occupancy_ratio,
            estimated_false_positive_rate=self.bloom_filter.estimated_false_positive_rate,
        )

    def process_events(self, event_ids: Iterable[str]) -> list[EventResult]:
        return [self.process_event(e) for e in event_ids]

    def process_csv(
        self, path: str | Path, id_column: str = "event_id", skip_invalid: bool = False
    ) -> list[EventResult]:
        """Process a CSV file whose ``id_column`` holds the event identity.

        Malformed rows (wrong field count, empty ID) raise ``CsvFormatError``
        with the line number, or are counted in ``skipped_rows`` when
        ``skip_invalid`` is true.
        """
        results: list[EventResult] = []
        with Path(path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise CsvFormatError("CSV file is empty or has no header row")
            if id_column not in reader.fieldnames:
                raise CsvFormatError(
                    f"CSV has no '{id_column}' column (found: {', '.join(reader.fieldnames)})"
                )
            for row in reader:
                line = reader.line_num
                try:
                    if None in row or any(v is None for v in row.values()):
                        raise CsvFormatError(f"line {line}: wrong number of fields")
                    results.append(self.process_event(row[id_column]))
                except (CsvFormatError, InvalidEventError) as exc:
                    if skip_invalid:
                        self.skipped_rows += 1
                    elif isinstance(exc, CsvFormatError):
                        raise
                    else:
                        raise CsvFormatError(f"line {line}: {exc}") from exc
        return results

    def summary(self) -> dict[str, float | int]:
        """Counters and filter statistics (ratios are not confirmed-duplicate rates)."""
        bf = self.bloom_filter
        return {
            "events_processed": self.event_count,
            "classified_new": self.event_count - self.possible_duplicate_count,
            "classified_possible_duplicate": self.possible_duplicate_count,
            "skipped_rows": self.skipped_rows,
            "bit_array_size": bf.bit_array_size,
            "num_hashes": bf.num_hashes,
            "bits_set": bf.bit_set_count,
            "occupancy": bf.occupancy_ratio,
            "estimated_false_positive_rate": bf.estimated_false_positive_rate,
            "memory_bytes_logical": bf.memory_usage_bytes,
        }

    def reset(self) -> None:
        """Clear the filter and all counters."""
        self.bloom_filter.clear()
        self.event_count = 0
        self.possible_duplicate_count = 0
        self.skipped_rows = 0
