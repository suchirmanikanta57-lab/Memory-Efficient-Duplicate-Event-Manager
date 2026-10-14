import pytest

from src.event_generator import generate_stream
from src.metrics import ConfusionCounts, GroundTruthTracker, safe_ratio


def test_safe_ratio():
    assert safe_ratio(1, 4) == 0.25
    assert safe_ratio(0, 5) == 0.0
    assert safe_ratio(3, 0) is None


def test_confusion_counts_and_derived_values():
    c = ConfusionCounts()
    for truth, pred in [(False, False), (False, True), (True, True), (True, True), (True, False), (False, False)]:
        c.record(truth, pred)
    assert (c.tp, c.fp, c.tn, c.fn) == (2, 1, 2, 1)
    assert c.total == 6 and c.actual_repeats == 3 and c.first_time_events == 3
    assert c.flagged_possible_duplicate == 3 and c.classified_new == 3
    assert c.false_positive_rate == pytest.approx(1 / 3)
    assert c.false_negative_rate == pytest.approx(1 / 3)
    assert c.possible_duplicate_share == pytest.approx(0.5)


def test_rates_are_distinct_quantities():
    c = ConfusionCounts(tp=10, fp=1, tn=9, fn=0)
    assert c.false_positive_rate == pytest.approx(0.1)
    assert c.possible_duplicate_share == pytest.approx(11 / 20)


def test_zero_denominators():
    c = ConfusionCounts()
    assert c.false_positive_rate is None and c.false_negative_rate is None
    assert c.possible_duplicate_share is None
    only_repeats = ConfusionCounts(tp=5)
    assert only_repeats.false_positive_rate is None
    assert only_repeats.false_negative_rate == 0.0


def test_ground_truth_tracker():
    g = GroundTruthTracker()
    assert g.observe("a") is False
    assert g.observe("a") is True
    assert g.observe("b") is False


def test_generator_is_deterministic_and_exact():
    a = list(generate_stream(300, 120, seed=7))
    assert a == list(generate_stream(300, 120, seed=7))
    assert a != list(generate_stream(300, 120, seed=8))
    assert len(a) == 300 and len(set(a)) == 120


def test_generator_first_occurrence_precedes_repeats_and_format():
    seen = set()
    for e in generate_stream(200, 50, seed=3):
        assert ":" in e and e.split(":")[0].isupper()
        seen.add(e)
    assert len(seen) == 50


@pytest.mark.parametrize("n,u", [(0, 0), (5, 5), (5, 1), (1, 1)])
def test_generator_edge_cases(n, u):
    s = list(generate_stream(n, u, 1))
    assert len(s) == n and len(set(s)) == u


@pytest.mark.parametrize("n,u", [(5, 6), (-1, 0), (3, -1), (3, 0)])
def test_generator_invalid(n, u):
    with pytest.raises(ValueError):
        list(generate_stream(n, u, 1))
