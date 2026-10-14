"""Rebuild summary.txt and plots from CSV files already in a results directory.

Usage: python scripts/generate_report.py [results_dir]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import experiment_runner as xr  # noqa: E402


def run(results_dir: Path) -> int:
    memory_csv, sweep_csv = results_dir / "memory_comparison.csv", results_dir / "unique_sweep.csv"
    if not memory_csv.is_file():
        print(f"error: {memory_csv} not found; run scripts/run_experiments.py first", file=sys.stderr)
        return 1
    memory_rows = xr.read_results_csv(memory_csv)
    sweep_rows = xr.read_results_csv(sweep_csv) if sweep_csv.is_file() else []
    (results_dir / "summary.txt").write_text(xr.build_summary(memory_rows, sweep_rows), encoding="utf-8")
    print(f"wrote {results_dir / 'summary.txt'}")
    try:
        for path in xr.generate_plots(results_dir, memory_rows, sweep_rows):
            print(f"wrote {path}")
    except xr.PlottingUnavailableError as exc:
        print(f"warning: plots skipped: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(run(Path(sys.argv[1] if len(sys.argv) > 1 else "experiments/results")))
