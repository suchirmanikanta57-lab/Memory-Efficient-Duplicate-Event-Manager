import unittest
from src.core.bloom_filter import BloomFilter
from src.core.two_tier_detector import TwoTierDetector
from src.experiment.false_positive_bench import FalsePositiveBench
from src.model.detection_result import DetectionStatus
from src.model.event import Event


class TestBloomFilter(unittest.TestCase):
    """Automated unit test suite verifying mathematical correctness,
    edge cases, and guarantees of the Bloom Filter implementation.
    """

    def setUp(self):
        # 1,000 items, 1% false positive probability
        self.bf = BloomFilter(expected_elements=1000, target_fp_rate=0.01)

    def test_empty_filter_never_contains_elements(self):
        """Rule 1: An empty filter must never return True for any query."""
        self.assertFalse(self.bf.might_contain("user_login:alice"))
        self.assertFalse(self.bf.might_contain("payment:tx_998822"))
        self.assertEqual(self.bf.inserted_count, 0)
        self.assertEqual(self.bf.get_bits_set_count(), 0)

    def test_added_element_is_always_reported_present(self):
        """Rule 2: Zero False Negatives. If an element was added, might_contain() MUST return True."""
        event_str = "iot:sensor:temperature_reading:zone_4"
        was_new = self.bf.add(event_str)

        self.assertTrue(was_new, "First insertion should flip at least one bit.")
        self.assertTrue(self.bf.might_contain(event_str), "Added element MUST report might_contain() == True.")
        self.assertEqual(self.bf.inserted_count, 1)

    def test_idempotent_duplicate_insertion(self):
        """Rule 3: Re-inserting the same element should succeed without modifying additional bits."""
        event = "order:checkout:order_id_5544"
        first_insert = self.bf.add(event)
        self.assertTrue(first_insert)
        bits_after_first = self.bf.get_bits_set_count()

        second_insert = self.bf.add(event)
        self.assertFalse(second_insert, "Duplicate insertion should not flip any new bits.")
        self.assertEqual(self.bf.get_bits_set_count(), bits_after_first)
        self.assertEqual(self.bf.inserted_count, 2)

    def test_event_object_interoperability(self):
        """Rule 4: Bloom filter correctly accepts Event domain objects."""
        evt = Event(payload="credit_card_charge", event_id="tx_123", source="PAYMENT_GW")
        self.bf.add(evt)
        self.assertTrue(self.bf.might_contain(evt))
        self.assertTrue(self.bf.might_contain(evt.get_identity_string()))

    def test_invalid_parameters_raise_value_errors(self):
        """Rule 5: Defensive parameter validation."""
        # Blank / None inputs
        with self.assertRaises(ValueError):
            self.bf.add("")
        with self.assertRaises(ValueError):
            self.bf.add("   ")

        # Invalid n or p
        with self.assertRaises(ValueError):
            BloomFilter(expected_elements=0, target_fp_rate=0.01)
        with self.assertRaises(ValueError):
            BloomFilter(expected_elements=100, target_fp_rate=0.0)
        with self.assertRaises(ValueError):
            BloomFilter(expected_elements=100, target_fp_rate=1.0)
        with self.assertRaises(ValueError):
            BloomFilter(size_in_bits=-10, hash_count=5)

    def test_optimal_sizing_formulas(self):
        """Rule 6: Verify mathematical sizing calculations against theoretical values."""
        # For n=10,000 and p=0.01 (1%):
        # m = -(10000 * ln(0.01)) / (ln(2)^2) ≈ 95,851 bits ≈ 11,982 bytes
        # k = (95851 / 10000) * ln(2) ≈ 6.64 -> 7 hashes
        m = BloomFilter.calculate_optimal_m(10000, 0.01)
        k = BloomFilter.calculate_optimal_k(m, 10000)

        self.assertAlmostEqual(m, 95851, delta=100)
        self.assertEqual(k, 7)

    def test_two_tier_detector_flow(self):
        """Rule 7: Two-tier architecture distinguishes new events from exact duplicates."""
        two_tier = TwoTierDetector(BloomFilter(expected_elements=100, target_fp_rate=0.01))

        # First time event: Should be DEFINITE_UNIQUE and DB lookup avoided
        r1 = two_tier.process_event("user:login:john")
        self.assertEqual(r1.status, DetectionStatus.DEFINITE_UNIQUE)
        self.assertTrue(r1.is_unique)
        self.assertFalse(r1.is_duplicate)
        self.assertEqual(two_tier.db_lookups_avoided, 1)

        # Second time same event: Should be CONFIRMED_DUPLICATE
        r2 = two_tier.process_event("user:login:john")
        self.assertEqual(r2.status, DetectionStatus.CONFIRMED_DUPLICATE)
        self.assertTrue(r2.is_duplicate)
        self.assertFalse(r2.is_unique)
        self.assertEqual(two_tier.confirmed_duplicates, 1)

    def test_empirical_false_positive_rate_within_bound(self):
        """Rule 8: Empirical false positive rate should be close to target p (statistical tolerance)."""
        # Small fast bench: n=2000, queries=10000, target=5% (0.05)
        report = FalsePositiveBench.run_single_experiment(
            inserted_count=2000,
            test_count=10000,
            target_fp_rate=0.05,
            config_name="Unit Test Trial"
        )
        # Check that observed rate is reasonably close to 5% (within 3.0% margin)
        self.assertLess(report.observed_fp_rate, 8.0)
        self.assertGreater(report.memory_saving_vs_exact_pct, 90.0)


if __name__ == "__main__":
    unittest.main()
