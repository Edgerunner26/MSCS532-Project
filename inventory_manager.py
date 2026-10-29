"""InventoryManager ties the data structures together.

  products     HashTable  sku -> Product           fast lookup by SKU
  categories   HashTable  category -> set of SKUs  fast category listing
  prices       PriceIndex sorted (price, sku)      price range searches
  stock_heap   MinHeap    (quantity, sku)          lowest stock first
"""
from hash_table import HashTable
from min_heap import MinHeap
from price_index import PriceIndex
from product import Product


class InventoryManager:
    def __init__(self):
        self.products = HashTable()
        self.categories = HashTable()
        self.prices = PriceIndex()
        self.stock_heap = MinHeap()

    # ----- add and remove -----
    def add_product(self, sku, name, category, price, quantity):
        if self.products.contains(sku):
            raise ValueError(f"SKU {sku} already exists")
        product = Product(sku, name, category, price, quantity)
        self.products.put(sku, product)
        self._add_to_category(category, sku)
        self.prices.add(price, sku)
        self.stock_heap.push((quantity, sku))

    def remove_product(self, sku):
        product = self.products.remove(sku)
        self.categories.get(product.category).discard(sku)
        self.prices.remove(product.price, sku)
        # The old heap entry is skipped later because the SKU is gone.

    # ----- updates -----
    def update_quantity(self, sku, new_quantity):
        product = self._require(sku)
        product.quantity = new_quantity
        # Lazy update: push a fresh entry and ignore the old one later.
        self.stock_heap.push((new_quantity, sku))
        # If old entries pile up, rebuild the heap from current data.
        if len(self.stock_heap) > 2 * len(self.products) + 16:
            self._rebuild_heap()

    def update_price(self, sku, new_price):
        product = self._require(sku)
        self.prices.remove(product.price, sku)
        product.price = new_price
        self.prices.add(new_price, sku)

    def change_category(self, sku, new_category):
        product = self._require(sku)
        self.categories.get(product.category).discard(sku)
        product.category = new_category
        self._add_to_category(new_category, sku)

    # ----- queries -----
    def find(self, sku):
        return self.products.get(sku)

    def in_category(self, category):
        return sorted(self.categories.get(category, set()))

    def in_price_range(self, low, high):
        return self.prices.range(low, high)

    def low_stock(self, threshold):
        """Return (quantity, sku) for every product below threshold, lowest first."""
        found, keep = [], []
        while len(self.stock_heap) and self.stock_heap.peek()[0] < threshold:
            quantity, sku = self.stock_heap.pop()
            product = self.products.get(sku)
            # Skip stale entries left by updates or removals.
            if product is not None and product.quantity == quantity:
                if (quantity, sku) not in keep:
                    found.append((quantity, sku))
                    keep.append((quantity, sku))
        for entry in keep:            # put the valid entries back
            self.stock_heap.push(entry)
        return found

    # ----- helpers -----
    def _rebuild_heap(self):
        self.stock_heap = MinHeap()
        for sku, product in self.products.items():
            self.stock_heap.push((product.quantity, sku))

    def _require(self, sku):
        product = self.products.get(sku)
        if product is None:
            raise KeyError(f"SKU {sku} not found")
        return product

    def _add_to_category(self, category, sku):
        skus = self.categories.get(category)
        if skus is None:
            skus = set()
            self.categories.put(category, skus)
        skus.add(sku)

    def __len__(self):
        return len(self.products)
