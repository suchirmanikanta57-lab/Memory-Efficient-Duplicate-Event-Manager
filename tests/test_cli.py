import csv
from pathlib import Path

import pytest

from src import cli

SAMPLE = str(Path(__file__).resolve().parents[1] / "data" / "sample_events.csv")


def run(capsys, *argv):
    code = cli.main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_help_output(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for command in ("demo", "detect", "experiment", "stats", "clear-demo", "simulate"):
        assert command in out


def test_demo(capsys):
    code, out, _ = run(capsys, "demo", "--memory-kb", "2")
    assert code == 0 and "POSSIBLE_DUPLICATE" in out and "NEW_EVENT" in out
    assert "NOT a confirmed" in out


def test_detect_sample(capsys):
    code, out, _ = run(capsys, "detect", "--input", SAMPLE, "--memory-kb", "4", "--show-events")
    assert code == 0 and "events processed       : 60" in out


def test_detect_output_file_and_target_fpr(capsys, tmp_path):
    target = tmp_path / "o" / "res.csv"
    code, out, _ = run(capsys, "detect", "--input", SAMPLE, "--target-fpr", "0.01",
                       "--expected-events", "100", "--output", str(target))
    assert code == 0 and target.is_file()
    with target.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 60 and {r["classification"] for r in rows} <= {"NEW_EVENT", "POSSIBLE_DUPLICATE"}
    assert any(r["classification"] == "POSSIBLE_DUPLICATE" for r in rows)


def test_missing_input_file(capsys, tmp_path):
    code, out, err = run(capsys, "detect", "--input", str(tmp_path / "missing.csv"))
    assert code == 1 and "not found" in err and "Traceback" not in err


def test_malformed_csv_exit_code(capsys, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("event_id,t\n,1\n", encoding="utf-8")
    code, _, err = run(capsys, "detect", "--input", str(bad))
    assert code == 1 and "line 2" in err and "Traceback" not in err
    code, out, _ = run(capsys, "detect", "--input", str(bad), "--skip-invalid")
    assert code == 0 and "skipped malformed rows : 1" in out


def test_non_utf8_file_is_reported(capsys, tmp_path):
    f = tmp_path / "latin.csv"
    f.write_bytes(b"event_id\n\xff\xfe\n")
    code, _, err = run(capsys, "detect", "--input", str(f))
    assert code == 1 and err.startswith("error:")


@pytest.mark.parametrize("argv", [
    ["detect"],
    ["demo", "--memory-kb", "3"],
    ["detect", "--input", SAMPLE, "--memory-kb", "4", "--target-fpr", "0.01"],
    ["detect", "--input", SAMPLE, "--target-fpr", "1.5"],
    ["experiment", "--memory-kb", "16"],
    ["experiment", "--num-events", "0"],
    ["bogus"],
    [],
])
def test_invalid_arguments_exit_2(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2


def test_experiment_writes_outputs(capsys, tmp_path):
    code, out, _ = run(capsys, "experiment", "--memory-kb", "1", "2", "--num-events", "200",
                       "--unique-events", "100", "--unique-counts", "20", "40", "--hash-counts", "1", "2",
                       "--trials", "1", "--output-dir", str(tmp_path), "--seed", "9")
    assert code == 0
    for name in ("memory_comparison.csv", "unique_sweep.csv", "hash_sweep.csv", "summary.txt"):
        assert (tmp_path / name).is_file()
    with (tmp_path / "memory_comparison.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["memory_bits"] for r in rows] == ["8192", "16384"]
    assert "TECHNICAL SUMMARY" in out


def test_experiment_is_reproducible(capsys, tmp_path):
    def counts(sub):
        d = tmp_path / sub
        run(capsys, "experiment", "--memory-kb", "1", "--num-events", "300", "--unique-events", "150",
            "--unique-counts", "30", "--hash-counts", "2", "--trials", "1", "--output-dir", str(d), "--seed", "4")
        with (d / "memory_comparison.csv").open(encoding="utf-8", newline="") as f:
            return [{k: v for k, v in r.items() if not k.startswith("time_")} for r in csv.DictReader(f)]
    assert counts("a") == counts("b")


def test_experiment_with_plots(capsys, tmp_path):
    pytest.importorskip("matplotlib")
    code, out, _ = run(capsys, "experiment", "--memory-kb", "1", "--num-events", "100", "--unique-events", "50",
                       "--unique-counts", "10", "20", "--hash-counts", "2", "--trials", "1",
                       "--output-dir", str(tmp_path), "--plots")
    assert code == 0 and (tmp_path / "memory_vs_fpr.png").is_file()


def test_experiment_rejects_unique_above_events(capsys, tmp_path):
    code, _, err = run(capsys, "experiment", "--num-events", "10", "--unique-events", "20",
                       "--output-dir", str(tmp_path))
    assert code == 1 and "cannot exceed" in err


def test_simulate_stats_and_clear_demo(capsys):
    code, out, _ = run(capsys, "simulate", "--iterations", "300", "--report-every", "100")
    assert code == 0 and out.count("\n") >= 5
    code, out, _ = run(capsys, "stats", "--memory-kb", "1", "8", "--items", "500")
    assert code == 0 and "8192 bits" in out and "65536 bits" in out
    code, out, _ = run(capsys, "clear-demo")
    assert code == 0 and "occupancy 0.0000" in out and "-> NEW_EVENT (the filter has forgotten" in out


def test_module_entry_point_runs():
    import subprocess, sys
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run([sys.executable, "-m", "src.cli", "demo"], cwd=root, capture_output=True, text=True)
    assert proc.returncode == 0 and "POSSIBLE_DUPLICATE" in proc.stdout
