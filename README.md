# Memory-Limited Duplicate Event Detector Using a Bloom Filter

A Python case study that detects *possible* duplicate events in a stream while keeping membership
state in a fixed-size bit array. The Bloom Filter, its hashing, the detector, the experiments and the
CLI are all implemented here from scratch with the Python standard library (`pytest` and `matplotlib`
are optional development extras).

## 1. Project overview

Events such as `USER_LOGIN:user_104` or `PAYMENT:txn_205` arrive one by one. For each event the
detector asks the Bloom Filter whether all of its required bits are already 1:

| Filter answer | Label | Meaning |
|---|---|---|
| some bit is 0 | `NEW_EVENT` | **Definitely** never inserted. The event is then inserted. |
| all bits are 1 | `POSSIBLE_DUPLICATE` | Probably seen before, **but may be a false positive**. |

The filter never stores the events themselves, only bits.

## 2. Problem statement

How can a system flag repeated events when remembering every event ID would use too much memory?

## 3. Motivation

An exact set grows with the number of distinct events. A Bloom Filter has a fixed size chosen up front,
and trades exactness for space: it can wrongly flag a new event (false positive) but, in normal
operation, never wrongly reports a seen event as new.

## 4. Objectives

- Implement a Bloom Filter and deterministic double hashing ourselves.
- Build an event detector on top of it with honest labels (`POSSIBLE_DUPLICATE`).
- Compare 1, 2, 4 and 8 KiB logical memory budgets experimentally with known ground truth.
- Provide tests, documentation and viva material.

## 5. Real-world applications

Web crawlers skipping already-visited URLs, databases avoiding disk lookups for absent keys, caches
and CDNs, spell checkers and blocklists, network monitoring, and log or event de-duplication where an
occasional false alarm is acceptable.

## 6. What a Bloom Filter is

A bit array of `m` bits (initially all 0) and `k` hash functions. To insert an item, set the `k` bits its
hashes select. To query, check those `k` bits. See [docs/bloom_filter_explained.md](docs/bloom_filter_explained.md).

## 7. How the algorithm works

1. Compute one SHA-256 digest of the UTF-8 event ID; split it into `h1` and `h2` (each reduced mod `m`;
   `h2 = 0` is replaced by 1 so probes never all coincide).
2. Positions are `(h1 + i * h2) mod m` for `i = 0 .. k-1` (double hashing).
3. `might_contain`: all `k` bits are 1 -> `True`, otherwise `False`.
4. `process_event`: query first; insert only when the answer was `False`.

## 8. Architecture overview

```
CSV / generator --> EventDetector --> BloomFilter --> hash_functions
                         |                 (bytearray, m bits)
                         v
                  EventResult / summary --> CLI output, CSV export

experiment_runner --> (separate) GroundTruthTracker labels each event --> metrics --> CSV / plots
```

Details: [docs/architecture.md](docs/architecture.md).

## 9. Repository structure

```
memory-limited-duplicate-event-detector/
|-- README.md  LICENSE  .gitignore  requirements.txt  requirements-dev.txt  pyproject.toml
|-- CONTRIBUTING.md  SECURITY.md  CHANGELOG.md
|-- src/            bloom_filter.py hash_functions.py event_detector.py event_generator.py
|                   metrics.py experiment_runner.py cli.py __init__.py
|-- tests/          test_bloom_filter.py test_hash_functions.py test_event_detector.py
|                   test_metrics.py test_experiments.py test_cli.py __init__.py
|-- data/           sample_events.csv  README.md
|-- scripts/        run_demo.py  run_experiments.py  generate_report.py
|-- experiments/    README.md  results/.gitkeep
|-- docs/           architecture.md bloom_filter_explained.md algorithm_analysis.md
|                   experimental_methodology.md limitations.md viva_questions.md team_contributions.md
`-- .github/        workflows/python-tests.yml  ISSUE_TEMPLATE/  PULL_REQUEST_TEMPLATE.md
```

## 10. System requirements

Python 3.10 or newer. No internet access, database, Docker, API key or paid software is needed after
dependencies are installed. The core detector needs **no third-party packages**.

## 11. Installation

```bash
git clone <your-repository-url>
cd memory-limited-duplicate-event-detector
```

## 12. Virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
```

## 13. Dependencies

```bash
pip install -r requirements-dev.txt
```

| Package | Why | Required? |
|---|---|---|
| (none) | Runtime code is standard-library only (`requirements.txt` has no packages) | - |
| `pytest`, `pytest-cov` | Tests and optional coverage | development |
| `matplotlib` | Optional PNG plots; without it everything else still works | optional |

All commands below run from the repository root; no `PYTHONPATH` changes are needed.

## 14. Demo

```bash
python -m src.cli demo
python -m src.cli demo --memory-kb 1
python -m src.cli clear-demo          # shows that reset() makes the filter forget everything
python -m src.cli simulate --iterations 1000 --memory-kb 1 --report-every 200   # bounded live simulation
python scripts/run_demo.py            # same as `demo`, runnable from any directory
```

## 15. Processing a CSV file

```bash
python -m src.cli detect --input data/sample_events.csv --memory-kb 4
python -m src.cli detect --input data/sample_events.csv --memory-kb 1 --show-events
python -m src.cli detect --input data/sample_events.csv --target-fpr 0.01 --expected-events 100
python -m src.cli detect --input data/sample_events.csv --output experiments/results/sample_detect.csv
```

Event identity is the `event_id` column (change with `--id-column`), matched **case-sensitively** after
trimming whitespace. Empty IDs or wrong field counts stop the run with a line-numbered error; add
`--skip-invalid` to count and skip such rows instead. Schema: [data/README.md](data/README.md).

## 16. Memory-budget configuration

`--memory-kb` accepts 1, 2, 4 or 8, meaning 1024, 2048, 4096 or 8192 bytes, i.e. `m = bytes * 8` bits
(8192, 16384, 32768, 65536). The number of hashes `k` is derived from the expected unique events
(`--expected-events`, default 1000) unless overridden with `--num-hashes`. **This budget limits the
logical bit array only.** The Python process, interpreter, objects and this program's other data use
more RAM.

```bash
python -m src.cli stats                       # theoretical m, k and FPR for each budget (nothing is processed)
python -m src.cli stats --memory-kb 1 4 --items 500 1000 2000 --target-fpr 0.01
```

## 17. Experiments

```bash
python -m src.cli experiment                           # all four budgets, seed 42, writes experiments/results/
python -m src.cli experiment --memory-kb 1 2 4 8 --num-events 2000 --unique-events 1000 --seed 42
python -m src.cli experiment --output-dir my_results --trials 5
python scripts/run_experiments.py                      # same as `experiment`
```

Outputs: `memory_comparison.csv`, `unique_sweep.csv`, `hash_sweep.csv`, `summary.txt`. Generated files
are git-ignored. Counts depend only on seed and parameters; timings vary between runs. Method:
[docs/experimental_methodology.md](docs/experimental_methodology.md).

## 18. Plot generation

```bash
python -m src.cli experiment --plots                   # needs matplotlib
python scripts/generate_report.py experiments/results  # rebuild summary + plots from existing CSVs
```

Four PNGs are written: `memory_vs_fpr.png`, `memory_vs_occupancy.png`, `memory_vs_time.png`,
`unique_events_vs_fpr.png`. Without matplotlib you get a warning with the install command, and the CSVs
and summary are still produced.

## 19. Running the tests

```bash
python -m pytest
python -m pytest --cov=src --cov-report=term-missing    # optional coverage
```

## 20. Sample output

Produced by actually running `python -m src.cli demo` during development (4 KiB, 10 events):

```
Demo with 4 KiB logical budget
  USER_LOGIN:user_104      -> NEW_EVENT
  PAYMENT:txn_205          -> NEW_EVENT
  FILE_UPLOAD:file_309     -> NEW_EVENT
  USER_LOGIN:user_104      -> POSSIBLE_DUPLICATE
  SENSOR_ALERT:sensor_17   -> NEW_EVENT
  PAYMENT:txn_205          -> POSSIBLE_DUPLICATE
  PAGE_VIEW:page_501       -> NEW_EVENT
  USER_LOGIN:user_104      -> POSSIBLE_DUPLICATE
  PAGE_VIEW:page_502       -> NEW_EVENT
  FILE_UPLOAD:file_309     -> POSSIBLE_DUPLICATE
```

Produced by `python -m src.cli experiment` (seed 42, 2000 events, 1000 first-time, 3 timing trials).
**Counts reproduce for the same seed and Python version; the time column will differ on your machine.**
A 1000-event stream is light for 2-8 KiB, so most budgets show zero false positives in this sample, which
does not mean their true false-positive probability is zero (see `unique_sweep.csv` for heavier loads):

```
 KiB    bits   k  events    new    FP  FN   emp.FPR    theory   occ-est  occup.   time(s)
   1    8192   6    2000   1000     4   0   0.00400   0.01960   0.01950   0.519    0.0116
   2   16384  11    2000   1000     0   0   0.00000   0.00038   0.00039   0.490    0.0140
   4   32768  23    2000   1000     0   0   0.00000   0.00000   0.00000   0.505    0.0228
   8   65536  32    2000   1000     0   0   0.00000   0.00000   0.00000   0.388    0.0335
```

Column meanings: `emp.FPR = FP / (FP + TN)` among genuinely new events; `theory` is
`(1 - exp(-k n / m))^k` at the final number of distinct events; `occ-est` is `(X/m)^k`; `occup.` is the
fraction of bits set. These are four different quantities. Why `emp.FPR` is lower than `theory`:
[docs/algorithm_analysis.md](docs/algorithm_analysis.md).

## 21. Mathematical formulas

- Bits: `m = ceil(-n ln(p) / (ln 2)^2)`
- Hashes: `k = (m / n) ln 2`, rounded; this project clamps automatic values to `1..32`
- Theoretical false-positive probability: `p ~ (1 - exp(-k n / m))^k`
- Occupancy-based estimate: `p ~ (X / m)^k`
- Empirical FPR: `FP / (FP + TN)`

Example: `n = 1000`, `p = 0.01` gives `m = 9586` bits (1199 bytes) and `k = 6.64 -> 7`.

## 22. Complexity

Insert and query are `O(k)` hash-position computations (plus input-length cost for SHA-256); space is
`O(m)` bits regardless of how many events are processed. Details: [docs/algorithm_analysis.md](docs/algorithm_analysis.md).

## 23. Expected behaviour

- Inserted events are always reported as possibly present (no false negatives without deletion or tampering).
- Unseen events are usually `NEW_EVENT`, but occasionally `POSSIBLE_DUPLICATE` (false positive).
- A false positive is **not inserted** by the detector (it is classified as possible duplicate), so later
  genuine repeats of it are also flagged, which happens to be correct.
- Smaller budgets and more distinct events mean higher occupancy and more false positives.

## 24. Known limitations

No confirmation of true duplicates; no deletion; no persistence (restart = empty filter); accuracy
degrades past the planned capacity; budgets cover the bit array only. See [docs/limitations.md](docs/limitations.md).

## 25. False-positive explanation

Different events can set overlapping bits. After enough insertions, the `k` bits of a never-seen event
may all already be 1, so the filter says "possibly seen". The filter cannot tell this apart from a
genuine duplicate.

## 26. Comparison with exact duplicate detection

| | Bloom Filter (this project) | Exact set |
|---|---|---|
| Memory | fixed `m` bits | grows with distinct events |
| Answer | definite "new" / probable "seen" | exact |
| False positives | yes | no |
| False negatives | none in normal operation | none |
| Stores original IDs | no | yes |

An exact set is **not** used for detection. It appears only inside `GroundTruthTracker` to score experiments.

## 27. Future improvements

Counting Bloom Filters (deletion), scalable/partitioned filters, persistence to disk, an exact
second-stage check for confirmed duplicates, and larger experiment grids.

## 28. Team contributions

See [docs/team_contributions.md](docs/team_contributions.md) (names are placeholders to be filled in).

## 29. License

MIT; see [LICENSE](LICENSE). Replace the copyright-holder placeholder with your team name.

## 30. References

- B. H. Bloom, "Space/time trade-offs in hash coding with allowable errors", *Communications of the ACM*, 1970.
- A. Kirsch and M. Mitzenmacher, "Less hashing, same performance: building a better Bloom filter", *Random Structures & Algorithms*, 2008.
- Python documentation: `hashlib`, `argparse`, `csv`.
