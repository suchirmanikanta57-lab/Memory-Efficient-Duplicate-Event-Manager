from unittest import mock

import pytest

from src.bloom_filter import BloomFilter
from src.event_detector import (NEW_EVENT, POSSIBLE_DUPLICATE, CsvFormatError, EventDetector,
                                InvalidEventError, memory_budget_to_bits, normalize_event_id)


@pytest.fixture
def detector():
    return EventDetector(BloomFilter(bit_array_size=65536, num_hashes=5))


def test_negative_filter_result_is_new_event(detector):
    with mock.patch.object(detector.bloom_filter, "might_contain", return_value=False):
        result = detector.process_event("PAYMENT:txn_1")
    assert result.classification == NEW_EVENT
    assert result.inserted and not result.might_have_been_seen
    assert detector.bloom_filter.bit_set_count > 0


def test_positive_filter_result_is_possible_duplicate_not_inserted(detector):
    with mock.patch.object(detector.bloom_filter, "might_contain", return_value=True), \
            mock.patch.object(detector.bloom_filter, "add") as add:
        result = detector.process_event("PAYMENT:txn_1")
    assert result.classification == POSSIBLE_DUPLICATE == "POSSIBLE_DUPLICATE"
    assert result.might_have_been_seen and not result.inserted
    add.assert_not_called()


def test_repeated_event_is_flagged(detector):
    first = detector.process_event("USER_LOGIN:user_104")
    second = detector.process_event("USER_LOGIN:user_104")
    assert first.classification == NEW_EVENT
    assert second.classification == POSSIBLE_DUPLICATE


def test_result_fields_and_counters(detector):
    results = detector.process_events(["a:1", "b:2", "a:1", "a:1"])
    assert [r.event_count for r in results] == [1, 2, 3, 4]
    assert [r.possible_duplicate_count for r in results] == [0, 0, 1, 2]
    last = results[-1]
    assert last.occupancy == detector.bloom_filter.occupancy_ratio
    assert last.estimated_false_positive_rate == detector.bloom_filter.estimated_false_positive_rate
    summary = detector.summary()
    assert summary["events_processed"] == 4
    assert summary["classified_new"] == 2
    assert summary["classified_possible_duplicate"] == 2
    assert summary["memory_bytes_logical"] == 8192


def test_reset(detector):
    detector.process_events(["a", "b", "a"])
    detector.reset()
    assert detector.event_count == 0 and detector.possible_duplicate_count == 0
    assert detector.bloom_filter.bit_set_count == 0
    assert detector.process_event("a").classification == NEW_EVENT


def test_whitespace_is_stripped(detector):
    detector.process_event("  PAYMENT:txn_9  ")
    assert detector.process_event("PAYMENT:txn_9").classification == POSSIBLE_DUPLICATE


def test_matching_is_case_sensitive(detector):
    detector.process_event("Payment:txn_9")
    assert detector.process_event("PAYMENT:TXN_9").classification == NEW_EVENT


@pytest.mark.parametrize("bad", ["", "   ", "\t\n", None, 42])
def test_invalid_event_ids_rejected(detector, bad):
    with pytest.raises(InvalidEventError):
        detector.process_event(bad)
    assert detector.event_count == 0


def test_normalize_event_id():
    assert normalize_event_id(" x ") == "x"


def test_from_memory_budget_sizes():
    for kib in (1, 2, 4, 8):
        d = EventDetector.from_memory_budget(kib * 1024, 500)
        assert d.bloom_filter.bit_array_size == kib * 1024 * 8
        assert d.bloom_filter.memory_usage_bytes == kib * 1024
    with pytest.raises(ValueError):
        memory_budget_to_bits(0)
    with pytest.raises(ValueError):
        memory_budget_to_bits(-1)


def test_csv_processing(detector, tmp_path):
    f = tmp_path / "e.csv"
    f.write_text("event_id,event_type,timestamp\nA:1,A,t1\nB:2,B,t2\nA:1,A,t3\n", encoding="utf-8")
    results = detector.process_csv(f)
    assert [r.classification for r in results] == [NEW_EVENT, NEW_EVENT, POSSIBLE_DUPLICATE]


def test_csv_custom_id_column(detector, tmp_path):
    f = tmp_path / "e.csv"
    f.write_text("id,kind\nX,1\nX,2\n", encoding="utf-8")
    assert detector.process_csv(f, id_column="id")[1].classification == POSSIBLE_DUPLICATE


def test_csv_sample_file_is_parsed_not_collapsed():
    d = EventDetector(BloomFilter(bit_array_size=65536, num_hashes=5))
    results = d.process_csv("data/sample_events.csv")
    assert len(results) == 60
    assert sum(r.classification == NEW_EVENT for r in results) >= 30


@pytest.mark.parametrize("content,fragment", [
    ("", "empty"),
    ("a,b\n1,2\n", "no 'event_id' column"),
    ("event_id,t\nA,1,extra\n", "line 2"),
    ("event_id,t\nA\n", "line 2"),
    ("event_id,t\n,5\n", "line 2"),
    ("event_id,t\n   ,5\n", "line 2"),
])
def test_malformed_csv_raises(detector, tmp_path, content, fragment):
    f = tmp_path / "bad.csv"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(CsvFormatError, match=fragment):
        detector.process_csv(f)


def test_malformed_rows_can_be_skipped(detector, tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("event_id,t\nA,1\n,2\nB,3\nC\n", encoding="utf-8")
    results = detector.process_csv(f, skip_invalid=True)
    assert len(results) == 2 and detector.skipped_rows == 2
    assert detector.summary()["skipped_rows"] == 2


def test_missing_file_raises_oserror(detector, tmp_path):
    with pytest.raises(OSError):
        detector.process_csv(tmp_path / "nope.csv")
