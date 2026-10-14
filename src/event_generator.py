"""Deterministic synthetic event streams for demos and experiments."""

from __future__ import annotations

import random
from typing import Iterator

EVENT_TYPES = ("USER_LOGIN", "PAYMENT", "FILE_UPLOAD", "SENSOR_ALERT", "PAGE_VIEW")


def generate_stream(num_events: int, num_unique: int, seed: int = 42) -> Iterator[str]:
    """Yield ``num_events`` IDs containing exactly ``num_unique`` distinct IDs.

    Each distinct ID's first occurrence precedes its repeats; repeats pick a
    uniformly random earlier ID. The same arguments always give the same stream.
    """
    if num_events < 0 or num_unique < 0:
        raise ValueError("num_events and num_unique must be non-negative")
    if num_unique > num_events:
        raise ValueError(f"num_unique ({num_unique}) cannot exceed num_events ({num_events})")
    if num_events > 0 and num_unique == 0:
        raise ValueError("num_unique must be at least 1 when num_events > 0")
    rng = random.Random(seed)
    created: list[str] = []
    for step in range(num_events):
        remaining_new = num_unique - len(created)
        remaining_steps = num_events - step
        make_new = not created or rng.random() < remaining_new / remaining_steps
        if remaining_new == 0:
            make_new = False
        if make_new:
            kind = EVENT_TYPES[rng.randrange(len(EVENT_TYPES))]
            created.append(f"{kind}:id_{len(created):06d}")
            yield created[-1]
        else:
            yield created[rng.randrange(len(created))]
