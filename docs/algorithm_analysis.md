# Algorithm Analysis

All numbers below were recomputed with Python's `math` module while writing this document.

## Time complexity
With `k` positions per operation:

- Insert: `O(k)`; query: `O(k)`; `process_event`: `O(k)` (one query plus, for new events, one insert).
- For a configured `k`, cost does not grow with the number of previously processed events.
- SHA-256 costs time proportional to the ID length, so strictly each operation is `O(L + k)` for an ID of
  length `L`. CSV parsing and printing add their own costs.
- Throughput trade-off: larger `k` means more bit checks per event. Measured times in `hash_sweep.csv` are
  noisy single-machine medians and are not a universal guarantee.

## Space complexity
- Filter bits: `O(m)`, fixed at creation; processing more events does **not** enlarge it.
- Logical bit-array size: `ceil(m / 8)` bytes (`BloomFilter.memory_usage_bytes`).
- Python object size: `sys.getsizeof` of the bytearray adds object overhead (`object_size_bytes`).
- Total process memory: interpreter, modules, result lists and the CLI use far more than the bit array.
- Experiments additionally hold an exact `set` of IDs (ground truth) plus the generated stream. That grows
  with the dataset and is **not** part of the production filter.

Comparison with an exact set (conceptual): for 1000 IDs of 17 characters, `sys.getsizeof(set)` was 32,984
bytes on this machine's Python 3.12 *before* counting the 1000 string objects (58,000 bytes by the same
measure), versus 1,024 logical bytes for a 1 KiB filter. A set is exact; the filter is approximate. Values
vary across Python versions.

## Sizing formulas and their limits
`m = ceil(-n ln p / (ln 2)^2)`, `k = (m/n) ln 2`. They assume hash positions are independent and uniform,
`n` is known in advance, and `n` is large; they are approximations. `k` must be an integer, so rounding
moves the real rate slightly off target. Our automatic `k` is clamped to 1..32.

Worked example: `n = 1000`, `p = 0.01`: `m = 9586` bits (9.586 bits per item, 1199 bytes), `k = 6.6445`, rounded to 7.

## False-positive estimates
- Theoretical: `(1 - exp(-k n / m))^k`. Example: 1 KiB (`m = 8192`), `n = 1000`, `k = 6`:
  `exp(-6000/8192) = 0.4807`, so `p = (1 - 0.4807)^6 = 0.01960`.
- Occupancy-based: `(X / m)^k`, using the bits actually set. In the same run `X/m = 0.519`, giving
  `0.519^6 = 0.0195`, close to the theory.
- Empirical: `FP / (FP + TN)` measured on the stream.

**Why empirical can be lower than the final-state theory.** The empirical rate is averaged over the whole
stream, while the filter is emptier early on. For `m = 8192`, `k = 6`, `n = 1000`, the average of
`(1 - exp(-k i / m))^k` over `i = 0..999` is 0.00366, versus 0.01960 at `i = 1000`. The measured
0.00400 (4 of 1000 first-time events, seed 42) sits near the first number. Other sources of difference:
finite samples (small counts are noisy), hash imperfection, and the detector not inserting false-positive
events (which keeps occupancy a little lower).

## Budgets at n = 1000 (automatic k, theory)

| Budget | m (bits) | k | Theoretical p |
|---|---|---|---|
| 1 KiB | 8192 | 6 | 1.960e-02 |
| 2 KiB | 16384 | 11 | 3.823e-04 |
| 4 KiB | 32768 | 23 | 1.456e-07 |
| 8 KiB | 65536 | 32 (clamped from 45) | 6.058e-14 |

Capacity at `p = 0.01` by the ideal formula: 854, 1709, 3418 and 6837 items for 1, 2, 4, 8 KiB.

## Trade-offs
- More memory -> lower false-positive probability for the same `n`.
- More inserted events -> higher occupancy -> higher false-positive probability.
- `k` too small -> weak filtering; `k` too large -> bits fill quickly and every operation costs more
  (see `hash_sweep.csv`: at 1 KiB and n = 1000 the empirical rate was lowest near `k = 6`, the formula's choice, in the seed-42 run; a single run is only suggestive).
- Occupancy is not the false-positive rate; the share of events flagged as possible duplicates is neither.
