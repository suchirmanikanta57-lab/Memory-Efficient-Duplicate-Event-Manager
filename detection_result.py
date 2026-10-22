from enum import Enum
from typing import List
from src.model.event import Event


class DetectionStatus(Enum):
    """Possible outcomes when an event is screened."""

    # Bloom Filter returned false -> 100% Guaranteed Unique (Zero False Negatives)
    DEFINITE_UNIQUE = "DEFINITE_UNIQUE"

    # Bloom Filter returned true -> Possibly a duplicate, but could be a false positive
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"

    # Two-Tier mode confirmed: Bloom Filter flagged it AND exact storage verified it
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"

    # Two-Tier mode caught a false positive: Bloom filter said yes, but exact storage was empty!
    FALSE_POSITIVE_RESOLVED = "FALSE_POSITIVE_RESOLVED"


class DetectionResult:
    """Encapsulates the evaluation outcome of an event screening."""

    def __init__(self, event: Event, status: DetectionStatus, bit_positions: List[int],
                 latency_micros: float, message: str):
        self.event = event
        self.status = status
        self.bit_positions = list(bit_positions)
        self.latency_micros = latency_micros
        self.message = message

    @property
    def is_unique(self) -> bool:
        return self.status in (DetectionStatus.DEFINITE_UNIQUE, DetectionStatus.FALSE_POSITIVE_RESOLVED)

    @property
    def is_duplicate(self) -> bool:
        return self.status in (DetectionStatus.POSSIBLE_DUPLICATE, DetectionStatus.CONFIRMED_DUPLICATE)

    def to_display_string(self) -> str:
        return (
            f"--- SCREENING RESULT ---\n"
            f"Status:       {self.status.value}\n"
            f"Event:        \"{self.event.payload}\"\n"
            f"Hash Bits:    {self.bit_positions}\n"
            f"Latency:      {self.latency_micros:.2f} µs\n"
            f"Note:         {self.message}"
        )

    def __repr__(self) -> str:
        return (f"[{self.status.value}] Event: \"{self.event.payload}\" | "
                f"Bits: {self.bit_positions} | Latency: {self.latency_micros:.2f} µs | {self.message}")
