import pytest

from src import experiment_runner as xr


def det(row):
    """Deterministic (non-timing) part of a result row."""
    return {k: v for k, v in row.items() if not k.startswith("time_")}


def test_run_single_is_reproducible_except_timing():
    a = xr.run_single("t", 1, 400, 200, seed=5, trials=2)
    b = xr.run_single("t", 1, 400, 200, seed=5, trials=2)
    assert det(a) == det(b)


def test_different_seed_changes_stream_not_totals():
    a = xr.run_single("t", 1, 400, 200, seed=1, trials=1)
    b = xr.run_single("t", 1, 400, 200, seed=2, trials=1)
    assert a["total_events"] == b["total_events"] == 400
    assert a["first_time_events"] == b["first_time_events"] == 200


def test_confusion_counts_are_consistent():
    r = xr.run_single("t", 1, 3000, 1500, seed=11, trials=1)
    assert r["true_positives"] + r["false_positives"] + r["true_negatives"] + r["false_negatives"] == r["total_events"]
    assert r["first_time_events"] == r["false_positives"] + r["true_negatives"] == 1500
    assert r["actual_repeats"] == r["true_positives"] + r["false_negatives"] == 1500
    assert r["classified_new"] + r["classified_possible_duplicate"] == r["total_events"]
    assert r["false_negatives"] == 0
    assert r["empirical_fpr"] == pytest.approx(r["false_positives"] / r["first_time_events"])
    assert r["false_positives"] > 0  # 1 KiB is heavily overloaded by 1500 unique events


def test_memory_budget_conversion_in_results():
    rows = xr.memory_comparison([1, 2, 4, 8], 200, 100, seed=1, trials=1)
    assert [r["memory_bits"] for r in rows] == [8192, 16384, 32768, 65536]
    assert [r["memory_bytes_logical"] for r in rows] == [1024, 2048, 4096, 8192]
    assert all(r["false_negatives"] == 0 for r in rows)


def test_stream_without_repeats_has_zero_repeat_counts():
    row = xr.run_single("t", 1, 1, 1, seed=1, trials=1)
    assert row["first_time_events"] == 1 and row["actual_repeats"] == 0
    assert row["false_negatives"] == 0 and row["empirical_fpr"] == 0.0


def test_empty_stream_gives_undefined_rates():
    r = xr.run_single("t", 1, 0, 0, seed=1, trials=1)
    assert r["total_events"] == 0 and r["empirical_fpr"] is None


def test_invalid_experiment_parameters():
    with pytest.raises(ValueError):
        xr.validate_memory_kib([3])
    with pytest.raises(ValueError):
        xr.validate_memory_kib([])
    with pytest.raises(ValueError):
        xr.run_single("t", 1, 10, 5, trials=0)
    with pytest.raises(ValueError):
        xr.run_single("t", 1, 5, 10)


def test_sweeps_have_expected_shape():
    sweep = xr.unique_sweep([1, 2], [20, 40, 60], seed=1, trials=1, num_hashes=3)
    assert len(sweep) == 6 and {r["num_hashes"] for r in sweep} == {3}
    rows = xr.hash_sweep([1], [1, 2, 3], 100, 50, seed=1, trials=1)
    assert [r["num_hashes"] for r in rows] == [1, 2, 3]


def test_csv_round_trip_with_none(tmp_path):
    rows = xr.memory_comparison([1], 0 + 50, 25, seed=1, trials=1)
    rows.append(xr.run_single("t", 1, 0, 0, seed=1, trials=1))
    path = xr.write_results_csv(rows, tmp_path / "sub" / "r.csv")
    back = xr.read_results_csv(path)
    assert len(back) == 2 and back[1]["empirical_fpr"] is None
    assert back[0]["total_events"] == 50 and back[0]["memory_bits"] == 8192
    assert list(back[0].keys()) == list(xr.RESULT_FIELDS)


def test_summary_and_table_text():
    rows = xr.memory_comparison([1, 8], 200, 100, seed=1, trials=1)
    text = xr.build_summary(rows)
    assert "TECHNICAL SUMMARY" in text and "1 KiB" in text and "not process RAM" in text
    assert "N/A" in xr.format_table([xr.run_single("t", 1, 0, 0, seed=1, trials=1)])
    assert "No memory-comparison" in xr.build_summary([])


def test_simulation_is_bounded_and_ends_at_iterations():
    snaps = list(xr.simulate(250, 1, seed=1, report_every=100))
    assert [s["processed"] for s in snaps] == [100, 200, 250]
    assert all(s["new"] + s["possible_duplicates"] == s["processed"] for s in snaps)
    with pytest.raises(ValueError):
        list(xr.simulate(0, 1))


def test_plots_created(tmp_path):
    pytest.importorskip("matplotlib")
    mem = xr.memory_comparison([1, 2], 200, 100, seed=1, trials=1)
    sweep = xr.unique_sweep([1, 2], [20, 40], seed=1, trials=1)
    saved = xr.generate_plots(tmp_path, mem, sweep)
    assert sorted(p.name for p in saved) == ["memory_vs_fpr.png", "memory_vs_occupancy.png",
                                              "memory_vs_time.png", "unique_events_vs_fpr.png"]
    assert all(p.stat().st_size > 0 for p in saved)


def test_plots_unavailable_message(tmp_path, monkeypatch):
    import builtins
    real = builtins.__import__

    def fake(name, *a, **k):
        if name.startswith("matplotlib"):
            raise ImportError("no matplotlib")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    with pytest.raises(xr.PlottingUnavailableError, match="requirements-dev"):
        xr.generate_plots(tmp_path, [], [])
