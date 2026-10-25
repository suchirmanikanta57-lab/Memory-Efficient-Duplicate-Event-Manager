"""A from-scratch standard Bloom Filter backed by a ``bytearray``.

Why ``bytearray``: it is a flat, mutable block of bytes whose payload size is
exactly ``ceil(m / 8)``, so the "logical memory budget" is easy to state and
verify. A Python ``int`` bit-vector would be re-allocated on every update.

Query semantics (no deletions, no external modification of the bits):
* ``False`` -> DEFINITELY never added (some required bit is 0).
* ``True``  -> POSSIBLY added (all required bits are 1); may be a false positive.
"""

from __future__ import annotations

import math
import sys

from .hash_functions import hash_positions


def _positive_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value


def optimal_bit_count(expected_items: int, false_positive_rate: float) -> int:
    """m = ceil(-n ln(p) / (ln 2)^2)."""
    n = _positive_int("expected_items", expected_items)
    if not 0.0 < false_positive_rate < 1.0:
        raise ValueError(
            f"false_positive_rate must be strictly between 0 and 1, got {false_positive_rate}"
        )
    return max(1, math.ceil(-n * math.log(false_positive_rate) / (math.log(2) ** 2)))


MAX_AUTO_HASHES = 32  # for n << m the ideal k is unbounded and only slows every operation


def optimal_hash_count(bit_count: int, expected_items: int) -> int:
    """k = round((m / n) ln 2), clamped to [1, MAX_AUTO_HASHES]."""
    m = _positive_int("bit_array_size", bit_count)
    n = _positive_int("expected_items", expected_items)
    return min(MAX_AUTO_HASHES, max(1, round(m / n * math.log(2))))


class BloomFilter:
    """Fixed-size Bloom Filter.

    Configure with ``expected_items`` + ``false_positive_rate`` (m and k are
    derived), or with an explicit ``bit_array_size``. With an explicit size,
    ``num_hashes`` or ``expected_items`` is needed to pick k.
    """

    def __init__(
        self,
        expected_items: int | None = None,
        false_positive_rate: float | None = None,
        *,
        bit_array_size: int | None = None,
        num_hashes: int | None = None,
    ) -> None:
        if expected_items is not None:
            _positive_int("expected_items", expected_items)
        if num_hashes is not None:
            _positive_int("num_hashes", num_hashes)
        if bit_array_size is not None:
            _positive_int("bit_array_size", bit_array_size)
            if false_positive_rate is not None:
                raise ValueError(
                    "bit_array_size and false_positive_rate are inconsistent: "
                    "give one sizing method, not both"
                )
            size = bit_array_size
        else:
            if expected_items is None or false_positive_rate is None:
                raise ValueError(
                    "provide expected_items and false_positive_rate, or bit_array_size"
                )
            size = optimal_bit_count(expected_items, false_positive_rate)
        if num_hashes is None:
            if expected_items is None:
                raise ValueError("num_hashes is required when expected_items is not given")
            num_hashes = optimal_hash_count(size, expected_items)
        self._size = size
        self._num_hashes = num_hashes
        self._bits = bytearray((size + 7) // 8)
        self._set_bits = 0
        self._items_added = 0

    def add(self, item: str | bytes) -> int:
        """Insert ``item``; return how many bits changed from 0 to 1."""
        newly_set = 0
        for pos in hash_positions(item, self._num_hashes, self._size):
            byte_index, mask = pos >> 3, 1 << (pos & 7)
            if not self._bits[byte_index] & mask:
                self._bits[byte_index] |= mask
                newly_set += 1
        self._set_bits += newly_set
        self._items_added += 1
        return newly_set

    def might_contain(self, item: str | bytes) -> bool:
        """False = definitely not added; True = possibly added."""
        return all(
            self._bits[pos >> 3] & (1 << (pos & 7))
            for pos in hash_positions(item, self._num_hashes, self._size)
        )

    def clear(self) -> None:
        """Reset every bit and counter."""
        self._bits = bytearray(len(self._bits))
        self._set_bits = 0
        self._items_added = 0

    @property
    def bit_array_size(self) -> int:
        """m: number of bits."""
        return self._size

    @property
    def num_hashes(self) -> int:
        """k: number of hash positions per item."""
        return self._num_hashes

    @property
    def items_added(self) -> int:
        """Number of add() calls since creation/clear (repeats counted)."""
        return self._items_added

    @property
    def bit_set_count(self) -> int:
        """X: number of bits currently 1."""
        return self._set_bits

    @property
    def occupancy_ratio(self) -> float:
        """X / m: fraction of bits set (not a false-positive probability)."""
        return self._set_bits / self._size

    @property
    def memory_usage_bytes(self) -> int:
        """Logical payload: ceil(m / 8) bytes of the bit array only.

        Excludes Python object overhead (see ``object_size_bytes``) and the
        rest of the process.
        """
        return len(self._bits)

    @property
    def object_size_bytes(self) -> int:
        """``sys.getsizeof`` of the bytearray: payload plus object header."""
        return sys.getsizeof(self._bits)

    @property
    def estimated_false_positive_rate(self) -> float:
        """Occupancy-based estimate (X / m) ** k for a random unseen item."""
        return self.occupancy_ratio ** self._num_hashes

    def expected_false_positive_rate(self, num_items: int | None = None) -> float:
        """Theoretical (1 - exp(-k n / m)) ** k for n inserted distinct items.

        Defaults to ``items_added``, which over-counts n when repeats were added.
        Assumes independent, uniform hash positions.
        """
        n = self._items_added if num_items is None else num_items
        if n < 0:
            raise ValueError("num_items must be non-negative")
        return (1.0 - math.exp(-self._num_hashes * n / self._size)) ** self._num_hashes
