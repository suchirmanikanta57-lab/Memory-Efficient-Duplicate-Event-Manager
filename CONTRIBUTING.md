# Contributing

1. Fork or branch from `main`.
2. Create a virtual environment and install `requirements-dev.txt`.
3. Make focused changes; keep the core modules (`bloom_filter.py`, `hash_functions.py`,
   `event_detector.py`, `event_generator.py`, `metrics.py`) under 500 lines combined.
4. Add or update tests; run `python -m pytest`.
5. Update the docs if behaviour changes. Never describe `POSSIBLE_DUPLICATE` as a confirmed duplicate,
   and never add results you did not actually run.
6. Open a pull request using the template.

Style: PEP 8, type hints, docstrings, `pathlib` for paths, standard library first.
