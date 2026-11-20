"""Bounded least recently used cache built from a doubly linked list and HashTable.

Repeated read queries hit the same popular categories, price filters, and stock
thresholds. Caching recent results turns repeated queries into O(1) lookups
while a strict capacity cap stops cache memory from growing without bound.
"""

from hash_table import HashTable


class _CacheNode:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None


class LRUCache:
    """Fixed capacity LRU cache with O(1) lookup, update, and targeted removal."""

    __slots__ = ("_capacity", "_table", "_head", "_tail", "hits", "misses")

    def __init__(self, capacity=128):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self._capacity = capacity
        self._table = HashTable()
        self._head = _CacheNode()
        self._tail = _CacheNode()
        self._head.next = self._tail
        self._tail.prev = self._head
        self.hits = 0
        self.misses = 0

    def get(self, key):
        """Return the cached value and mark it most recent, or None on a miss."""
        node = self._table.get(key)
        if node is None:
            self.misses += 1
            return None
        self.hits += 1
        self._detach(node)
        self._attach_front(node)
        return node.value

    def put(self, key, value):
        """Store value for key and evict the oldest entry when capacity is full."""
        node = self._table.get(key)
        if node is not None:
            node.value = value
            self._detach(node)
            self._attach_front(node)
            return
        if len(self._table) >= self._capacity:
            oldest = self._tail.prev
            self._detach(oldest)
            self._table.remove(oldest.key)
        fresh = _CacheNode(key, value)
        self._attach_front(fresh)
        self._table.put(key, fresh)

    def invalidate(self, key):
        """Remove one key if it is cached, leaving unrelated entries warm."""
        node = self._table.get(key)
        if node is not None:
            self._detach(node)
            self._table.remove(key)

    def clear(self):
        """Drop all cached entries while keeping hit and miss totals."""
        if len(self._table) == 0:
            return
        self._table.clear()
        self._head.next = self._tail
        self._tail.prev = self._head

    def _detach(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _attach_front(self, node):
        first = self._head.next
        node.prev = self._head
        node.next = first
        self._head.next = node
        first.prev = node

    def __len__(self):
        return len(self._table)
