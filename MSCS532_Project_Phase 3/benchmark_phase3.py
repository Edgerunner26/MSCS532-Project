"""Benchmark comparing the Phase 2 baseline against the Phase 3 optimized design.

Measures catalog loading, price and stock updates, read heavy query mixes, and
memory usage from 2,000 up to 50,000 products, then writes CSV files to results.
"""

import bisect
import csv
from dataclasses import dataclass, replace
import os
import random
import statistics
import time
import tracemalloc

from inventory_manager import InventoryManager
from product import check_price, check_quantity, check_text

SIZES = [2000, 5000, 10000, 25000, 50000]
TRIALS = 3
SEED = 532


@dataclass(frozen=True)
class _P2Product:
    """Phase 2 unslotted product record with revision counter and checks."""

    sku: str
    name: str
    category: str
    price: float
    quantity: int
    revision: int = 0

    def __post_init__(self):
        check_text(self.sku, "sku")
        check_text(self.name, "name")
        check_text(self.category, "category")
        check_price(self.price)
        check_quantity(self.quantity)


class _P2HashTable:
    """Phase 2 separate chaining hash table without shrinking or reserve."""

    def __init__(self, capacity=8, max_load=0.75):
        self._buckets = [[] for _ in range(capacity)]
        self._size = 0
        self._max_load = max_load

    def _index(self, key):
        return hash(key) % len(self._buckets)

    def put(self, key, value):
        bucket = self._buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self._size += 1
        if self._size / len(self._buckets) > self._max_load:
            old = list(self.items())
            self._buckets = [[] for _ in range(len(self._buckets) * 2)]
            self._size = 0
            for k, v in old:
                self.put(k, v)

    def get(self, key, default=None):
        for k, v in self._buckets[self._index(key)]:
            if k == key:
                return v
        return default

    def remove(self, key):
        bucket = self._buckets[self._index(key)]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket.pop(i)
                self._size -= 1
                return v
        raise KeyError(key)

    def contains(self, key):
        marker = object()
        return self.get(key, marker) is not marker

    def items(self):
        for bucket in self._buckets:
            yield from bucket

    def __len__(self):
        return self._size


class _P2MinHeap:
    """Phase 2 plain binary min heap."""

    def __init__(self):
        self._data = []

    def push(self, item):
        self._data.append(item)
        i = len(self._data) - 1
        while i > 0:
            parent = (i - 1) // 2
            if self._data[i] < self._data[parent]:
                self._data[i], self._data[parent] = self._data[parent], self._data[i]
                i = parent
            else:
                break

    def pop(self):
        smallest = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            i = 0
            n = len(self._data)
            while True:
                left, right = 2 * i + 1, 2 * i + 2
                best = i
                if left < n and self._data[left] < self._data[best]:
                    best = left
                if right < n and self._data[right] < self._data[best]:
                    best = right
                if best == i:
                    break
                self._data[i], self._data[best] = self._data[best], self._data[i]
                i = best
        return smallest

    def peek(self):
        return self._data[0] if self._data else None

    def __len__(self):
        return len(self._data)


class _P2Inventory:
    """Faithful copy of the Phase 2 proof of concept for timing comparisons."""

    def __init__(self):
        self._products = _P2HashTable()
        self._categories = _P2HashTable()
        self._prices = []
        self._stock_heap = _P2MinHeap()
        self._revision = 0

    def add_product(self, sku, name, category, price, quantity):
        product = _P2Product(sku, name, category, price, quantity)
        if self._products.contains(sku):
            raise ValueError(f"SKU {sku} already exists")
        self._revision += 1
        product = replace(product, revision=self._revision)
        self._products.put(sku, product)
        skus = self._categories.get(category)
        if skus is None:
            skus = set()
            self._categories.put(category, skus)
        skus.add(sku)
        bisect.insort_left(self._prices, (price, sku))
        self._stock_heap.push((quantity, sku, product.revision))

    def remove_product(self, sku):
        product = self._products.remove(sku)
        idx = bisect.bisect_left(self._prices, (product.price, sku))
        self._prices.pop(idx)
        skus = self._categories.get(product.category)
        skus.remove(sku)
        if not skus:
            self._categories.remove(product.category)
        self._compact_heap()

    def update_quantity(self, sku, new_quantity):
        product = self._products.get(sku)
        self._revision += 1
        updated = replace(product, quantity=new_quantity, revision=self._revision)
        self._products.put(sku, updated)
        self._stock_heap.push((new_quantity, sku, updated.revision))
        self._compact_heap()

    def update_price(self, sku, new_price):
        product = self._products.get(sku)
        updated = replace(product, price=new_price)
        idx = bisect.bisect_left(self._prices, (product.price, sku))
        self._prices.pop(idx)
        bisect.insort_left(self._prices, (new_price, sku))
        self._products.put(sku, updated)

    def in_category(self, category):
        return sorted(self._categories.get(category, set()))

    def in_price_range(self, low, high):
        index = bisect.bisect_left(self._prices, (low, ""))
        result = []
        while index < len(self._prices):
            price, sku = self._prices[index]
            if price > high:
                break
            result.append(sku)
            index += 1
        return result

    def low_stock(self, threshold):
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
        if len(self._stock_heap) > 2 * len(self._products) + 16:
            self._stock_heap = _P2MinHeap()
            for sku, product in self._products.items():
                self._stock_heap.push((product.quantity, sku, product.revision))


def build_dataset(n, rng):
    """Create n deterministic product tuples with realistic price and stock spread."""
    categories = [f"Category{i}" for i in range(16)]
    return [
        (
            f"SKU{i:06d}",
            f"Product {i}",
            categories[i % 16],
            round(rng.uniform(1.0, 500.0), 2),
            rng.randrange(100),
        )
        for i in range(n)
    ]


def median_ms(fn):
    samples = []
    for _ in range(TRIALS):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return round(statistics.median(samples), 2)


def run_scaling_benchmarks():
    rows = []
    for n in SIZES:
        rng = random.Random(SEED + n)
        dataset = build_dataset(n, rng)
        price_ops = [(f"SKU{rng.randrange(n):06d}", round(rng.uniform(1.0, 500.0), 2)) for _ in range(2000)]
        stock_ops = [(f"SKU{rng.randrange(n):06d}", rng.randrange(100)) for _ in range(2000)]
        hot_cats = ["Category0", "Category1", "Category2", "Category3"]
        hot_ranges = [(10.0, 50.0), (50.0, 120.0), (120.0, 250.0), (250.0, 400.0)]

        def p2_load():
            inv = _P2Inventory()
            for row in dataset:
                inv.add_product(*row)

        def p3_incremental_load():
            inv = InventoryManager()
            for row in dataset:
                inv.add_product(*row)

        def p3_bulk_load():
            inv = InventoryManager()
            inv.add_many(dataset)

        t_p2_load = median_ms(p2_load)
        t_p3_inc = median_ms(p3_incremental_load)
        t_p3_bulk = median_ms(p3_bulk_load)

        # Build warm instances for update and query timing.
        def run_updates_p2():
            inv = _P2Inventory()
            for row in dataset:
                inv.add_product(*row)
            start = time.perf_counter()
            for sku, p in price_ops:
                inv.update_price(sku, p)
            for idx, (sku, q) in enumerate(stock_ops):
                inv.update_quantity(sku, q)
                if idx % 50 == 0:
                    inv.low_stock(10)
            return (time.perf_counter() - start) * 1000.0

        def run_updates_p3():
            inv = InventoryManager()
            inv.add_many(dataset)
            start = time.perf_counter()
            for sku, p in price_ops:
                inv.update_price(sku, p)
            for idx, (sku, q) in enumerate(stock_ops):
                inv.update_quantity(sku, q)
                if idx % 50 == 0:
                    inv.low_stock(10)
            return (time.perf_counter() - start) * 1000.0

        t_p2_upd = round(statistics.median([run_updates_p2() for _ in range(TRIALS)]), 2)
        t_p3_upd = round(statistics.median([run_updates_p3() for _ in range(TRIALS)]), 2)

        p2_warm = _P2Inventory()
        for row in dataset:
            p2_warm.add_product(*row)
        p3_warm = InventoryManager()
        p3_warm.add_many(dataset)

        # Check identical answers before timing queries.
        assert p2_warm.in_category("Category0") == p3_warm.in_category("Category0")
        assert p2_warm.in_price_range(10.0, 50.0) == p3_warm.in_price_range(10.0, 50.0)
        assert p2_warm.low_stock(10) == p3_warm.low_stock(10)

        def p2_queries():
            for i in range(400):
                p2_warm.in_category(hot_cats[i % 4])
                lo, hi = hot_ranges[i % 4]
                p2_warm.in_price_range(lo, hi)
                p2_warm.low_stock(10)

        def p3_queries():
            p3_warm._category_cache.clear()
            p3_warm._price_cache.clear()
            p3_warm._stock_cache.clear()
            for i in range(400):
                p3_warm.in_category(hot_cats[i % 4])
                lo, hi = hot_ranges[i % 4]
                p3_warm.in_price_range(lo, hi)
                p3_warm.low_stock(10)

        t_p2_qry = median_ms(p2_queries)
        t_p3_qry = median_ms(p3_queries)

        row = {
            "n": n,
            "p2_load_ms": t_p2_load,
            "p3_inc_load_ms": t_p3_inc,
            "p3_bulk_load_ms": t_p3_bulk,
            "p2_updates_ms": t_p2_upd,
            "p3_updates_ms": t_p3_upd,
            "p2_queries_ms": t_p2_qry,
            "p3_queries_ms": t_p3_qry,
        }
        rows.append(row)
        print(row)

    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "scaling_results.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_memory_benchmark():
    n = 50000
    rng = random.Random(SEED + 999)
    dataset = build_dataset(n, rng)
    mem_rows = []

    # Measure Phase 2 memory after load, updates, and 90 percent deletion.
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    p2 = _P2Inventory()
    for row in dataset:
        p2.add_product(*row)
    for i in range(40000):
        p2.update_quantity(f"SKU{i:06d}", (i + 3) % 100)
    p2_active_kib = round((tracemalloc.get_traced_memory()[0] - base) / 1024.0, 1)
    p2_heap_at_50k = len(p2._stock_heap)
    p2_buckets_after_load = len(p2._products._buckets)
    for i in range(45000):
        p2.remove_product(f"SKU{i:06d}")
    p2_after_delete_kib = round((tracemalloc.get_traced_memory()[0] - base) / 1024.0, 1)
    p2_buckets_after_delete = len(p2._products._buckets)
    tracemalloc.stop()
    mem_rows.append(
        {
            "version": "Phase 2 Proof of Concept",
            "active_50k_kib": p2_active_kib,
            "after_90pct_delete_kib": p2_after_delete_kib,
            "heap_entries_at_50k": p2_heap_at_50k,
            "buckets_at_50k": p2_buckets_after_load,
            "buckets_after_delete": p2_buckets_after_delete,
        }
    )
    del p2

    # Measure Phase 3 memory under the exact same sequence.
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    p3 = InventoryManager()
    p3.add_many(dataset)
    for i in range(40000):
        p3.update_quantity(f"SKU{i:06d}", (i + 3) % 100)
    p3_active_kib = round((tracemalloc.get_traced_memory()[0] - base) / 1024.0, 1)
    heap_at_50k = len(p3._stock_heap)
    p3_buckets_at_50k = p3.stats()["product_buckets"]
    for i in range(45000):
        p3.remove_product(f"SKU{i:06d}")
    p3_after_delete_kib = round((tracemalloc.get_traced_memory()[0] - base) / 1024.0, 1)
    p3_buckets_after_delete = p3.stats()["product_buckets"]
    tracemalloc.stop()
    mem_rows.append(
        {
            "version": "Phase 3 Optimized",
            "active_50k_kib": p3_active_kib,
            "after_90pct_delete_kib": p3_after_delete_kib,
            "heap_entries_at_50k": heap_at_50k,
            "buckets_at_50k": p3_buckets_at_50k,
            "buckets_after_delete": p3_buckets_after_delete,
        }
    )
    for r in mem_rows:
        print(r)

    with open(os.path.join("results", "memory_results.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(mem_rows[0].keys()))
        writer.writeheader()
        writer.writerows(mem_rows)


if __name__ == "__main__":
    run_scaling_benchmarks()
    run_memory_benchmark()
    print("Saved benchmark files to results/")
