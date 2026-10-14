# Bloom Filters Explained

## The problem
We want to ask "have I seen this event before?" using very little memory.

## Bit array
A Bloom Filter is a row of `m` bits, all 0 at the start. Our implementation stores them in a
`bytearray` of `ceil(m / 8)` bytes; bit `p` lives in byte `p // 8` at position `p % 8`.

## Hash functions
A hash function maps any input to a number. We need `k` positions in `0 .. m-1` per item. We hash once
with SHA-256 and derive them by double hashing: `position_i = (h1 + i * h2) mod m`. The same input
always yields the same positions (unlike Python's randomised built-in `hash()`).

## Insertion
Compute the `k` positions and set those bits to 1. Setting a bit that is already 1 changes nothing,
so inserting the same item twice is harmless.

## Membership testing
Compute the `k` positions. If any bit is 0 the item was **definitely never inserted**. If all are 1,
the item was **possibly inserted**.

## False positives
Other items may have set exactly those bits. Then a never-inserted item looks present. The more bits are
set (higher occupancy), the likelier this is. The filter cannot distinguish a real repeat from this case.

## Why no false negatives (normal operation)
Inserting an item sets all of its bits to 1, and a standard filter never clears a bit except through
`clear()`, which wipes everything. So an inserted item's bits stay 1 and its query returns `True`. This
guarantee breaks only if bits are removed or the array is corrupted.

## Why memory limits matter
`m` is fixed at creation. A smaller `m` saves memory but fills faster, raising the false-positive rate for
the same number of events. Our budgets (1, 2, 4, 8 KiB) make that trade-off measurable.

## Small worked example (m = 16, k = 3)
Positions below come from this project's hash function (`hash_positions(item, 3, 16)`):

| Step | Item | Positions | Result |
|---|---|---|---|
| 1 | `PAYMENT:txn_205` | 8, 11, 14 | bits all 0 -> new; set bits 8, 11, 14 |
| 2 | `USER_LOGIN:user_104` | 4, 10, 0 | bit 4 is 0 -> new; set bits 0, 4, 10 |
| 3 | `PAYMENT:txn_205` again | 8, 11, 14 | all 1 -> possible duplicate |
| 4 | `PAGE_VIEW:page_501` | 7, 11, 15 | bit 7 is 0 -> new (bit 11 happened to be shared) |

After step 2 bits {0, 4, 8, 10, 11, 14} are set. Step 4 shows overlap: one of the three required bits was
already set by another item. With many items, all three could be set by others, giving a false positive.
