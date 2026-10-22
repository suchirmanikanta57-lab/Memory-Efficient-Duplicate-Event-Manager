import time
from typing import List
from src.core.bloom_filter import BloomFilter
from src.experiment.benchmark_report import BenchmarkReport


class FalsePositiveBench:
    """Scientific experiment harness for measuring empirical false-positive rates
    and comparing them against theoretical mathematical limits.
    """

    @staticmethod
    def run_single_experiment(inserted_count: int = 10000, test_count: int = 50000,
                                target_fp_rate: float = 0.01,
                                config_name: str = "Standard 1% Target") -> BenchmarkReport:
        """Runs a controlled empirical trial:
        1. Inserts `inserted_count` unique synthetic events into a clean Bloom Filter.
        2. Queries `test_count` completely separate, non-overlapping events.
        3. Measures exact number of false positives (where filter returned True).
        4. Calculates observed false positive rate = (FP / test_count) * 100%.
        """
        bf = BloomFilter(expected_elements=inserted_count, target_fp_rate=target_fp_rate)

        start_time = time.perf_counter()

        # Step 1: Insert known items
        for i in range(inserted_count):
            bf.add(f"urn:event:sensor:temperature:{i}:verified")

        # Step 2: Query disjoint, non-inserted items
        false_positives = 0
        for j in range(test_count):
            # Guaranteed never inserted
            test_event = f"urn:event:unseen:synthetic_test:{j}:probe"
            if bf.might_contain(test_event):
                false_positives += 1

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        observed_fp_pct = (false_positives / test_count) * 100.0 if test_count > 0 else 0.0
        theoretical_fp_pct = bf.get_theoretical_fp_rate() * 100.0

        # Memory estimation:
        # Bloom Filter memory: (m + 7) // 8 bytes
        bf_memory = bf.get_memory_usage_bytes()
        # In Python, an exact set storing 10,000 strings (~50 bytes string + ~64 bytes hash table entry)
        # consumes ~114 bytes per item = ~1,140,000 bytes (~1.14 MB).
        est_exact_memory = inserted_count * 114
        memory_saving_pct = max(0.0, ((est_exact_memory - bf_memory) / est_exact_memory) * 100.0)

        return BenchmarkReport(
            config_name=config_name,
            items_inserted=inserted_count,
            test_queries_count=test_count,
            bits_count_m=bf.size_in_bits,
            hash_count_k=bf.hash_count,
            memory_bytes=bf_memory,
            false_positives_count=false_positives,
            observed_fp_rate=observed_fp_pct,
            theoretical_fp_rate=theoretical_fp_pct,
            execution_time_ms=elapsed_ms,
            memory_saving_vs_exact_pct=memory_saving_pct
        )

    @staticmethod
    def compare_configurations(inserted_count: int = 10000, test_count: int = 50000) -> List[BenchmarkReport]:
        """Compares three distinct trade-off configurations:
        - Config A: Tight Budget (p = 0.05 / 5% target) -> Minimum memory, highest FP rate.
        - Config B: Balanced (p = 0.01 / 1% target)     -> Production standard.
        - Config C: High Precision (p = 0.001 / 0.1%)   -> High accuracy, larger bit array.
        """
        configs = [
            ("Low Memory (p=5%)", 0.05),
            ("Balanced (p=1%)", 0.01),
            ("High Precision (p=0.1%)", 0.001),
        ]

        reports = []
        for name, p in configs:
            report = FalsePositiveBench.run_single_experiment(
                inserted_count=inserted_count,
                test_count=test_count,
                target_fp_rate=p,
                config_name=name
            )
            reports.append(report)

        return reports
