"""Coordinate products, categories, prices, and stock priorities."""
from dataclasses import replace

from hash_table import HashTable
from min_heap import MinHeap
from price_index import PriceIndex
from product import Product, check_quantity, check_text


class InventoryManager:
    """A single user inventory prototype that stores data in memory."""

    def __init__(self):
        self._products = HashTable()
        self._categories = HashTable()
        self._prices = PriceIndex()
        self._stock_heap = MinHeap()
        self._revision = 0

    def add_product(self, sku, name, category, price, quantity):
        """Validate the whole record before changing any index."""
        product = Product(sku, name, category, price, quantity)
        if self._products.contains(sku):
            raise ValueError(f"SKU {sku} already exists")
        self._revision += 1
        product = replace(product, revision=self._revision)
        self._products.put(sku, product)
        self._add_category(category, sku)
        self._prices.add(price, sku)
        self._stock_heap.push((quantity, sku, product.revision))

    def remove_product(self, sku):
        """Remove all searchable records and leave old heap entries stale."""
        product = self._require(sku)
        self._prices.remove(product.price, sku)
        self._remove_category(product.category, sku)
        self._products.remove(sku)
        self._compact_heap()

    def update_quantity(self, sku, new_quantity):
        """Create a new revision so older heap entries can be rejected."""
        product = self._require(sku)
        updated = replace(product, quantity=new_quantity)
        self._revision += 1
        updated = replace(updated, revision=self._revision)
        self._products.put(sku, updated)
        self._stock_heap.push((new_quantity, sku, updated.revision))
        self._compact_heap()

    def update_price(self, sku, new_price):
        """Validate first, then replace the old price pair."""
        product = self._require(sku)
        updated = replace(product, price=new_price)
        self._prices.remove(product.price, sku)
        self._prices.add(new_price, sku)
        self._products.put(sku, updated)

    def change_category(self, sku, new_category):
        """Move the SKU and remove a category when it becomes empty."""
        product = self._require(sku)
        updated = replace(product, category=new_category)
        self._remove_category(product.category, sku)
        self._add_category(new_category, sku)
        self._products.put(sku, updated)

    def find(self, sku):
        """Return an immutable Product or None for a missing SKU."""
        check_text(sku, "sku")
        return self._products.get(sku)

    def in_category(self, category):
        """Return sorted SKUs. Sorting k results costs O(k log k)."""
        check_text(category, "category")
        return sorted(self._categories.get(category, set()))

    def in_price_range(self, low, high):
        """Return all SKUs within the inclusive bounds."""
        return self._prices.range(low, high)

    def low_stock(self, threshold):
        """Report stock strictly below the threshold without removing products."""
        check_quantity(threshold)
        results = []
        keep = []
        while len(self._stock_heap) and self._stock_heap.peek()[0] < threshold:
            quantity, sku, revision = self._stock_heap.pop()
            product = self._products.get(sku)
            if product is not None and product.revision == revision:
                results.append((quantity, sku))
                keep.append((quantity, sku, revision))
        for entry in keep:
            self._stock_heap.push(entry)
        return results

    def _compact_heap(self):
        """Bound stale entries after updates and deletions."""
        if len(self._stock_heap) > 2 * len(self) + 16:
            self._stock_heap = MinHeap()
            for sku, product in self._products.items():
                self._stock_heap.push((product.quantity, sku, product.revision))

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
