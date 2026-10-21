from typing import List


class HashStrategy:
    """High-performance, deterministic hashing engine for the Bloom Filter.

    Implements the Kirsch-Mitzenmacher optimization technique:
    Instead of calculating k independent hash passes, it calculates two
    independent 64-bit hashes (h1 and h2) and generates k unique bit positions using:

        g_i(x) = (h1(x) + i * h2(x)) mod m      for i = 0, 1, ..., k-1

    Reference: Kirsch, A., & Mitzenmacher, M. (2006).
    "Less Hashing, Same Performance: Building a Better Bloom Filter."
    """

    # 64-bit FNV-1a constants
    FNV_64_INIT = 0xcbf29ce484222325
    FNV_64_PRIME = 0x100000001b3
    MASK_64 = 0xFFFFFFFFFFFFFFFF

    @staticmethod
    def get_bit_positions(input_str: str, m: int, k: int) -> List[int]:
        """Computes k unique bit positions in range [0, m - 1] for an input string.

        :param input_str: The event string to hash
        :param m: The total bit-array size (must be > 0)
        :param k: The number of hash functions (must be > 0)
        :return: A list of k integer bit indices
        """
        if not input_str:
            raise ValueError("Input string for hashing cannot be null or empty.")
        if m <= 0 or k <= 0:
            raise ValueError("m and k must be strictly positive integers.")

        data = input_str.encode("utf-8")

        # 1. Compute two independent 64-bit hash values
        h1 = HashStrategy.fnv1a64(data)
        h2 = HashStrategy.murmur64(data)

        # Guard: ensure h2 is never 0 so each step advances
        if h2 == 0:
            h2 = 0x517cc1b727220a95

        # 2. Generate k positions via Kirsch-Mitzenmacher linear combination
        positions = []
        for i in range(k):
            combined = (h1 + i * h2) & HashStrategy.MASK_64
            positions.append(combined % m)

        return positions

    @staticmethod
    def fnv1a64(data: bytes) -> int:
        """Computes a 64-bit Fowler-Noll-Vo (FNV-1a) hash with excellent bit avalanche."""
        h = HashStrategy.FNV_64_INIT
        for b in data:
            h = (h ^ b) & HashStrategy.MASK_64
            h = (h * HashStrategy.FNV_64_PRIME) & HashStrategy.MASK_64
        return h

    @staticmethod
    def murmur64(data: bytes) -> int:
        """Computes a 64-bit mixer hash based on MurmurHash3 finalization."""
        h = (0x123456789ABCDEF0 ^ len(data)) & HashStrategy.MASK_64
        for b in data:
            h ^= (b << 32) & HashStrategy.MASK_64
            h = (h * 0xd6e8feb86659fd93) & HashStrategy.MASK_64
            h ^= (h >> 32)

        # Finalization avalanche mixing
        h ^= (h >> 33)
        h = (h * 0xff51afd7ed558ccd) & HashStrategy.MASK_64
        h ^= (h >> 33)
        h = (h * 0xc4ceb9fe1a85ec53) & HashStrategy.MASK_64
        h ^= (h >> 33)
        return h
