# Software Requirements Specification (SRS)

## Project Title
**Memory-Limited Duplicate Event Detector Using Bloom Filter and Hash Functions**

---

## 1. Problem Statement

High-throughput distributed systems (financial payments, IoT sensor grids, microservice logging, clickstream trackers) process millions of events per second. Deduplicating these incoming events is vital to prevent double-billing, skewed metrics, and wasted processing cycles.

Traditional approaches store all previously seen event identities in a hash set, database, or key-value store (e.g., Redis). However:
- Storing 100,000,000 raw strings requires **gigabytes to tens of gigabytes of expensive RAM**.
- Querying a persistent database for every incoming event creates an I/O bottleneck.

An ultra-compact, high-speed preliminary screening mechanism is required to screen events before querying secondary storage.

---

## 2. Proposed Solution

We implement a **Two-Tier Duplicate Event Detection Architecture** in pure Python 3:
1. **Tier 1 (Probabilistic Screener - Bloom Filter)**:
   - Uses a compact `bytearray` bit array in RAM.
   - Sized optimally via mathematical formulas to guarantee a target false-positive rate (e.g., $1\%$).
   - Completely filters out genuinely new events in $\mathcal{O}(k)$ nanosecond time without touching secondary storage.
2. **Tier 2 (Exact Verification - Persistent Storage / DB)**:
   - Only queried when Tier 1 flags an event as a candidate duplicate.
   - Eliminates false positives, providing $100\%$ detection accuracy with minimal memory/query overhead.

---

## 3. Project Objectives

1. Demonstrate how a Bloom Filter reduces memory footprint by over **$95\%$** compared to standard hash sets.
2. Formulate and verify optimal bit-array sizing ($m$) and hash function count ($k$).
3. Implement Kirsch-Mitzenmacher double hashing using 64-bit FNV-1a and Murmur3 bit mixing.
4. Experimentally measure empirical false-positive rates and compare them against theoretical bounds.
5. Provide a two-tier architecture where the Bloom filter acts as an L1 database-query-saving cache.

---

## 4. Functional Requirements

| Req ID | Description |
| :--- | :--- |
| **FR-1** | **Add Event**: Ingest an event string or `Event` domain object, compute $k$ hash positions, and set bits to 1. |
| **FR-2** | **Query Event**: Screen an event to return `DEFINITELY_ABSENT` (if any bit is 0) or `POSSIBLY_PRESENT` (if all bits are 1). |
| **FR-3** | **Telemetry Display**: Output $m$, $k$, memory usage, bits set, fill ratio, and theoretical false positive probability. |
| **FR-4** | **Scientific Experiment**: Run automated false positive trials with $n$ inserted items and $Q$ unseen test queries to measure observed vs theoretical rates. |
| **FR-5** | **Configuration Comparator**: Benchmark and contrast three configurations ($5\%$, $1\%$, $0.1\%$). |
| **FR-6** | **Two-Tier Engine**: Combine Bloom Filter screening with exact store verification, tracking saved database queries and resolved false positives. |
| **FR-7** | **Interactive CLI**: Provide a clean terminal menu with defensive input validation and help instructions. |

---

## 5. Non-Functional Requirements

- **Zero External Dependencies**: Pure Python 3 standard library only (`bytearray`, `hashlib`, `math`, `time`, `dataclasses`, `unittest`).
- **Low Latency**: Event screening operations must complete within microseconds ($\mu s$).
- **Defensive Error Handling**: Empty strings, invalid menu choices, and non-positive parameters must be gracefully intercepted.
- **Portability**: Must run seamlessly across Windows 10/11, macOS, and Linux on Python 3.8+.

---

## 6. Success Criteria

1. **Zero False Negatives**: $100\%$ guarantee that an inserted item will never be marked as absent.
2. **Predictable False Positives**: Observed empirical false positive rates must match theoretical formulas within a standard deviation of $\pm 0.5\%$.
3. **Memory Savings**: Greater than $90\%$ RAM savings compared to exact set storage.
4. **Automated Test Coverage**: 100% test pass rate across all edge cases in `tests/test_bloom_filter.py`.
