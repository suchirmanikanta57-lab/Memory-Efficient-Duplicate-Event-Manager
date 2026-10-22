# Memory-Limited Duplicate Event Detector Using Bloom Filter

[![Language](https://img.shields.io/badge/Language-Python%203.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(Standard%20Library)-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-100%25%20Passing-success.svg)]()

> A space-efficient, high-performance event deduplication engine implemented in **pure Python 3**. Demonstrates probabilistic set membership, mathematical parameter sizing, empirical false-positive analysis, and a two-tier database query-avoidance architecture.

---

## Table of Contents
1. [Overview](#1-overview)
2. [Problem Statement & Motivation](#2-problem-statement--motivation)
3. [Core DSA Concepts](#3-core-dsa-concepts)
4. [Architecture & System Design](#4-architecture--system-design)
5. [Mathematical Foundation](#5-mathematical-foundation)
6. [Empirical Experimental Results](#6-empirical-experimental-results)
7. [Complexity Analysis](#7-complexity-analysis)
8. [Project Structure](#8-project-structure)
9. [Quick Start & Execution](#9-quick-start--execution)
10. [Running Automated Tests](#10-running-automated-tests)
11. [GitHub Upload Instructions](#11-github-upload-instructions)
12. [License](#12-license)

---

## 1. Overview

In modern event-driven architectures (financial payment gateways, IoT sensor networks, distributed logging, user clickstream ingestion), millions of discrete events stream into the platform every minute. Detecting and eliminating duplicate events is critical to preventing duplicate transactions and skewed data analytics.

This project implements a **Memory-Limited Duplicate Event Detector** in Python 3 that uses a **Bloom Filter** as a front-line probabilistic filter (Tier 1) combined with an exact store (Tier 2).

### Key Highlights
- **Zero External Dependencies**: Implemented entirely with Python's built-in standard library (`bytearray`, `hashlib`, `math`, `time`, `dataclasses`, `unittest`).
- **>98% RAM Savings**: Compresses 10,000 event tracking states from ~1.14 MB down to 11.76 KB.
- **Zero False Negatives**: Guaranteed mathematically never to drop or misidentify an unseen event.
- **Controlled False Positives**: Mathematically bounded error rates verified through scientific empirical benchmarks.
- **Kirsch-Mitzenmacher Hashing**: Generates $k$ independent hash positions using two 64-bit base hashes ($h_1$ and $h_2$).

---

## 2. Problem Statement & Motivation

### The Naive Approach
A naive deduplication engine stores all incoming event IDs in an in-memory hash set (such as Python's `set()` or Redis `SET`).

```text
Incoming Event String: "user_login:user_987421:session_881273:ip_192.168.1.101"
Raw String Size: ~70 bytes
Python Set Overhead: ~64 bytes per entry
Total RAM per event: ~134 bytes

For 100,000,000 events:
100,000,000 * 134 bytes ≈ 13.4 GB of expensive server RAM!
```

### The Bloom Filter Solution
Instead of storing full event strings, a Bloom Filter uses an array of single bits. An event is hashed to $k$ bit indices and the corresponding bits are set to `1`.

For 10,000 events at a 1% false positive rate:
- **Python Set**: ~1.14 MB
- **Bloom Filter**: **11.76 KB** (**98.9% memory savings!**)

---

## 3. Core DSA Concepts

| Concept | Explanation |
| :--- | :--- |
| **Bloom Filter** | A space-efficient probabilistic data structure that tests whether an element is a member of a set. |
| **Bit Array** | A contiguous memory buffer of bits (0 or 1). In Python, implemented using `bytearray((m + 7) // 8)`. |
| **Hash Collision** | When two distinct inputs produce the same hash position in the bit array. |
| **False Positive** | When the filter reports an event is present (`might_contain == True`), but it was never actually inserted. |
| **Zero False Negatives** | If an event was inserted, its $k$ bits are set to 1. Querying it will always find all $k$ bits set to 1. A standard Bloom filter **never** says an item is absent when it was actually added. |

---

## 4. Architecture & System Design

The application utilizes a **Two-Tier Hybrid Deduplication Pipeline**:

```
             +----------------------------+
             |   Incoming Event Stream    |
             +----------------------------+
                           |
                           v
        +--------------------------------------+
        | Tier 1: Bloom Filter (In-Memory RAM) |
        |   - O(k) Nanosecond Screening        |
        |   - 11.76 KB Footprint (10k items)   |
        +--------------------------------------+
                     /            \
 might_contain() == False     might_contain() == True
                   /                \
                  v                  v
    +------------------------+  +---------------------------------+
    |  DEFINITELY UNIQUE     |  |   Candidate Duplicate Detected  |
    |  - Add to Bloom Filter |  +---------------------------------+
    |  - Add to DB Storage   |                  |
    |  - DB Query AVOIDED!   |                  v
    +------------------------+  +---------------------------------+
                                | Tier 2: Exact Store / Database  |
                                +---------------------------------+
                                       /                     \
                                Match in DB              Not in DB
                                    /                         \
                                   v                           v
                      +-----------------------+   +-----------------------+
                      |  CONFIRMED DUPLICATE  |   |  FALSE POSITIVE       |
                      |  - Reject duplicate   |   |  - Caught by Tier 2!  |
                      |  - Zero data loss     |   |  - Insert to DB       |
                      +-----------------------+   +-----------------------+
```

### Component Roles
1. **Tier 1 (Bloom Filter)**: Filters out 100% of genuinely fresh events. Saves 90%+ of expensive database lookups.
2. **Tier 2 (Exact Store)**: Serves as the ground-truth authority when Tier 1 detects a potential match. Eliminates false positives completely.

---

## 5. Mathematical Foundation

### 1. Optimal Bit Array Size ($m$)
$$m = -\frac{n \cdot \ln(p)}{(\ln 2)^2}$$
- $n$: Number of expected events.
- $p$: Target false-positive probability ($0 < p < 1$).

### 2. Optimal Number of Hash Functions ($k$)
$$k = \frac{m}{n} \cdot \ln(2)$$

### 3. Theoretical False-Positive Probability
$$p = \left( 1 - e^{-\frac{k \cdot n}{m}} \right)^k$$

### 4. Kirsch-Mitzenmacher Double Hashing
Rather than calculating $k$ independent cryptographic hash functions, we compute two 64-bit base hashes ($h_1$ via FNV-1a and $h_2$ via Murmur3 bit mixing) and synthesize $k$ positions:
$$g_i(x) = (h_1(x) + i \cdot h_2(x)) \pmod m \quad \text{for } i \in [0, k-1]$$

---

## 6. Empirical Experimental Results

Controlled experiment executed with **10,000 inserted items** and **50,000 unseen query items**:

| Configuration | Events ($n$) | Bits ($m$) | Hashes ($k$) | Memory | False Positives | Observed FP % | Theoretical FP % | Memory Saved vs Set |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Low Memory (p=5%)** | 10,000 | 62,353 | 4 | **7.67 KB** | 2,423 | 4.8460% | 5.0268% | **99.3%** |
| **Balanced (p=1%)** | 10,000 | 95,851 | 7 | **11.76 KB** | 503 | 1.0060% | 1.0039% | **98.9%** |
| **High Precision (p=0.1%)** | 10,000 | 143,776 | 10 | **17.61 KB** | 41 | 0.0820% | 0.1000% | **98.4%** |

> **Key Finding**: The experimentally observed false positive rate (1.0060%) matches the theoretical prediction (1.0039%) within a 0.002% margin of error!

---

## 7. Complexity Analysis

| Operation | Time Complexity | Space Complexity | Description |
| :--- | :---: | :---: | :--- |
| **`add(event)`** | $\mathcal{O}(k)$ | $\mathcal{O}(1)$ | Computes $h_1, h_2$ and sets $k$ bits to 1. |
| **`might_contain(event)`** | $\mathcal{O}(k)$ | $\mathcal{O}(1)$ | Checks $k$ bits with early exit on first 0. |
| **Bit Array Storage** | $\mathcal{O}(1)$ | $\mathcal{O}(m)$ | Flat `bytearray` allocated in memory. |
| **Two-Tier Query** | $\mathcal{O}(k)$ average | $\mathcal{O}(m + N_{\text{unique}})$ | 100% of new events resolved without DB access. |

---

## 8. Project Structure

```text
BloomFilterEventDetector_Python/
│
├── main.py                     # Top-level executable entry point
├── run_detector.bat            # One-click Windows batch launcher
├── requirements.txt            # Zero-dependency specification
├── LICENSE                     # MIT Open Source License
├── .gitignore                  # Git ignore rules
├── README.md                   # Complete architectural documentation
│
├── src/                        # Core Python Application Source Code
│   ├── __init__.py
│   ├── model/                  # Domain Data Models
│   │   ├── __init__.py
│   │   ├── event.py            # Event object with payload, timestamp, and UUID
│   │   └── detection_result.py # DetectionStatus enum and screening telemetry
│   ├── hash/                   # Hashing Algorithms
│   │   ├── __init__.py
│   │   └── hash_strategy.py    # 64-bit FNV-1a + Murmur3 Kirsch-Mitzenmacher
│   ├── core/                   # Bloom Filter Data Structure Engine
│   │   ├── __init__.py
│   │   ├── bloom_filter.py     # Pure bytearray bit array implementation
│   │   └── two_tier_detector.py# Hybrid Bloom Filter + Exact Store Deduplicator
│   ├── experiment/             # Scientific Benchmarking Suite
│   │   ├── __init__.py
│   │   ├── benchmark_report.py # Metrics DTO
│   │   └── false_positive_bench.py # Empirical false-positive lab
│   └── ui/                     # Interactive Presentation Layer
│       ├── __init__.py
│       └── console_app.py      # 8-option interactive CLI menu
│
├── tests/                      # Automated Test Suite (100% Pass)
│   ├── __init__.py
│   └── test_bloom_filter.py    # 8 automated unit tests
│
└── docs/                       # Technical & Academic Documentation
    ├── algorithm.md            # Deep mathematical derivations & proofs
    ├── requirements.md         # Software Requirements Specification (SRS)
    ├── testing.md              # Test matrix & QA report
    └── viva-questions.md       # College viva & technical interview Q&A
```

---

## 9. Quick Start & Execution

### Prerequisites
- Python 3.8 or higher installed on your machine.
- Verify Python installation:
  ```bash
  python --version
  ```

### Running the Application

#### Option A: Windows One-Click
Double-click the **`run_detector.bat`** file in the project directory.

#### Option B: Terminal Command
```bash
cd C:\BloomFilterEventDetector_Python
python main.py
```

### Interactive Menu Options
```text
=================================================================
                        MAIN MENU
=================================================================
 1. Add an Event to Bloom Filter
 2. Query Event (Screen for Possible Duplicate)
 3. View Bloom Filter Statistics & Memory Telemetry
 4. Run Empirical False-Positive Experiment (Scientific Trial)
 5. Compare Bloom Filter Configurations (Memory vs Accuracy)
 6. Two-Tier Exact Verification Mode (Hybrid L1 + L2 Architecture)
 7. Reconfigure Bloom Filter Parameters (Custom m, k or n, p)
 8. Exit
=================================================================
```

---

## 10. Running Automated Tests

Run the built-in test discovery from the project root:

```bash
cd C:\BloomFilterEventDetector_Python
python -m unittest discover tests -v
```

All 8 unit tests execute in ~0.2 seconds and verify zero false negatives, parameter sizing, exception handling, and empirical error bounds.

---

## 11. GitHub Upload Instructions

### Method 1: Upload via GitHub Web Browser (Easiest & Fastest)
1. Open your web browser and go to [github.com/new](https://github.com/new).
2. Repository name: `BloomFilter-Duplicate-Event-Detector`.
3. Choose **Public**, leave "Add a README" **unchecked**, and click **Create repository**.
4. Click the link **"uploading an existing file"**.
5. Drag and drop all files and folders from `C:\BloomFilterEventDetector_Python\` into GitHub.
6. Commit changes with message: `"Initial release of Bloom Filter Duplicate Event Detector in Python"`.

### Method 2: Upload via Git Command Line
```bash
cd C:\BloomFilterEventDetector_Python
git init
git add .
git commit -m "Initial commit: Pure Python 3 Bloom Filter Event Detector"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/BloomFilter-Duplicate-Event-Detector.git
git push -u origin main
```

---

## 12. License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
