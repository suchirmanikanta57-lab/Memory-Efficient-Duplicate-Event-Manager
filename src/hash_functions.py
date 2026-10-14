"""Deterministic double hashing for the Bloom Filter.

One SHA-256 digest is computed per item. Its two 128-bit halves become h1 and
h2, and the i-th bit position is ``(h1 + i * h2) mod m`` (Kirsch-Mitzenmacher
double hashing). Python's built-in ``hash()`` is never used because it is
randomised per process and would make results irreproducible.
"""

from __future__ import annotations

import hashlib


def to_bytes(item: str | bytes) -> bytes:
    """Convert an item to a stable byte string (strings use UTF-8)."""
    if isinstance(item, bytes):
        return item
    if isinstance(item, str):
        return item.encode("utf-8")
    raise TypeError(f"item must be str or bytes, got {type(item).__name__}")


def base_hashes(item: str | bytes, size: int) -> tuple[int, int]:
    """Return (h1, h2) for ``item`` reduced modulo ``size``.

    h2 is forced to be nonzero modulo ``size`` (0 becomes 1). Otherwise every
    probe would land on the same bit, silently reducing k to 1. For size == 1
    every position is 0 anyway.
    """
    if size < 1:
        raise ValueError("size must be a positive integer")
    digest = hashlib.sha256(to_bytes(item)).digest()
    h1 = int.from_bytes(digest[:16], "big") % size
    h2 = int.from_bytes(digest[16:], "big") % size
    if h2 == 0:
        h2 = 1 % size
    return h1, h2


def hash_positions(item: str | bytes, num_hashes: int, size: int) -> list[int]:
    """Return ``num_hashes`` bit positions in ``range(size)`` for ``item``.

    Positions may repeat for small ``size``; distinct inputs may collide.
    """
    if num_hashes < 1:
        raise ValueError("num_hashes must be a positive integer")
    h1, h2 = base_hashes(item, size)
    return [(h1 + i * h2) % size for i in range(num_hashes)]
