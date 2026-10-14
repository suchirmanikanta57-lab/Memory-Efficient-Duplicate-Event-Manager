"""Run the CLI demo from anywhere: ``python scripts/run_demo.py``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["demo", *sys.argv[1:]]))
