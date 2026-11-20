"""Inventory manager combining fast indexes, bulk loading, and bounded caching."""

from dataclasses import replace

from hash_table import HashTable
from lru_cache import LRUCache
from min_heap import IndexedMinHeap
from price_index import PriceIndex
from product import Product, check_price, check_quantity, check_text


class InventoryManager:
    """Coordinate product lookup, category sets, ordered prices, and stock alerts.

    Phase 3 replaces the flat sorted price list with a B plus tree, replaces lazy
    duplicate heap entries with an in place indexed min heap, shrinks hash tables
    after heavy deletions, adds atomic batch loading, and caches repeated queries
    in fixed size LRU caches with targeted invalidation.
    """

    __slots__ = (
        "_products",
        "_categories",
        "_prices",
        "_stock_heap",
        "_category_cache",
        "_price_cache",
        "_stock_cache",
    )

    def __init__(self, cache_capacity=128, price_leaf_size=128):
        self._products = HashTable()
        self._categories = HashTable()
        self._prices = PriceIndex(max_keys=price_leaf_size)
        self._stock_heap = IndexedMinHeap()
        self._category_cache = LRUCache(capacity=cache_capacity)
        self._price_cache = LRUCache(capacity=cache_capacity)
        self._stock_cache = LRUCache(capacity=cache_capacity)

    def add_product(self, sku, name, category, price, quantity):
        """Validate a single product and insert it across every index."""
        product = Product(sku, name, category, price, quantity)
        if self._products.contains(sku):
            raise ValueError(f"SKU {sku} already exists")
        self._products.put(sku, product)
        self._add_category(category, sku)
        self._prices.add(price, sku)
        self._stock_heap.push_or_update(sku, quantity)
        self._category_cache.invalidate(category)
        self._price_cache.clear()
        self._stock_cache.clear()

    def add_many(self, records):
        """Validate and load a batch of (sku, name, category, price, quantity) tuples.

        Every record is checked before any structure changes, so a bad row in the
        middle of a large file leaves the inventory completely untouched. When the
        inventory starts empty, the price tree and stock heap build in bulk.
        """
        validated = []
        seen = set()
        for row in records:
            if len(row) != 5:
                raise ValueError("each record must have five fields")
            product = Product(*row)
            if product.sku in seen or self._products.contains(product.sku):
                raise ValueError(f"SKU {product.sku} already exists")
            seen.add(product.sku)
            validated.append(product)

        if not validated:
            return 0

        was_empty = len(self._products) == 0
        self._products.reserve(len(self._products) + len(validated))

        touched_categories = set()
        for product in validated:
            self._products.put(product.sku, product)
            self._add_category(product.category, product.sku)
            touched_categories.add(product.category)

        if was_empty:
            sorted_prices = sorted((p.price, p.sku) for p in validated)
            self._prices.build_sorted(sorted_prices)
            self._stock_heap.build([(p.quantity, p.sku) for p in validated])
        else:
            for product in validated:
                self._prices.add(product.price, product.sku)
                self._stock_heap.push_or_update(product.sku, product.quantity)

        for category in touched_categories:
            self._category_cache.invalidate(category)
        self._price_cache.clear()
        self._stock_cache.clear()
        return len(validated)

    def remove_product(self, sku):
        """Remove a product from every index and invalidate matching caches."""
        product = self._require(sku)
        self._prices.remove(product.price, sku)
        self._remove_category(product.category, sku)
        self._stock_heap.remove_key(sku)
        self._products.remove(sku)
        self._category_cache.invalidate(product.category)
        self._price_cache.clear()
        self._stock_cache.clear()

    def update_quantity(self, sku, new_quantity):
        """Update stock in place inside the indexed heap without touching prices."""
        product = self._require(sku)
        updated = replace(product, quantity=new_quantity)
        self._products.put(sku, updated)
        self._stock_heap.push_or_update(sku, new_quantity)
        self._stock_cache.clear()

    def update_price(self, sku, new_price):
        """Validate the new price first, then update the price tree."""
        product = self._require(sku)
        updated = replace(product, price=new_price)
        if product.price != new_price:
            self._prices.remove(product.price, sku)
            self._prices.add(new_price, sku)
            self._price_cache.clear()
        self._products.put(sku, updated)

    def change_category(self, sku, new_category):
        """Move a SKU between categories and invalidate only those two categories."""
        product = self._require(sku)
        updated = replace(product, category=new_category)
        if product.category != new_category:
            self._remove_category(product.category, sku)
            self._add_category(new_category, sku)
            self._category_cache.invalidate(product.category)
            self._category_cache.invalidate(new_category)
        self._products.put(sku, updated)

    def find(self, sku):
        """Return the Product for sku in average O(1) time, or None when absent."""
        check_text(sku, "sku")
        return self._products.get(sku)

    def in_category(self, category):
        """Return sorted SKUs in category, serving repeated reads from cache."""
        check_text(category, "category")
        cached = self._category_cache.get(category)
        if cached is not None:
            return list(cached)
        result = tuple(sorted(self._categories.get(category, ())))
        self._category_cache.put(category, result)
        return list(result)

    def in_price_range(self, low, high):
        """Return SKUs within the inclusive price bounds, using cache on repeats."""
        check_price(low)
        check_price(high)
        if low > high:
            raise ValueError("low price must not exceed high price")
        key = (float(low), float(high))
        cached = self._price_cache.get(key)
        if cached is not None:
            return list(cached)
        result = tuple(self._prices.range(low, high))
        self._price_cache.put(key, result)
        return list(result)

    def low_stock(self, threshold):
        """Return (quantity, sku) pairs strictly below threshold without heap churn."""
        check_quantity(threshold)
        cached = self._stock_cache.get(threshold)
        if cached is not None:
            return list(cached)
        result = tuple(self._stock_heap.below_threshold(threshold))
        self._stock_cache.put(threshold, result)
        return list(result)

    def stats(self):
        """Return structural sizes and cache counters for diagnostics and testing."""
        return {
            "products": len(self._products),
            "product_buckets": self._products.bucket_count(),
            "heap_entries": len(self._stock_heap),
            "price_entries": len(self._prices),
            "cache_hits": (
                self._category_cache.hits
                + self._price_cache.hits
                + self._stock_cache.hits
            ),
            "cache_misses": (
                self._category_cache.misses
                + self._price_cache.misses
                + self._stock_cache.misses
            ),
        }

    def _require(self, sku):
        product = self.find(sku)
        if product is None:
            raise KeyError(f"SKU {sku} not found")
        return product

    def _add_category(self, category, sku):
        skus = self._categories.get(category)
        if skus is None:
            skus = set()
            self._categories.put(category, skus)
        skus.add(sku)

    def _remove_category(self, category, sku):
        skus = self._categories.get(category)
        skus.remove(sku)
        if not skus:
            self._categories.remove(category)

    def __len__(self):
        return len(self._products)
