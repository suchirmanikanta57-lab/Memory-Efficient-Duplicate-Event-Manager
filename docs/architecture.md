# Architecture

## Modules

| Module | Responsibility |
|---|---|
| `src/hash_functions.py` | SHA-256 based double hashing; `hash_positions(item, k, m)` |
| `src/bloom_filter.py` | `BloomFilter` (bytearray bit array), sizing formulas, estimates |
| `src/event_detector.py` | `EventDetector`, `EventResult`, ID normalisation, CSV reading, budget conversion |
| `src/event_generator.py` | Deterministic synthetic streams with exact numbers of distinct events |
| `src/metrics.py` | `ConfusionCounts`, `safe_ratio`, **evaluation-only** `GroundTruthTracker` |
| `src/experiment_runner.py` | Experiments, CSV export, summary text, optional plots, bounded simulation |
| `src/cli.py` | `argparse` commands: demo, detect, experiment, simulate, stats, clear-demo |
| `scripts/` | Thin launchers (and `generate_report.py`) that work from any directory |

The "core" (filter, hashing, detector, generator, metrics) is under 500 physical lines in total.

## Data flow (detection path)

```
 event source (CSV rows / generator / list)
        |
        v
 normalize_event_id  --(empty/non-string)--> InvalidEventError / CsvFormatError
        |
        v
 BloomFilter.might_contain(key) --> hash_positions --> check k bits
        |                                   |
   all bits 1                          some bit 0
        |                                   |
 POSSIBLE_DUPLICATE                  add(key); NEW_EVENT
        \_______________ EventResult + counters ___/
```

## Data flow (experiments)

```
 generate_stream(seed) --> events
        |                     \
        v                      v
 EventDetector (prediction)   GroundTruthTracker (truth, set-based, outside the detector)
        \________ ConfusionCounts.record(truth, prediction) ________/
                                 |
                      result row --> CSV / summary / plots
```

The detector never reads the ground truth; the truth is only compared with the detector's output after
the fact. Design decisions: `bytearray` was chosen because its payload size is exactly `ceil(m/8)` bytes,
so the memory budget is easy to state and verify; automatic `k` is clamped to 32 so tiny workloads in big
filters do not compute hundreds of positions per event.
