# Limitations

- **False positives.** `POSSIBLE_DUPLICATE` may be a new event. The application never calls it confirmed.
- **No exact confirmation.** Confirming needs a second, exact mechanism (e.g. a database lookup). This project does not include one.
- **Capacity planning.** `m` and `k` are chosen for an expected number of distinct events. Exceeding it raises occupancy and the false-positive probability, and the filter cannot grow.
- **Filling effect.** Accuracy worsens continuously as bits fill; `unique_sweep.csv` shows this.
- **Hashing cost.** Each event costs one SHA-256 digest (proportional to ID length) plus `k` position computations; SHA-256 is chosen for stability and explainability, not speed.
- **Memory accounting.** The budget covers the logical bit array only. Python objects, the interpreter, CSV results held in memory (`process_csv` returns a list) and experiment ground truth use more.
- **No deletion.** A standard Bloom Filter cannot remove one item (clearing a bit could erase other items). Only `clear()` resets everything. Deletion is **not implemented**.
- **No persistence.** State lives in memory only; nothing is saved or recovered.
- **Restart effect.** After a restart the filter is empty: previously seen events are reported `NEW_EVENT` again, so duplicates across restarts are missed. This is not a false negative of the structure; it is lost state.
- **Normalisation.** IDs are trimmed but case-sensitive; `A:1` and `a:1` are different events.
- **Not a security control.** SHA-256 is used for distribution, not for secrecy.
- **Synthetic experiments.** Results describe the generated streams and chosen parameters only.
