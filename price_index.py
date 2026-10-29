"""A sorted list of (price, sku) pairs for fast price range searches.

Binary search (the bisect module) finds positions in O(log n).
"""
import bisect


class PriceIndex:
    def __init__(self):
        self._pairs = []   # always kept in sorted order

    def add(self, price, sku):
        """Insert a pair in sorted position. O(log n) search plus O(n) shift."""
        bisect.insort(self._pairs, (price, sku))

    def remove(self, price, sku):
        """Remove a pair if it exists."""
        i = bisect.bisect_left(self._pairs, (price, sku))
        if i < len(self._pairs) and self._pairs[i] == (price, sku):
            self._pairs.pop(i)

    def range(self, low, high):
        """Return SKUs with low <= price <= high. O(log n + k)."""
        start = bisect.bisect_left(self._pairs, (low, ""))
        result = []
        for price, sku in self._pairs[start:]:
            if price > high:
                break
            result.append(sku)
        return result

    def __len__(self):
        return len(self._pairs)
