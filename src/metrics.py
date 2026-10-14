"""Evaluation metrics and the evaluation-only ground-truth tracker."""

from __future__ import annotations

from dataclasses import dataclass


def safe_ratio(numerator: float, denominator: float) -> float | None:
    """numerator / denominator, or None (reported as N/A) when denominator is 0."""
    return None if denominator == 0 else numerator / denominator


class GroundTruthTracker:
    """EVALUATION ONLY: exact record of which IDs have truly been seen.

    Never used by ``EventDetector``; it only labels events so experiments can
    compare the Bloom Filter's answers against the truth.
    """

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def observe(self, event_id: str) -> bool:
        """Return True if ``event_id`` was truly seen before, then record it."""
        was_seen = event_id in self._seen
        self._seen.add(event_id)
        return was_seen


@dataclass
class ConfusionCounts:
    """Positive = 'possible duplicate'. TP: repeat flagged; FP: new event flagged;
    TN: new event reported new; FN: repeat reported new (expected 0)."""

    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    def record(self, truly_seen: bool, flagged_duplicate: bool) -> None:
        """Count one (truth, prediction) pair."""
        if truly_seen and flagged_duplicate:
            self.tp += 1
        elif truly_seen:
            self.fn += 1
        elif flagged_duplicate:
            self.fp += 1
        else:
            self.tn += 1

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def actual_repeats(self) -> int:
        return self.tp + self.fn

    @property
    def first_time_events(self) -> int:
        return self.fp + self.tn

    @property
    def flagged_possible_duplicate(self) -> int:
        return self.tp + self.fp

    @property
    def classified_new(self) -> int:
        return self.tn + self.fn

    @property
    def false_positive_rate(self) -> float | None:
        """FP / (FP + TN): among genuinely new events. None if there are none."""
        return safe_ratio(self.fp, self.fp + self.tn)

    @property
    def false_negative_rate(self) -> float | None:
        """FN / (FN + TP): among genuine repeats. None if there are none."""
        return safe_ratio(self.fn, self.fn + self.tp)

    @property
    def possible_duplicate_share(self) -> float | None:
        """(TP + FP) / total: share of ALL events flagged. NOT the FP rate."""
        return safe_ratio(self.flagged_possible_duplicate, self.total)
