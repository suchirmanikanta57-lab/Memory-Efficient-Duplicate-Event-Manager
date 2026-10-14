"""Command-line interface: ``python -m src.cli <command>``."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Sequence

from . import experiment_runner as xr
from .bloom_filter import BloomFilter, optimal_hash_count
from .event_detector import (NEW_EVENT, POSSIBLE_DUPLICATE, SUPPORTED_MEMORY_KIB,
                             CsvFormatError, EventDetector, memory_budget_to_bits)

CAVEAT = (f"Note: {POSSIBLE_DUPLICATE} means every required bit was already 1. It is NOT a confirmed\n"
          f"duplicate and may be a false positive. {NEW_EVENT} is definite: some required bit was 0.")
DEMO_EVENTS = ["USER_LOGIN:user_104", "PAYMENT:txn_205", "FILE_UPLOAD:file_309", "USER_LOGIN:user_104",
               "SENSOR_ALERT:sensor_17", "PAYMENT:txn_205", "PAGE_VIEW:page_501", "USER_LOGIN:user_104",
               "PAGE_VIEW:page_502", "FILE_UPLOAD:file_309"]
DEMO_CAPACITY = 1000  # planned number of unique events for the demo filters


def _positive(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {text}")
    return value


def _fpr(text: str) -> float:
    value = float(text)
    if not 0.0 < value < 1.0:
        raise argparse.ArgumentTypeError(f"must be strictly between 0 and 1, got {text}")
    return value


def _add_memory(p: argparse.ArgumentParser, many: bool = False, default=None) -> None:
    kw = dict(type=int, choices=SUPPORTED_MEMORY_KIB, default=default,
              help="logical Bloom Filter memory budget in KiB (1, 2, 4 or 8)")
    p.add_argument("--memory-kb", **kw, **({"nargs": "+"} if many else {}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="Memory-limited duplicate event detector using a Bloom Filter. Budgets limit the "
                    "logical bit array only, not total process RAM.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("demo", help="process a small built-in event stream")
    _add_memory(p, default=4)

    p = sub.add_parser("detect", help="classify events from a CSV file")
    p.add_argument("--input", required=True, help="CSV file with a header row")
    p.add_argument("--id-column", default="event_id", help="column holding the event identity")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--memory-kb", type=int, choices=SUPPORTED_MEMORY_KIB, default=None,
                       help="logical memory budget in KiB (default 4 if --target-fpr is absent)")
    group.add_argument("--target-fpr", type=_fpr, help="size the filter for this false-positive probability")
    p.add_argument("--expected-events", type=_positive, default=1000, help="expected unique events (default 1000)")
    p.add_argument("--num-hashes", type=_positive, help="override the number of hash functions")
    p.add_argument("--skip-invalid", action="store_true", help="skip malformed rows instead of failing")
    p.add_argument("--show-events", action="store_true", help="print one line per event")
    p.add_argument("--output", help="write per-event results to this CSV file")

    p = sub.add_parser("experiment", help="compare memory budgets on generated data")
    _add_memory(p, many=True, default=list(SUPPORTED_MEMORY_KIB))
    p.add_argument("--num-events", type=_positive, default=2000)
    p.add_argument("--unique-events", type=_positive, default=1000)
    p.add_argument("--unique-counts", type=_positive, nargs="+", default=list(xr.DEFAULT_UNIQUE_COUNTS))
    p.add_argument("--sweep-hashes", type=_positive, default=4, help="fixed k used by the unique-event sweep")
    p.add_argument("--hash-counts", type=_positive, nargs="+", default=list(xr.DEFAULT_HASH_COUNTS))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--trials", type=_positive, default=3, help="timing repetitions per configuration")
    p.add_argument("--output-dir", default="experiments/results")
    p.add_argument("--plots", action="store_true", help="also save PNG plots (needs matplotlib)")

    p = sub.add_parser("simulate", help="bounded live event-stream simulation")
    _add_memory(p, default=1)
    p.add_argument("--iterations", type=_positive, default=1000)
    p.add_argument("--report-every", type=_positive, default=200)
    p.add_argument("--seed", type=int, default=42)

    p = sub.add_parser("stats", help="theoretical filter configurations (no events processed)")
    _add_memory(p, many=True, default=list(SUPPORTED_MEMORY_KIB))
    p.add_argument("--items", type=_positive, nargs="+", default=[500, 1000, 2000, 4000])
    p.add_argument("--target-fpr", type=_fpr, default=0.01)

    p = sub.add_parser("clear-demo", help="show that clearing resets the filter")
    _add_memory(p, default=4)
    return parser


def _print_summary(summary: dict) -> None:
    print(f"  events processed       : {summary['events_processed']}")
    print(f"  classified {NEW_EVENT:<12}: {summary['classified_new']}")
    print(f"  classified {POSSIBLE_DUPLICATE:<12}: {summary['classified_possible_duplicate']}")
    if summary["skipped_rows"]:
        print(f"  skipped malformed rows : {summary['skipped_rows']}")
    print(f"  filter bits (m) / hashes (k): {summary['bit_array_size']} / {summary['num_hashes']}")
    print(f"  logical bit-array bytes: {summary['memory_bytes_logical']}")
    print(f"  occupancy              : {summary['occupancy']:.4f}")
    print(f"  occupancy-based FPR est: {summary['estimated_false_positive_rate']:.6f}")


def cmd_demo(args: argparse.Namespace) -> int:
    detector = EventDetector.from_memory_budget(args.memory_kb * 1024, DEMO_CAPACITY)
    print(f"Demo with {args.memory_kb} KiB logical budget")
    for r in detector.process_events(DEMO_EVENTS):
        print(f"  {r.event_id:<24} -> {r.classification}")
    _print_summary(detector.summary())
    print(CAVEAT)
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.is_file():
        print(f"error: input file not found: {path}", file=sys.stderr)
        return 1
    if args.target_fpr is not None:
        bloom = BloomFilter(args.expected_events, args.target_fpr, num_hashes=args.num_hashes)
        detector, label = EventDetector(bloom), f"target FPR {args.target_fpr}"
    else:
        kib = args.memory_kb or 4
        detector = EventDetector.from_memory_budget(kib * 1024, args.expected_events, args.num_hashes)
        label = f"{kib} KiB logical budget"
    results = detector.process_csv(path, args.id_column, args.skip_invalid)
    print(f"Processed {path} ({label})")
    if args.show_events:
        for i, r in enumerate(results, 1):
            print(f"  {i:>5}. {r.event_id:<28} -> {r.classification}")
    _print_summary(detector.summary())
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["event_id", "classification", "occupancy", "estimated_false_positive_rate"])
            writer.writerows([r.event_id, r.classification, f"{r.occupancy:.6f}",
                              f"{r.estimated_false_positive_rate:.8f}"] for r in results)
        print(f"  per-event results written to {out}")
    print(CAVEAT)
    return 0


def cmd_experiment(args: argparse.Namespace) -> int:
    if args.unique_events > args.num_events:
        print("error: --unique-events cannot exceed --num-events", file=sys.stderr)
        return 1
    out_dir = Path(args.output_dir)
    kibs = sorted(set(args.memory_kb))
    memory_rows = xr.memory_comparison(kibs, args.num_events, args.unique_events, args.seed, args.trials)
    sweep_rows = xr.unique_sweep(kibs, args.unique_counts, 2, args.seed, args.trials, args.sweep_hashes)
    hash_rows = xr.hash_sweep(kibs, args.hash_counts, args.num_events, args.unique_events, args.seed, args.trials)
    for name, rows in (("memory_comparison", memory_rows), ("unique_sweep", sweep_rows), ("hash_sweep", hash_rows)):
        print(f"wrote {xr.write_results_csv(rows, out_dir / f'{name}.csv')}")
    summary = xr.build_summary(memory_rows, sweep_rows)
    (out_dir / "summary.txt").write_text(summary, encoding="utf-8")
    print(f"wrote {out_dir / 'summary.txt'}\n")
    print(summary)
    if args.plots:
        try:
            for path in xr.generate_plots(out_dir, memory_rows, sweep_rows):
                print(f"wrote {path}")
        except xr.PlottingUnavailableError as exc:
            print(f"warning: plots skipped: {exc}", file=sys.stderr)
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    print(f"Simulating {args.iterations} events, {args.memory_kb} KiB budget, seed {args.seed}")
    print(f"{'processed':>10} {'new':>7} {'possible-dup':>13} {'occupancy':>10} {'est.FPR':>10}")
    for s in xr.simulate(args.iterations, args.memory_kb, args.seed, args.report_every):
        print(f"{s['processed']:>10} {s['new']:>7} {s['possible_duplicates']:>13} "
              f"{s['occupancy']:>10.4f} {s['estimated_fpr']:>10.6f}")
    print(CAVEAT)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    print("Theoretical configurations: p = (1 - exp(-k n / m)) ** k, k = round(m/n * ln 2)")
    print("No events are processed and nothing is stored between runs.\n")
    for kib in sorted(set(args.memory_kb)):
        m = memory_budget_to_bits(kib * 1024)
        capacity = math.floor(-m * math.log(2) ** 2 / math.log(args.target_fpr))
        print(f"{kib} KiB = {m} bits; about {capacity} items at target FPR {args.target_fpr} (ideal formula)")
        for n in args.items:
            k = optimal_hash_count(m, n)
            p = (1 - math.exp(-k * n / m)) ** k
            print(f"    n={n:<6} k={k:<3} theoretical FPR={p:.3e}")
    return 0


def cmd_clear_demo(args: argparse.Namespace) -> int:
    detector = EventDetector.from_memory_budget(args.memory_kb * 1024, DEMO_CAPACITY)
    detector.process_events(DEMO_EVENTS)
    print(f"Stream 1 processed: occupancy {detector.bloom_filter.occupancy_ratio:.4f}")
    again = detector.process_event(DEMO_EVENTS[0]).classification
    print(f"  re-sending {DEMO_EVENTS[0]} -> {again}")
    detector.reset()
    print(f"After reset: occupancy {detector.bloom_filter.occupancy_ratio:.4f}, events {detector.event_count}")
    after = detector.process_event(DEMO_EVENTS[0]).classification
    print(f"  re-sending {DEMO_EVENTS[0]} -> {after} (the filter has forgotten everything)")
    detector.process_events(["PAYMENT:txn_999", "PAGE_VIEW:page_777"])
    print(f"Stream 2 processed: {detector.event_count} events, occupancy {detector.bloom_filter.occupancy_ratio:.4f}")
    return 0


HANDLERS = {"demo": cmd_demo, "detect": cmd_detect, "experiment": cmd_experiment,
            "simulate": cmd_simulate, "stats": cmd_stats, "clear-demo": cmd_clear_demo}


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI; returns 0 on success, 1 for input errors (argparse uses 2 for usage errors)."""
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.command](args)
    except (CsvFormatError, ValueError, OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
