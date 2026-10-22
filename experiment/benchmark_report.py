from dataclasses import dataclass


@dataclass
class BenchmarkReport:
    """Holds analytical and empirical metrics from a Bloom Filter experiment."""
    config_name: str
    items_inserted: int
    test_queries_count: int
    bits_count_m: int
    hash_count_k: int
    memory_bytes: int
    false_positives_count: int
    observed_fp_rate: float
    theoretical_fp_rate: float
    execution_time_ms: float
    memory_saving_vs_exact_pct: float

    def format_row(self) -> str:
        """Formats the report as a clean table row."""
        mem_str = f"{self.memory_bytes / 1024:.2f} KB" if self.memory_bytes >= 1024 else f"{self.memory_bytes} B"
        return (
            f"| {self.config_name:<20} | {self.items_inserted:>7,} | {self.bits_count_m:>8,} | "
            f"{self.hash_count_k:>2} | {mem_str:>9} | {self.false_positives_count:>5,} | "
            f"{self.observed_fp_rate:>8.4f}% | {self.theoretical_fp_rate:>8.4f}% | {self.memory_saving_vs_exact_pct:>6.1f}% |"
        )
