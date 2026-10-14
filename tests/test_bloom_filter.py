import math

import pytest

from src.bloom_filter import (MAX_AUTO_HASHES, BloomFilter, optimal_bit_count,
                              optimal_hash_count)


def test_init_from_expected_items_and_fpr():
    bf = BloomFilter(1000, 0.01)
    assert bf.bit_array_size == math.ceil(-1000 * math.log(0.01) / math.log(2) ** 2) == 9586
    assert bf.num_hashes == round(9586 / 1000 * math.log(2)) == 7
    assert bf.memory_usage_bytes == math.ceil(9586 / 8)


def test_init_with_explicit_size_and_hashes():
    bf = BloomFilter(bit_array_size=8192, num_hashes=3)
    assert (bf.bit_array_size, bf.num_hashes, bf.memory_usage_bytes) == (8192, 3, 1024)


def test_explicit_size_derives_hashes_from_expected_items():
    assert BloomFilter(1000, bit_array_size=8192).num_hashes == 6


def test_hash_count_is_capped():
    assert optimal_hash_count(65536, 10) == MAX_AUTO_HASHES
    assert optimal_hash_count(8, 1000) == 1


@pytest.mark.parametrize("kwargs", [
    dict(expected_items=0, false_positive_rate=0.01),
    dict(expected_items=-5, false_positive_rate=0.01),
    dict(expected_items=10, false_positive_rate=0.0),
    dict(expected_items=10, false_positive_rate=1.0),
    dict(expected_items=10, false_positive_rate=-0.1),
    dict(bit_array_size=-8, num_hashes=2),
    dict(bit_array_size=0, num_hashes=2),
    dict(bit_array_size=64, num_hashes=0),
    dict(bit_array_size=64, num_hashes=-1),
    dict(bit_array_size=64),
    dict(expected_items=10),
    dict(),
    dict(expected_items=10, false_positive_rate=0.01, bit_array_size=64),
    dict(bit_array_size=64.5, num_hashes=2),
    dict(bit_array_size=True, num_hashes=2),
])
def test_invalid_configuration_raises(kwargs):
    with pytest.raises(ValueError):
        BloomFilter(**kwargs)


def test_formula_helpers_validate():
    with pytest.raises(ValueError):
        optimal_bit_count(10, 1.5)
    with pytest.raises(ValueError):
        optimal_hash_count(0, 10)


def test_add_and_query_new_item():
    bf = BloomFilter(bit_array_size=4096, num_hashes=4)
    assert not bf.might_contain("alpha")
    newly = bf.add("alpha")
    assert 1 <= newly <= 4
    assert bf.might_contain("alpha")
    assert bf.bit_set_count == newly


def test_no_false_negatives_for_inserted_items():
    bf = BloomFilter(500, 0.01)
    items = [f"PAYMENT:txn_{i}" for i in range(500)]
    for item in items:
        bf.add(item)
    assert all(bf.might_contain(item) for item in items)


def test_repeated_insertion_sets_no_new_bits():
    bf = BloomFilter(bit_array_size=4096, num_hashes=4)
    bf.add("x")
    before = bf.bit_set_count
    assert bf.add("x") == 0
    assert bf.bit_set_count == before
    assert bf.items_added == 2
    assert bf.might_contain("x")


def test_unseen_item_query_on_empty_filter_is_negative():
    assert not BloomFilter(100, 0.01).might_contain("never added")


def test_clear_resets_everything():
    bf = BloomFilter(bit_array_size=1024, num_hashes=3)
    bf.add("a")
    bf.add("b")
    bf.clear()
    assert bf.bit_set_count == 0 and bf.items_added == 0 and bf.occupancy_ratio == 0.0
    assert not bf.might_contain("a")
    assert bf.memory_usage_bytes == 128


def test_bit_set_count_matches_actual_bits():
    bf = BloomFilter(bit_array_size=2048, num_hashes=5)
    for i in range(100):
        bf.add(f"e{i}")
    assert bf.bit_set_count == sum(bin(b).count("1") for b in bf._bits)


def test_occupancy_and_estimates():
    bf = BloomFilter(bit_array_size=1000, num_hashes=2)
    assert bf.occupancy_ratio == 0 and bf.estimated_false_positive_rate == 0
    bf.add("a")
    assert bf.occupancy_ratio == bf.bit_set_count / 1000
    assert bf.estimated_false_positive_rate == pytest.approx((bf.bit_set_count / 1000) ** 2)


def test_theoretical_rate_matches_formula():
    bf = BloomFilter(bit_array_size=8192, num_hashes=6)
    expected = (1 - math.exp(-6 * 1000 / 8192)) ** 6
    assert bf.expected_false_positive_rate(1000) == pytest.approx(expected)
    assert bf.expected_false_positive_rate(0) == 0
    with pytest.raises(ValueError):
        bf.expected_false_positive_rate(-1)


def test_theoretical_rate_defaults_to_items_added():
    bf = BloomFilter(bit_array_size=8192, num_hashes=6)
    for i in range(10):
        bf.add(str(i))
    assert bf.expected_false_positive_rate() == bf.expected_false_positive_rate(10)


def test_object_size_exceeds_payload():
    bf = BloomFilter(bit_array_size=8192, num_hashes=3)
    assert bf.object_size_bytes > bf.memory_usage_bytes


@pytest.mark.parametrize("item", ["", "naïve café", "🚀", "a,b;c\"d", "line\nbreak", b"raw-bytes"])
def test_empty_unicode_special_items(item):
    bf = BloomFilter(bit_array_size=2048, num_hashes=3)
    bf.add(item)
    assert bf.might_contain(item)


def test_non_multiple_of_eight_size():
    bf = BloomFilter(bit_array_size=13, num_hashes=2)
    assert bf.memory_usage_bytes == 2
    for i in range(50):
        bf.add(str(i))
    assert bf.bit_set_count <= 13
