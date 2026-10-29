"""A hash table that uses separate chaining.

Each bucket is a small Python list of (key, value) pairs. When the table
gets too full, it doubles in size so lookups stay close to O(1).
"""


class HashTable:
    def __init__(self, capacity=8, max_load=0.75):
        self._buckets = [[] for _ in range(capacity)]
        self._size = 0
        self._max_load = max_load

    def _index(self, key):
        """Turn a key into a bucket number."""
        return hash(key) % len(self._buckets)

    def put(self, key, value):
        """Insert a new key or replace the value of an existing key. Average O(1)."""
        bucket = self._buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)   # key already here, so update it
                return
        bucket.append((key, value))
        self._size += 1
        if self._size / len(self._buckets) > self._max_load:
            self._resize()

    def get(self, key, default=None):
        """Return the value for key, or default if it is missing. Average O(1)."""
        for k, v in self._buckets[self._index(key)]:
            if k == key:
                return v
        return default

    def remove(self, key):
        """Delete key and return its value. Raise KeyError if it is missing."""
        bucket = self._buckets[self._index(key)]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket.pop(i)
                self._size -= 1
                return v
        raise KeyError(key)

    def contains(self, key):
        return self.get(key, _MISSING) is not _MISSING

    def items(self):
        """Yield every (key, value) pair."""
        for bucket in self._buckets:
            yield from bucket

    def _resize(self):
        """Double the number of buckets and rehash every pair. O(n), but rare."""
        old_items = list(self.items())
        self._buckets = [[] for _ in range(len(self._buckets) * 2)]
        self._size = 0
        for k, v in old_items:
            self.put(k, v)

    def __len__(self):
        return self._size


_MISSING = object()   # marker used by contains()
