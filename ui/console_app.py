import sys
from typing import Optional
from src.core.bloom_filter import BloomFilter
from src.core.two_tier_detector import TwoTierDetector
from src.experiment.false_positive_bench import FalsePositiveBench
from src.model.detection_result import DetectionStatus


class ConsoleApp:
    """Interactive command-line interface for the Duplicate Event Detector."""

    BANNER = r"""
=============================================================================
*  MEMORY-LIMITED DUPLICATE EVENT DETECTOR USING BLOOM FILTER & HASH FUNCTIONS *
*                   Data Structures & Algorithms Case Study                   *
*                      Pure Python 3 High-Performance Engine                  *
=============================================================================
"""

    def __init__(self):
        # Default sizing: 10,000 expected events, 1.0% error rate
        self.bloom_filter = BloomFilter(expected_elements=10000, target_fp_rate=0.01)
        self.two_tier_detector = TwoTierDetector(self.bloom_filter)

    def print_menu(self):
        print("\n" + "=" * 65)
        print("                        MAIN MENU")
        print("=" * 65)
        print(" 1. Add an Event to Bloom Filter")
        print(" 2. Query Event (Screen for Possible Duplicate)")
        print(" 3. View Bloom Filter Statistics & Memory Telemetry")
        print(" 4. Run Empirical False-Positive Experiment (Scientific Trial)")
        print(" 5. Compare Bloom Filter Configurations (Memory vs Accuracy)")
        print(" 6. Two-Tier Exact Verification Mode (Hybrid L1 + L2 Architecture)")
        print(" 7. Reconfigure Bloom Filter Parameters (Custom m, k or n, p)")
        print(" 8. Exit")
        print("=" * 65)

    def run(self):
        print(self.BANNER)
        print(f"[*] Initialized Bloom Filter with m={self.bloom_filter.size_in_bits:,} bits, "
              f"k={self.bloom_filter.hash_count} hash functions.")
        print(f"[*] Memory Footprint: {self.bloom_filter.get_memory_usage_bytes()} bytes "
              f"({self.bloom_filter.get_memory_usage_bytes() / 1024:.2f} KB)")

        while True:
            self.print_menu()
            choice = input("\nEnter your choice (1-8): ").strip()

            if choice == "1":
                self.handle_add_event()
            elif choice == "2":
                self.handle_query_event()
            elif choice == "3":
                self.handle_view_stats()
            elif choice == "4":
                self.handle_fp_experiment()
            elif choice == "5":
                self.handle_compare_configs()
            elif choice == "6":
                self.handle_two_tier_mode()
            elif choice == "7":
                self.handle_reconfigure()
            elif choice == "8":
                print("\nThank you for using the Duplicate Event Detector. Goodbye!\n")
                sys.exit(0)
            else:
                print("[!] Invalid choice! Please select an option between 1 and 8.")

    def handle_add_event(self):
        print("\n--- [1] ADD AN EVENT ---")
        event = input("Enter event payload or description (e.g. 'user_login:alice:ip_192.168.1.1'): ").strip()
        if not event:
            print("[!] Error: Event cannot be blank.")
            return

        positions = self.bloom_filter.get_bit_positions(event)
        was_new = self.bloom_filter.add(event)

        print(f"\n[+] Event successfully processed:")
        print(f"    Payload:        \"{event}\"")
        print(f"    Hash Positions: {positions}")
        print(f"    Status:         {'At least one bit was newly set to 1' if was_new else 'All hash bits were already set to 1'}")
        print(f"    Total Inserted: {self.bloom_filter.inserted_count:,} events")

    def handle_query_event(self):
        print("\n--- [2] QUERY EVENT (PROBABILISTIC SCREENING) ---")
        event = input("Enter event to check: ").strip()
        if not event:
            print("[!] Error: Event cannot be blank.")
            return

        positions = self.bloom_filter.get_bit_positions(event)
        might_exist = self.bloom_filter.might_contain(event)

        print(f"\n--- QUERY RESULT ---")
        print(f"Event:          \"{event}\"")
        print(f"Hash Positions: {positions}")

        if not might_exist:
            print("\n>>> RESULT: DEFINITELY ABSENT (Zero Duplicate Chance) <<<")
            print("Explanation: At least one calculated bit position in the bit array was 0.")
            print("A Bloom Filter has ZERO FALSE NEGATIVES. This event has NEVER been inserted before.")
        else:
            print("\n>>> RESULT: POSSIBLY PRESENT (Potential Duplicate or False Positive) <<<")
            print("Explanation: All k calculated bit positions were found set to 1.")
            print(f"Current Theoretical False Positive Probability: {self.bloom_filter.get_theoretical_fp_rate() * 100:.4f}%")
            print("Note: If 100% certainty is needed, inspect Tier 2 Exact Storage (Option 6).")

    def handle_view_stats(self):
        print("\n" + self.bloom_filter.get_stats_summary())

    def handle_fp_experiment(self):
        print("\n--- [4] RUN EMPIRICAL FALSE-POSITIVE EXPERIMENT ---")
        print("This experiment measures the actual observed false-positive rate vs mathematical formula.")

        try:
            n_str = input("Number of unique events to insert [default: 10,000]: ").strip()
            inserted_count = int(n_str) if n_str else 10000

            q_str = input("Number of disjoint test queries to check [default: 50,000]: ").strip()
            test_count = int(q_str) if q_str else 50000

            p_str = input("Target false-positive probability (0.001 - 0.20) [default: 0.01]: ").strip()
            target_p = float(p_str) if p_str else 0.01
        except ValueError:
            print("[!] Invalid numerical input. Aborting experiment.")
            return

        print(f"\n[*] Executing trial: Inserting {inserted_count:,} events, testing {test_count:,} disjoint events...")
        report = FalsePositiveBench.run_single_experiment(inserted_count, test_count, target_p)

        print("\n" + "=" * 65)
        print("                    EXPERIMENT RESULTS")
        print("=" * 65)
        print(f"Configuration:              {report.config_name}")
        print(f"Events Inserted (n):        {report.items_inserted:,}")
        print(f"Disjoint Queries Tested:    {report.test_queries_count:,}")
        print(f"Bit Array Size (m):         {report.bits_count_m:,} bits ({report.memory_bytes / 1024:.2f} KB)")
        print(f"Hash Functions (k):         {report.hash_count_k}")
        print(f"Observed False Positives:   {report.false_positives_count:,}")
        print(f"Observed False Positive %:  {report.observed_fp_rate:.4f}%")
        print(f"Theoretical Expected %:     {report.theoretical_fp_rate:.4f}%")
        print(f"Delta (|Observed - Target|): {abs(report.observed_fp_rate - (target_p * 100)):.4f}%")
        print(f"Estimated Memory Savings:   {report.memory_saving_vs_exact_pct:.1f}% vs Python exact set")
        print(f"Execution Latency:          {report.execution_time_ms:.2f} ms")
        print("=" * 65)

    def handle_compare_configs(self):
        print("\n--- [5] COMPARE BLOOM FILTER CONFIGURATIONS ---")
        print("Running comparative benchmark across 3 distinct memory/accuracy configurations...")
        print("Inserting 10,000 events, testing 50,000 disjoint events for each config...\n")

        reports = FalsePositiveBench.compare_configurations(10000, 50000)

        header = (
            f"| {'Configuration':<20} | {'Events':>7} | {'Bits (m)':>8} | "
            f"{'k':>2} | {'Memory':>9} | {'FP Cnt':>6} | {'Obs FP %':>9} | {'Theo FP %':>9} | {'Saved %':>7} |"
        )
        sep = "-" * len(header)

        print(sep)
        print(header)
        print(sep)
        for r in reports:
            print(r.format_row())
        print(sep)
        print("\nKey Takeaway:")
        print("1. As target false positive drops (5% -> 0.1%), bits 'm' and hashes 'k' increase.")
        print("2. Even the highest precision config (0.1%) uses under 19 KB for 10,000 events!")
        print("3. An equivalent exact hash set in memory would consume ~1.14 MB (over 98% memory savings!).")

    def handle_two_tier_mode(self):
        print("\n--- [6] TWO-TIER EXACT VERIFICATION MODE ---")
        print("Combines Bloom Filter (Tier 1 fast screener) + Exact Storage (Tier 2 DB confirmation).")
        print("Options:")
        print("  a. Ingest and verify an individual event")
        print("  b. Run batch demonstration (1,000 mixed events)")
        print("  c. View Two-Tier Telemetry")
        print("  d. Back to main menu")

        sub_choice = input("Select sub-option (a/b/c/d): ").strip().lower()

        if sub_choice == "a":
            event = input("Enter event payload: ").strip()
            if not event:
                print("[!] Event cannot be blank.")
                return
            result = self.two_tier_detector.process_event(event)
            print(f"\n{result.to_display_string()}")

        elif sub_choice == "b":
            print("\n[*] Simulating stream of 1,000 events (700 unique, 300 duplicates)...")
            for i in range(700):
                self.two_tier_detector.process_event(f"stream:event:id_{i}")
            for i in range(300):
                # Duplicate events from the first 300
                self.two_tier_detector.process_event(f"stream:event:id_{i}")

            print("[+] Stream processing complete!")
            print(f"\n{self.two_tier_detector.get_stats_summary()}")

        elif sub_choice == "c":
            print(f"\n{self.two_tier_detector.get_stats_summary()}")

    def handle_reconfigure(self):
        print("\n--- [7] RECONFIGURE BLOOM FILTER PARAMETERS ---")
        print("1. Sizing by Expected Elements (n) and Target FP Rate (p)")
        print("2. Explicit sizing by Bit Array Size (m) and Hash Functions (k)")

        mode = input("Select sizing strategy (1 or 2): ").strip()
        try:
            if mode == "1":
                n = int(input("Expected elements (n): ").strip())
                p = float(input("Target false-positive rate (e.g. 0.01 for 1%): ").strip())
                self.bloom_filter = BloomFilter(expected_elements=n, target_fp_rate=p)
            elif mode == "2":
                m = int(input("Bit array size in bits (m): ").strip())
                k = int(input("Number of hash functions (k): ").strip())
                self.bloom_filter = BloomFilter(size_in_bits=m, hash_count=k)
            else:
                print("[!] Invalid strategy selected.")
                return

            self.two_tier_detector = TwoTierDetector(self.bloom_filter)
            print(f"\n[+] Successfully reconfigured Bloom Filter!")
            print(f"    Bits (m):   {self.bloom_filter.size_in_bits:,} ({self.bloom_filter.get_memory_usage_bytes()} bytes)")
            print(f"    Hashes (k): {self.bloom_filter.hash_count}")
        except Exception as e:
            print(f"[!] Reconfiguration failed: {e}")
