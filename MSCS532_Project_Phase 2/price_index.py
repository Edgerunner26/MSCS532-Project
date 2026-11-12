"""A sorted list of price and SKU pairs with binary search."""
import bisect

from product import check_price, check_text


class PriceIndex:
    """Support insert, delete, and inclusive price range searches."""

    def __init__(self):
        self._pairs = []

    def add(self, price, sku):
        """Insert one pair. List movement makes this O(n)."""
        check_price(price)
        check_text(sku, "sku")
        pair = (price, sku)
        index = bisect.bisect_left(self._pairs, pair)
        if index < len(self._pairs) and self._pairs[index] == pair:
            raise ValueError("price pair already exists")
        self._pairs.insert(index, pair)

    def remove(self, price, sku):
        """Remove an exact pair or raise KeyError."""
        check_price(price)
        check_text(sku, "sku")
        pair = (price, sku)
        index = bisect.bisect_left(self._pairs, pair)
        if index == len(self._pairs) or self._pairs[index] != pair:
            raise KeyError(pair)
        self._pairs.pop(index)

    def range(self, low, high):
        """Return matching SKUs in O(log n + k) time without a tail copy."""
        check_price(low)
        check_price(high)
        if low > high:
            raise ValueError("low price must not exceed high price")
        index = bisect.bisect_left(self._pairs, (low, ""))
        result = []
        while index < len(self._pairs):
            price, sku = self._pairs[index]
            if price > high:
                break
            result.append(sku)
            index += 1
        return result

    def __len__(self):
        return len(self._pairs)
