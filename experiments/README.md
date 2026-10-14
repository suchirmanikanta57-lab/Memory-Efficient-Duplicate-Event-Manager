# Experiments

Run from the repository root:

```bash
python -m src.cli experiment --plots
```

Files written to `experiments/results/` (git-ignored except `.gitkeep`):

| File | Content |
|---|---|
| `memory_comparison.csv` | One row per memory budget on the same stream (k tuned to the expected unique count) |
| `unique_sweep.csv` | Budgets x numbers of distinct events, with k fixed (default 4, `--sweep-hashes`) |
| `hash_sweep.csv` | Budgets x numbers of hash functions on the same stream |
| `summary.txt` | Technical summary built from the CSV rows |
| `*.png` | Plots (only with `--plots` and matplotlib installed) |

Column definitions and methodology: `docs/experimental_methodology.md`. An empty `empirical_fpr` cell
means the denominator was zero (no first-time events).
