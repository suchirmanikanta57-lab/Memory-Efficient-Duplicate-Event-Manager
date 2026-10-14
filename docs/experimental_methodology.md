# Experimental Methodology

## Dataset generation
`generate_stream(num_events, num_unique, seed)` yields exactly `num_unique` distinct IDs among
`num_events` events. At each step it either creates a new ID (`TYPE:id_000123`, type chosen from five
categories) or repeats a uniformly chosen earlier ID. The probability of creating a new ID is
`remaining_new / remaining_steps`, so the target count is always met and a first occurrence always
precedes its repeats. It uses a private `random.Random(seed)`: same arguments, same stream.

## Ground-truth tracking
`GroundTruthTracker` (in `metrics.py`) is an exact `set`. It is used **only** in `experiment_runner.py`,
**after** the detector has answered, to label each event as truly seen or truly new. The detector never
sees it, so detection stays Bloom-Filter-only.

## Controlled experiments
For each configuration a fresh filter is built and the same stream is processed in order.

| Experiment | Varies | Fixed |
|---|---|---|
| `memory_comparison` | 1, 2, 4, 8 KiB | stream; k = optimal for the unique count (clamped 1..32) |
| `unique_sweep` | number of distinct events (stream = 2x that many events) | k (default 4); seed |
| `hash_sweep` | k (1, 2, 3, 4, 6, 8, 12) | stream; budget |

Holding k fixed in `unique_sweep` isolates the effect of load. In `memory_comparison`, k is tuned per
budget, so differences combine memory and k.

## Metrics
Positive = flagged `POSSIBLE_DUPLICATE`. TP: genuine repeat flagged. FP: first-time event flagged.
TN: first-time event reported new. FN: genuine repeat reported new (expected 0).

- `empirical_fpr = FP / (FP + TN)`; blank in CSV / `N/A` on screen when the denominator is 0.
- `theoretical_fpr = (1 - exp(-k n / m))^k` with `n` = first-time events (final state).
- `occupancy_estimated_fpr = (X/m)^k` from the final bit count.
- `occupancy = X/m`, `memory_bytes_logical = ceil(m/8)`, `time_median_s` / `time_min_s` over trials.

These are different quantities; the share of all events flagged is not the false-positive rate.

## Reproducibility
Counts depend only on seed and parameters (verified by running the experiment twice and comparing all
non-timing columns, and by automated tests). Timing is measured with `time.perf_counter` around event
processing only, repeated `--trials` times with a fresh filter; the median and minimum are reported. Timings
depend on machine load and Python version.

## Interpreting results
- Zero observed false positives in a sample does not prove the true probability is zero; with `N` new events
  the smallest nonzero rate observable is `1/N`.
- If an experiment has no first-time events the FPR is undefined and is reported as such.
- Empirical rates are averaged over a filling filter, so they are expected to be below the final-state
  theoretical value (see `algorithm_analysis.md`).

## Sources of bias
Synthetic IDs share a regular format; SHA-256 behaves close to uniformly, but real traffic may be skewed
(e.g. heavily repeated hot keys, which cause fewer distinct insertions than events). One seed is one sample:
rerun with other `--seed` values for variance. Parameters such as the 2x stream length are arbitrary choices.
The detector does not insert false positives, which slightly lowers occupancy compared with inserting every event.
