"""Run all experiments: ``python scripts/run_experiments.py [experiment options]``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["experiment", *sys.argv[1:]]))
