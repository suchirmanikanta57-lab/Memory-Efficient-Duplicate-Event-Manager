# Viva Questions and Answers

**1. Why did you choose a Bloom Filter?**
We need to test membership of a stream of events in fixed, small memory. A Bloom Filter uses a constant number of bits regardless of how many events arrive, at the price of occasional false positives.

**2. How does a Bloom Filter work?**
It has `m` bits and `k` hash positions per item. Insertion sets those bits; a query checks them. Any 0 bit means "definitely not seen"; all 1s means "possibly seen".

**3. What is the bit array, and how did you store it?**
A row of `m` bits, initially 0. We store it in a `bytearray` of `ceil(m/8)` bytes; bit `p` is `bytes[p // 8] & (1 << (p % 8))`. Its payload size is exactly the byte budget, which makes memory limits easy to state.

**4. Why not Python's built-in `hash()`?**
String hashing is randomised per process, so positions would change between runs and break reproducibility. We use SHA-256, which is deterministic.

**5. What is double hashing?**
We compute one digest, split it into `h1` and `h2`, and use `(h1 + i*h2) mod m` for `i = 0..k-1`. It gives `k` positions from one hash computation and is easy to explain.

**6. Why must `h2` be nonzero?**
If `h2 mod m` were 0, all `k` positions would equal `h1`, so the filter would behave as if `k = 1`. We replace 0 by 1.

**7. What is a false positive?**
A never-inserted event whose `k` bits were all already set by other events, so the filter answers "possibly seen".

**8. Can a standard Bloom Filter produce false negatives?**
Not in normal operation. Insertion sets bits to 1 and nothing clears them (except `clear()`), so an inserted item's bits remain 1. Deletion or corrupting the array would break this.

**9. What is the optimal number of hash functions?**
`k = (m/n) ln 2`, rounded. At that value about half the bits are set when `n` items are inserted. Too few hashes filter weakly; too many fill the array fast. We clamp automatic values to 1..32.

**10. How do you size the filter for a target error rate?**
`m = ceil(-n ln p / (ln 2)^2)`. For `n = 1000`, `p = 0.01` this gives 9586 bits (1199 bytes) and `k = 6.64`, rounded to 7.

**11. What is the space complexity?**
`O(m)` bits, fixed at creation; it does not grow with the number of processed events. The whole Python process uses more than the bit array.

**12. What is the time complexity?**
`O(k)` per insert or query, plus the cost of hashing the ID (proportional to its length). For fixed `k` it does not depend on how many events were seen before.

**13. How does capacity planning work?**
Pick the expected number of distinct events `n` and a target `p`, then compute `m` and `k`. If more than `n` distinct events arrive, occupancy and false positives rise; the filter cannot be resized.

**14. Why doesn't the filter store the original events?**
It stores only bits, which is the source of its memory efficiency. This also means it cannot list events or confirm a duplicate.

**15. How does it compare with a Python `set`?**
A set is exact and stores every ID, so memory grows with distinct events. The filter has fixed memory but gives probabilistic "possible" answers. We use a set only in `GroundTruthTracker` to evaluate experiments, never for detection.

**16. Why do theoretical and empirical false-positive rates differ?**
The theory value used is the final-state rate after all `n` inserts, while the measured rate averages over a filling filter. Also, samples are finite and hashes are not perfectly uniform. For 1 KiB, `n = 1000`, `k = 6` the final-state theory is 0.0196 and the fill-averaged theory is 0.00366; the measured seed-42 value was 0.00400.

**17. What happens when memory is reduced?**
`m` shrinks, occupancy for the same data rises, and the false-positive probability increases. The `memory_comparison` and `unique_sweep` experiments measure this.

**18. How is the experiment validated?**
Ground truth is tracked separately in a set; each event's prediction is compared with truth to build TP/FP/TN/FN. Tests check count consistency (TP+FP+TN+FN = total), reproducibility for equal seeds, zero false negatives, and budget-to-bits conversion.

**19. Why can't the detector confirm duplicates?**
A positive answer is produced both by true repeats and by false positives, and the filter holds no information to tell them apart. So we label it `POSSIBLE_DUPLICATE`.

**20. What is the difference between occupancy and false-positive rate?**
Occupancy is the fraction of bits set (`X/m`). The false-positive probability is roughly `(X/m)^k`; the empirical FPR is `FP/(FP+TN)` over new events. A half-full filter with `k = 6` has a probability near `0.5^6 = 0.0156`, not 0.5.

**21. Why is the empirical FPR defined over new events only?**
A false positive can only happen for an event that is genuinely new. Repeats flagged correctly are true positives. Including them in the denominator would mix different populations.

**22. How do you handle zero denominators?**
`safe_ratio` returns `None` (blank in CSV, `N/A` on screen) rather than inventing 0 or crashing, e.g. when a stream has no first-time events.

**23. What if an experiment shows zero false positives?**
We report zero for that sample. It does not prove the true probability is zero; with `N` new events we can only resolve rates around `1/N`.

**24. What are real-world applications?**
Web crawlers (visited URLs), databases and caches (avoid disk lookups for missing keys), blocklists, network monitoring and event de-duplication.

**25. What happens when the application restarts?**
The in-memory filter is empty, so old events are `NEW_EVENT` again. Persistence is not implemented; this is lost state, not a false negative of the structure itself.

**26. Does the memory budget cap total RAM use?**
No. It fixes the logical bit-array size only. The interpreter, objects, result lists and experiment ground truth use additional memory.

**27. Why is case sensitivity a design choice?**
Different IDs like `A:1` and `a:1` may be different events; merging them carelessly could hide real events. Whitespace is trimmed; empty IDs are rejected rather than merged.

**28. Why is a false-positive event not inserted?**
The detector inserts only events classified `NEW_EVENT`. A false positive is classified as a possible duplicate, so no insertion occurs. Its bits are already set, so a later repeat is flagged anyway.

**29. How would you add deletion?**
A Counting Bloom Filter replaces bits with small counters that can be decremented, at several times the memory. It is listed as future work and is not implemented here.

**30. What future enhancements would you make?**
Persistence to disk, scalable filters that grow, an exact second-stage check to confirm duplicates, counting filters, and larger multi-seed experiments with confidence intervals.
