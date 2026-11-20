"""Separate chaining hash table with lazy buckets, shrinking, and bulk reserve.

Phase 2 allocated a Python list object for every empty bucket on each resize.
Here empty slots hold None until a key lands there, which cuts memory overhead
and speeds up rehashing. The table doubles above max_load and halves below
min_load, keeping min_load below half of max_load to avoid boundary thrashing.
"""

from math import isfinite

_MISSING = object()


class HashTable:
    __slots__ = ("_buckets", "_size", "_max_load", "_min_load", "_min_capacity")

    def __init__(self, capacity=8, max_load=0.75, min_load=0.20):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if type(max_load) not in (int, float) or not isfinite(max_load) or not 0 < max_load <= 1:
            raise ValueError("max_load must be greater than zero and at most one")
        if type(min_load) not in (int, float) or not isfinite(min_load) or not 0 <= min_load < max_load / 2:
            raise ValueError("min_load must be nonnegative and less than half of max_load")
        self._min_capacity = min(capacity, 8)
        self._buckets = [None] * capacity
        self._size = 0
        self._max_load = max_load
        self._min_load = min_load

    def bucket_count(self):
        """Return the current number of allocated bucket slots."""
        return len(self._buckets)

    def reserve(self, expected_size):
        """Preallocate enough bucket slots for a known batch size in one step."""
        if type(expected_size) is not int or expected_size < 0:
            raise ValueError("expected_size must be a nonnegative integer")
        needed = int(expected_size / self._max_load) + 1
        target = len(self._buckets)
        while target < needed:
            target *= 2
        if target > len(self._buckets):
            self._rehash(target)

    def put(self, key, value):
        """Insert a key or replace its value in average O(1) time."""
        buckets = self._buckets
        idx = hash(key) % len(buckets)
        bucket = buckets[idx]
        if bucket is None:
            buckets[idx] = [(key, value)]
        else:
            for i, (k, _) in enumerate(bucket):
                if k == key:
                    bucket[i] = (key, value)
                    return
            bucket.append((key, value))
        self._size += 1
        if self._size > len(buckets) * self._max_load:
            self._rehash(len(buckets) * 2)

    def get(self, key, default=None):
        """Return the value for key, or default when key is absent."""
        buckets = self._buckets
        bucket = buckets[hash(key) % len(buckets)]
        if bucket is not None:
            for k, v in bucket:
                if k == key:
                    return v
        return default

    def remove(self, key):
        """Delete key and return its old value, or raise KeyError if missing."""
        buckets = self._buckets
        idx = hash(key) % len(buckets)
        bucket = buckets[idx]
        if bucket is not None:
            for i, (k, v) in enumerate(bucket):
                if k == key:
                    if len(bucket) == 1:
                        buckets[idx] = None
                    else:
                        bucket.pop(i)
                    self._size -= 1
                    half = len(buckets) // 2
                    if (
                        len(buckets) > self._min_capacity
                        and half >= self._min_capacity
                        and self._size < len(buckets) * self._min_load
                    ):
                        self._rehash(half)
                    return v
        raise KeyError(key)

    def contains(self, key):
        """Return True when key is stored in the table."""
        return self.get(key, _MISSING) is not _MISSING

    def clear(self):
        """Remove every item and reset bucket slots back to minimum capacity."""
        if self._size == 0 and len(self._buckets) == self._min_capacity:
            return
        self._buckets = [None] * self._min_capacity
        self._size = 0

    def items(self):
        """Yield all stored key and value pairs."""
        for bucket in self._buckets:
            if bucket is not None:
                yield from bucket

    def _rehash(self, new_capacity):
        """Move existing unique pairs into a fresh flat slot array."""
        new_buckets = [None] * new_capacity
        for bucket in self._buckets:
            if bucket is not None:
                for pair in bucket:
                    idx = hash(pair[0]) % new_capacity
                    slot = new_buckets[idx]
                    if slot is None:
                        new_buckets[idx] = [pair]
                    else:
                        slot.append(pair)
        self._buckets = new_buckets

    def __len__(self):
        return self._size
