"""Reproducible experiments comparing logical memory budgets.

Ground truth (``GroundTruthTracker``) lives only here and is used only to
label events after the detector has answered. Timing is the only
non-deterministic output; all counts depend only on the seed and parameters.
"""

from __future__ import annotations

import csv
import statistics
import time
from pathlib import Path
from typing import Iterator, Sequence

from .bloom_filter import BloomFilter
from .event_detector import SUPPORTED_MEMORY_KIB, EventDetector, memory_budget_to_bits
from .event_generator import generate_stream
from .metrics import ConfusionCounts, GroundTruthTracker

DEFAULT_UNIQUE_COUNTS = (250, 500, 1000, 2000, 4000, 8000)
DEFAULT_HASH_COUNTS = (1, 2, 3, 4, 6, 8, 12)
RESULT_FIELDS = (
    "experiment", "memory_kib", "memory_bits", "num_hashes", "seed", "trials",
    "total_events", "first_time_events", "actual_repeats", "classified_new",
    "classified_possible_duplicate", "true_positives", "false_positives",
    "true_negatives", "false_negatives", "empirical_fpr", "theoretical_fpr",
    "occupancy_estimated_fpr", "occupancy", "memory_bytes_logical",
    "time_median_s", "time_min_s",
)
_INT_FIELDS = {f for f in RESULT_FIELDS if f not in {
    "experiment", "empirical_fpr", "theoretical_fpr", "occupancy_estimated_fpr",
    "occupancy", "time_median_s", "time_min_s"}}
_FLOAT_FIELDS = {"empirical_fpr", "theoretical_fpr", "occupancy_estimated_fpr",
                 "occupancy", "time_median_s", "time_min_s"}


class PlottingUnavailableError(RuntimeError):
    """matplotlib is not installed."""


def validate_memory_kib(values: Sequence[int]) -> list[int]:
    """Check budgets are among the supported 1/2/4/8 KiB values."""
    out = list(values)
    bad = [v for v in out if v not in SUPPORTED_MEMORY_KIB]
    if not out or bad:
        raise ValueError(f"memory budgets must be chosen from {SUPPORTED_MEMORY_KIB} KiB, got {bad or out}")
    return out


def run_single(experiment: str, memory_kib: int, num_events: int, num_unique: int,
               seed: int = 42, num_hashes: int | None = None, trials: int = 3) -> dict:
    """One configuration: fresh filter per trial, same stream every trial.

    ``num_hashes=None`` uses the optimal k for ``num_unique`` and the budget.
    """
    if trials < 1:
        raise ValueError("trials must be at least 1")
    events = list(generate_stream(num_events, num_unique, seed))
    times: list[float] = []
    for _ in range(trials):
        detector = EventDetector.from_memory_budget(memory_kib * 1024, max(num_unique, 1), num_hashes)
        truth, counts = GroundTruthTracker(), ConfusionCounts()
        start = time.perf_counter()
        predictions = [detector.process_event(e).might_have_been_seen for e in events]
        times.append(time.perf_counter() - start)
        for event, predicted in zip(events, predictions):
            counts.record(truth.observe(event), predicted)
    bf = detector.bloom_filter
    return {
        "experiment": experiment, "memory_kib": memory_kib,
        "memory_bits": memory_budget_to_bits(memory_kib * 1024),
        "num_hashes": bf.num_hashes, "seed": seed, "trials": trials,
        "total_events": counts.total, "first_time_events": counts.first_time_events,
        "actual_repeats": counts.actual_repeats, "classified_new": counts.classified_new,
        "classified_possible_duplicate": counts.flagged_possible_duplicate,
        "true_positives": counts.tp, "false_positives": counts.fp,
        "true_negatives": counts.tn, "false_negatives": counts.fn,
        "empirical_fpr": counts.false_positive_rate,
        "theoretical_fpr": bf.expected_false_positive_rate(counts.first_time_events),
        "occupancy_estimated_fpr": bf.estimated_false_positive_rate,
        "occupancy": bf.occupancy_ratio, "memory_bytes_logical": bf.memory_usage_bytes,
        "time_median_s": statistics.median(times), "time_min_s": min(times),
    }


def memory_comparison(memory_kibs: Sequence[int], num_events: int, num_unique: int,
                      seed: int = 42, trials: int = 3) -> list[dict]:
    """Same stream, every memory budget."""
    return [run_single("memory_comparison", m, num_events, num_unique, seed, None, trials)
            for m in validate_memory_kib(memory_kibs)]


def unique_sweep(memory_kibs: Sequence[int], unique_counts: Sequence[int], events_per_unique: int = 2,
                 seed: int = 42, trials: int = 3, num_hashes: int = 4) -> list[dict]:
    """Vary the number of distinct events with k held FIXED (so only load changes).

    Each stream has ``events_per_unique`` x as many events as distinct events.
    """
    return [run_single("unique_sweep", m, u * events_per_unique, u, seed, num_hashes, trials)
            for m in validate_memory_kib(memory_kibs) for u in unique_counts]


def hash_sweep(memory_kibs: Sequence[int], hash_counts: Sequence[int], num_events: int,
               num_unique: int, seed: int = 42, trials: int = 3) -> list[dict]:
    """Vary k at fixed budget and data."""
    return [run_single("hash_sweep", m, num_events, num_unique, seed, k, trials)
            for m in validate_memory_kib(memory_kibs) for k in hash_counts]


def simulate(iterations: int, memory_kib: int, seed: int = 42, report_every: int = 100,
             unique_ratio: float = 0.5, expected_items: int | None = None) -> Iterator[dict]:
    """Bounded live simulation: yield a progress snapshot every ``report_every`` events."""
    if iterations < 1 or report_every < 1 or not 0 < unique_ratio <= 1:
        raise ValueError("iterations/report_every must be >= 1 and unique_ratio in (0, 1]")
    num_unique = max(1, int(iterations * unique_ratio))
    detector = EventDetector.from_memory_budget(memory_kib * 1024, expected_items or num_unique)
    for event in generate_stream(iterations, num_unique, seed):
        result = detector.process_event(event)
        if result.event_count % report_every == 0 or result.event_count == iterations:
            yield {"processed": result.event_count,
                   "new": result.event_count - result.possible_duplicate_count,
                   "possible_duplicates": result.possible_duplicate_count,
                   "occupancy": result.occupancy,
                   "estimated_fpr": result.estimated_false_positive_rate}


def write_results_csv(rows: Sequence[dict], path: str | Path) -> Path:
    """Write rows to CSV; undefined ratios (None) become empty cells."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row[k] is None else row[k]) for k in RESULT_FIELDS})
    return path


def read_results_csv(path: str | Path) -> list[dict]:
    """Read a results CSV back with numeric types restored (empty -> None)."""
    rows = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row: dict = {}
            for key, value in raw.items():
                if key in _INT_FIELDS:
                    row[key] = int(value)
                elif key in _FLOAT_FIELDS:
                    row[key] = None if value == "" else float(value)
                else:
                    row[key] = value
            rows.append(row)
    return rows


def _fmt(value: float | None, digits: int = 5) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def format_table(rows: Sequence[dict]) -> str:
    """Readable side-by-side table (empirical vs theoretical FPR)."""
    header = (f"{'KiB':>4} {'bits':>7} {'k':>3} {'events':>7} {'new':>6} {'FP':>5} {'FN':>3} "
              f"{'emp.FPR':>9} {'theory':>9} {'occ-est':>9} {'occup.':>7} {'time(s)':>9}")
    lines = [header, "-" * len(header)]
    for r in rows:
        lines.append(
            f"{r['memory_kib']:>4} {r['memory_bits']:>7} {r['num_hashes']:>3} {r['total_events']:>7} "
            f"{r['first_time_events']:>6} {r['false_positives']:>5} {r['false_negatives']:>3} "
            f"{_fmt(r['empirical_fpr']):>9} {_fmt(r['theoretical_fpr']):>9} "
            f"{_fmt(r['occupancy_estimated_fpr']):>9} {r['occupancy']:>7.3f} {r['time_median_s']:>9.4f}")
    return "\n".join(lines)


def build_summary(memory_rows: Sequence[dict], sweep_rows: Sequence[dict] = ()) -> str:
    """Technical summary text built only from the supplied result rows."""
    if not memory_rows:
        return "No memory-comparison results available.\n"
    first = memory_rows[0]
    out = ["TECHNICAL SUMMARY", "=================",
           f"Seed: {first['seed']}   Trials per configuration: {first['trials']}",
           f"Dataset: {first['total_events']} events, {first['first_time_events']} first-time, "
           f"{first['actual_repeats']} genuine repeats",
           "Budgets are logical bit-array sizes only, not process RAM.", "", format_table(memory_rows), "",
           "Observations (this run only):"]
    for r in memory_rows:
        note = ("no false positives observed in this sample (does not prove the true probability is 0)"
                if r["false_positives"] == 0 and r["first_time_events"] > 0
                else "no first-time events, FPR undefined" if r["first_time_events"] == 0
                else f"{r['false_positives']} false positives among {r['first_time_events']} first-time events")
        out.append(f"- {r['memory_kib']} KiB: {note}; occupancy {r['occupancy']:.3f}; "
                   f"false negatives {r['false_negatives']}; median time {r['time_median_s']:.4f}s")
    if sweep_rows:
        out.append(f"- unique-event sweep has {len(sweep_rows)} configurations (see unique_sweep.csv)")
    out += ["", "Main limitations: possible duplicates are not confirmed duplicates; FPR grows as the",
            "filter fills; no deletion or persistence; timings vary by machine and run."]
    return "\n".join(out) + "\n"


def generate_plots(output_dir: str | Path, memory_rows: Sequence[dict], sweep_rows: Sequence[dict]) -> list[Path]:
    """Save four PNG plots built directly from the result rows."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise PlottingUnavailableError(
            "matplotlib is not installed; run: pip install -r requirements-dev.txt") from exc
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    def bars(name: str, key: str, ylabel: str, title: str, scale: float = 1.0) -> None:
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = [str(r["memory_kib"]) for r in memory_rows]
        values = [(r[key] or 0.0) * scale for r in memory_rows]
        ax.bar(labels, values, label=ylabel)
        ax.set(xlabel="Logical memory budget (KiB)", ylabel=ylabel, title=title)
        ax.legend()
        fig.tight_layout()
        saved.append(out_dir / name)
        fig.savefig(saved[-1], dpi=120)
        plt.close(fig)

    if memory_rows:
        bars("memory_vs_fpr.png", "empirical_fpr", "Empirical FPR (FP / (FP + TN))",
             "Memory budget vs empirical false-positive rate")
        bars("memory_vs_occupancy.png", "occupancy", "Occupancy (fraction of bits set)",
             "Memory budget vs filter occupancy")
        bars("memory_vs_time.png", "time_median_s", "Median processing time (ms)",
             "Memory budget vs processing time", 1000.0)
    if sweep_rows:
        fig, ax = plt.subplots(figsize=(6, 4))
        for m in sorted({r["memory_kib"] for r in sweep_rows}):
            pts = [r for r in sweep_rows if r["memory_kib"] == m]
            ax.plot([r["first_time_events"] for r in pts], [r["empirical_fpr"] or 0.0 for r in pts],
                    marker="o", label=f"{m} KiB")
        ax.set(xlabel="Unique events inserted", ylabel="Empirical FPR",
               title="Unique events vs empirical false-positive rate", xscale="log")
        ax.legend()
        fig.tight_layout()
        saved.append(out_dir / "unique_events_vs_fpr.png")
        fig.savefig(saved[-1], dpi=120)
        plt.close(fig)
    return saved
