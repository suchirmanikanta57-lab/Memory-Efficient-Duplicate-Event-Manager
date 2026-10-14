import pytest

from src.hash_functions import base_hashes, hash_positions, to_bytes


def test_identical_input_is_reproducible():
    assert hash_positions("PAYMENT:txn_205", 5, 1000) == hash_positions("PAYMENT:txn_205", 5, 1000)


def test_str_and_equivalent_bytes_match():
    assert hash_positions("abc", 3, 500) == hash_positions(b"abc", 3, 500)


def test_different_inputs_usually_differ():
    assert hash_positions("event_a", 6, 10**6) != hash_positions("event_b", 6, 10**6)


@pytest.mark.parametrize("size", [1, 2, 7, 64, 8192, 65536])
def test_positions_within_range(size):
    for item in ("a", "b", "", "USER_LOGIN:user_1", "ünï"):
        positions = hash_positions(item, 20, size)
        assert len(positions) == 20
        assert all(0 <= p < size for p in positions)


def test_requested_number_of_positions():
    assert len(hash_positions("x", 1, 100)) == 1
    assert len(hash_positions("x", 9, 100)) == 9


def test_step_is_never_zero_for_size_above_one():
    for i in range(2000):
        _, h2 = base_hashes(f"item{i}", 97)
        assert h2 != 0


def test_zero_step_adjusted_to_one(monkeypatch):
    class FakeDigest:
        def digest(self):
            return (5).to_bytes(16, "big") + (0).to_bytes(16, "big")

    monkeypatch.setattr("src.hash_functions.hashlib.sha256", lambda data: FakeDigest())
    assert base_hashes("anything", 10) == (5, 1)


@pytest.mark.parametrize("item", ["", "😀 emoji", "日本語", "tab\tnew\nline", "quote\"'\\", "a" * 10000])
def test_empty_unicode_and_special_strings(item):
    positions = hash_positions(item, 4, 1024)
    assert positions == hash_positions(item, 4, 1024)
    assert all(0 <= p < 1024 for p in positions)


def test_invalid_arguments():
    with pytest.raises(ValueError):
        hash_positions("x", 0, 10)
    with pytest.raises(ValueError):
        hash_positions("x", 1, 0)
    with pytest.raises(TypeError):
        to_bytes(123)  # type: ignore[arg-type]
