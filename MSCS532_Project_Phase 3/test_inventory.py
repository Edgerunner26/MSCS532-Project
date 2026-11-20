"""Automated unit, edge case, cache, and stress tests for Phase 3 inventory."""

from dataclasses import FrozenInstanceError
import random
import unittest

from hash_table import HashTable
from inventory_manager import InventoryManager
from lru_cache import LRUCache
from min_heap import IndexedMinHeap, MinHeap
from price_index import PriceIndex


class CollisionKey:
    """Force distinct keys into bucket 1 to test collision chains."""

    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return 1

    def __eq__(self, other):
        return isinstance(other, CollisionKey) and self.value == other.value


class TestHashTable(unittest.TestCase):
    def test_insert_replace_and_none(self):
        table = HashTable()
        table.put("a", 10)
        table.put("a", None)
        self.assertEqual(len(table), 1)
        self.assertTrue(table.contains("a"))
        self.assertIsNone(table.get("a"))
        self.assertFalse(table.contains("missing"))

    def test_forced_collisions(self):
        table = HashTable()
        for number in range(20):
            table.put(CollisionKey(number), number)
        table.remove(CollisionKey(5))
        for number in range(20):
            if number != 5:
                self.assertEqual(table.get(CollisionKey(number)), number)

    def test_resize_preserves_records(self):
        table = HashTable(capacity=2)
        for number in range(100):
            table.put(str(number), number)
        self.assertEqual(len(table), 100)
        self.assertEqual(dict(table.items()), {str(n): n for n in range(100)})

    def test_shrink_reclaims_buckets_after_deletions(self):
        table = HashTable()
        for number in range(200):
            table.put(f"k{number}", number)
        peak = table.bucket_count()
        for number in range(195):
            table.remove(f"k{number}")
        self.assertLess(table.bucket_count(), peak)
        self.assertGreaterEqual(table.bucket_count(), 8)
        self.assertEqual({k: v for k, v in table.items()}, {f"k{n}": n for n in range(195, 200)})

    def test_boundary_alternation_does_not_thrash(self):
        table = HashTable(capacity=8)
        for number in range(7):
            table.put(number, number)
        buckets_after_grow = table.bucket_count()
        for _ in range(20):
            table.remove(6)
            table.put(6, 6)
        self.assertEqual(table.bucket_count(), buckets_after_grow)

    def test_reserve_and_clear(self):
        table = HashTable()
        table.reserve(100)
        self.assertGreaterEqual(table.bucket_count(), 128)
        table.put("x", 1)
        table.clear()
        self.assertEqual(len(table), 0)
        self.assertEqual(table.bucket_count(), 8)
        with self.assertRaises(ValueError):
            table.reserve(-1)

    def test_missing_delete(self):
        with self.assertRaises(KeyError):
            HashTable().remove("missing")

    def test_invalid_configuration(self):
        for capacity in (0, -1, 1.5, True):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                HashTable(capacity=capacity)
        for load in (0, 2, float("nan"), "bad", True):
            with self.subTest(load=load), self.assertRaises(ValueError):
                HashTable(max_load=load)
        for min_load in (-0.1, 0.4, float("nan"), True):
            with self.subTest(min_load=min_load), self.assertRaises(ValueError):
                HashTable(max_load=0.75, min_load=min_load)


class TestMinHeapAndIndexedHeap(unittest.TestCase):
    def test_empty_heap(self):
        heap = MinHeap()
        self.assertIsNone(heap.peek())
        with self.assertRaises(IndexError):
            heap.pop()

    def test_order_with_duplicates(self):
        heap = MinHeap()
        values = [5, 1, 1, 9, 0, 4]
        for value in values:
            heap.push(value)
        self.assertEqual([heap.pop() for _ in values], sorted(values))
        self.assertEqual(len(heap), 0)

    def test_seeded_random_order(self):
        rng = random.Random(532)
        values = [rng.randrange(100) for _ in range(200)]
        heap = MinHeap()
        for value in values:
            heap.push(value)
        self.assertEqual([heap.pop() for _ in values], sorted(values))

    def test_bottom_up_heapify(self):
        rng = random.Random(99)
        values = [rng.randrange(500) for _ in range(300)]
        heap = MinHeap(values)
        self.assertEqual([heap.pop() for _ in values], sorted(values))

    def test_indexed_heap_in_place_updates_and_delete(self):
        heap = IndexedMinHeap()
        heap.push_or_update("A", 10)
        heap.push_or_update("B", 4)
        heap.push_or_update("C", 7)
        heap.push_or_update("A", 1)
        self.assertEqual(len(heap), 3)
        self.assertEqual(heap.peek(), (1, "A"))
        heap.push_or_update("A", 25)
        self.assertEqual(heap.peek(), (4, "B"))
        heap.remove_key("B")
        self.assertEqual(len(heap), 2)
        self.assertEqual(heap.peek(), (7, "C"))
        with self.assertRaises(KeyError):
            heap.remove_key("missing")

    def test_indexed_heap_build_and_threshold_is_nondestructive(self):
        pairs = [(i % 15, f"S{i:03d}") for i in range(120)]
        heap = IndexedMinHeap()
        heap.build(pairs)
        expected = sorted(p for p in pairs if p[0] < 4)
        self.assertEqual(heap.below_threshold(4), expected)
        self.assertEqual(heap.below_threshold(4), expected)
        self.assertEqual(len(heap), 120)
        self.assertEqual(heap.below_threshold(0), [])

    def test_indexed_heap_random_sequence(self):
        rng = random.Random(532)
        heap = IndexedMinHeap()
        ref = {}
        for _ in range(500):
            key = f"K{rng.randrange(40)}"
            if not ref or rng.random() < 0.7:
                val = rng.randrange(30)
                heap.push_or_update(key, val)
                ref[key] = val
            elif key in ref:
                heap.remove_key(key)
                del ref[key]
            self.assertEqual(len(heap), len(ref))
            expected = sorted((v, k) for k, v in ref.items() if v < 10)
            self.assertEqual(heap.below_threshold(10), expected)


class TestPriceIndex(unittest.TestCase):
    def setUp(self):
        self.index = PriceIndex()
        for price, sku in [(20, "D"), (10, "B"), (5, "A"), (10, "C")]:
            self.index.add(price, sku)

    def test_inclusive_bounds_and_ties(self):
        self.assertEqual(self.index.range(10, 10), ["B", "C"])
        self.assertEqual(self.index.range(5, 20), ["A", "B", "C", "D"])

    def test_empty_results(self):
        self.assertEqual(self.index.range(21, 30), [])
        self.assertEqual(PriceIndex().range(0, 10), [])

    def test_delete_and_duplicate(self):
        self.index.remove(10, "B")
        self.assertEqual(self.index.range(10, 10), ["C"])
        with self.assertRaises(KeyError):
            self.index.remove(10, "B")
        with self.assertRaises(ValueError):
            self.index.add(10, "C")

    def test_invalid_ranges(self):
        for low, high in [(20, 10), (-1, 10), (0, float("nan")), (0, "bad"), (True, 5)]:
            with self.subTest(low=low, high=high), self.assertRaises(ValueError):
                self.index.range(low, high)

    def test_invalid_leaf_size(self):
        for bad in (0, 3, -4, 4.5, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                PriceIndex(max_keys=bad)

    def test_small_tree_splits_borrows_and_merges(self):
        rng = random.Random(532)
        tree = PriceIndex(max_keys=4)
        ref = set()
        for step in range(1500):
            if not ref or rng.random() < 0.55:
                pair = (rng.randrange(35), f"S{rng.randrange(70):02d}")
                if pair not in ref:
                    tree.add(*pair)
                    ref.add(pair)
            else:
                pair = rng.choice(tuple(ref))
                tree.remove(*pair)
                ref.remove(pair)
            if step % 50 == 0:
                lo, hi = sorted((rng.randrange(35), rng.randrange(35)))
                expected = [s for p, s in sorted(ref) if lo <= p <= hi]
                self.assertEqual(tree.range(lo, hi), expected)
        self.assertEqual(len(tree), len(ref))

    def test_drain_to_empty_and_refill(self):
        tree = PriceIndex(max_keys=4)
        items = [(i % 17, f"P{i:03d}") for i in range(80)]
        for price, sku in items:
            tree.add(price, sku)
        rng = random.Random(12)
        shuffled = list(items)
        rng.shuffle(shuffled)
        for price, sku in shuffled:
            tree.remove(price, sku)
        self.assertEqual(len(tree), 0)
        self.assertEqual(tree.range(0, 100), [])
        tree.add(9.5, "Z1")
        self.assertEqual(tree.range(0, 10), ["Z1"])

    def test_build_sorted_across_sizes(self):
        for max_keys in (4, 5, 16):
            for n in (0, 1, 3, 4, 5, 7, 19, 65):
                tree = PriceIndex(max_keys=max_keys)
                pairs = sorted((i % 11, f"S{i:03d}") for i in range(n))
                tree.build_sorted(pairs)
                self.assertEqual(len(tree), n)
                self.assertEqual(tree.range(0, 20), [s for _, s in pairs])


class TestLRUCache(unittest.TestCase):
    def test_eviction_and_hit_counters(self):
        cache = LRUCache(capacity=2)
        self.assertIsNone(cache.get("a"))
        cache.put("a", (1,))
        cache.put("b", (2,))
        self.assertEqual(cache.get("a"), (1,))
        cache.put("c", (3,))
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("c"), (3,))
        self.assertEqual(cache.hits, 2)
        self.assertEqual(cache.misses, 2)

    def test_update_existing_promotes_key(self):
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)
        cache.put("c", 3)
        self.assertEqual(cache.get("a"), 10)
        self.assertIsNone(cache.get("b"))

    def test_targeted_invalidate_and_clear(self):
        cache = LRUCache(capacity=4)
        cache.put("tech", ("A",))
        cache.put("office", ("B",))
        cache.invalidate("tech")
        self.assertIsNone(cache.get("tech"))
        self.assertEqual(cache.get("office"), ("B",))
        cache.clear()
        self.assertEqual(len(cache), 0)

    def test_empty_tuple_counts_as_cache_hit(self):
        cache = LRUCache(capacity=4)
        cache.put("empty", ())
        self.assertEqual(cache.get("empty"), ())
        self.assertEqual(cache.hits, 1)

    def test_invalid_capacity(self):
        for bad in (0, -2, 1.5, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                LRUCache(capacity=bad)


class TestInventoryManager(unittest.TestCase):
    def setUp(self):
        self.inventory = InventoryManager()
        self.inventory.add_product("A", "Cable", "Tech", 9.99, 40)
        self.inventory.add_product("B", "Mouse", "Tech", 24.50, 6)
        self.inventory.add_product("C", "Stapler", "Office", 12.00, 3)

    def test_insert_and_find(self):
        self.assertEqual(len(self.inventory), 3)
        self.assertEqual(self.inventory.find("B").name, "Mouse")
        self.assertIsNone(self.inventory.find("missing"))

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            self.inventory.add_product("A", "Copy", "Other", 1, 1)
        self.assertEqual(len(self.inventory), 3)
        self.assertEqual(self.inventory.in_category("Other"), [])

    def test_invalid_new_records_leave_indexes_unchanged(self):
        cases = [
            ("", "Name", "Category", 1, 1),
            (" X", "Name", "Category", 1, 1),
            ("X", "", "Category", 1, 1),
            ("X", "Name", " ", 1, 1),
            ("X", "Name", "Category", -1, 1),
            ("X", "Name", "Category", float("inf"), 1),
            ("X", "Name", "Category", 1, -1),
            ("X", "Name", "Category", 1, True),
        ]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.inventory.add_product(*values)
        self.assertEqual(len(self.inventory), 3)
        self.assertEqual(self.inventory.in_price_range(0, 100), ["A", "C", "B"])
        self.assertEqual(self.inventory.in_category("Category"), [])

    def test_invalid_quantity_preserves_record(self):
        original = self.inventory.find("B")
        for quantity in (-1, 1.5, "4", True):
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                self.inventory.update_quantity("B", quantity)
        self.assertEqual(self.inventory.find("B"), original)
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])

    def test_invalid_price_preserves_index(self):
        for price in (-1, float("nan"), float("inf"), "5", True):
            with self.subTest(price=price), self.assertRaises(ValueError):
                self.inventory.update_price("B", price)
        self.assertEqual(self.inventory.find("B").price, 24.50)
        self.assertEqual(self.inventory.in_price_range(20, 30), ["B"])

    def test_invalid_category_preserves_index(self):
        with self.assertRaises(ValueError):
            self.inventory.change_category("B", "")
        self.assertEqual(self.inventory.in_category("Tech"), ["A", "B"])

    def test_missing_update_and_delete(self):
        operations = [
            lambda: self.inventory.update_quantity("missing", 1),
            lambda: self.inventory.update_price("missing", 1),
            lambda: self.inventory.change_category("missing", "Sale"),
            lambda: self.inventory.remove_product("missing"),
        ]
        for operation in operations:
            with self.assertRaises(KeyError):
                operation()

    def test_price_update(self):
        self.inventory.update_price("B", 5)
        self.assertEqual(self.inventory.in_price_range(5, 10), ["B", "A"])
        self.assertEqual(self.inventory.in_price_range(20, 30), [])

    def test_category_move_and_cleanup(self):
        self.inventory.change_category("C", "Sale")
        self.assertEqual(self.inventory.in_category("Office"), [])
        self.assertFalse(self.inventory._categories.contains("Office"))
        self.assertEqual(self.inventory.in_category("Sale"), ["C"])

    def test_delete_cleans_indexes(self):
        self.inventory.remove_product("C")
        self.assertIsNone(self.inventory.find("C"))
        self.assertEqual(self.inventory.in_category("Office"), [])
        self.assertEqual(self.inventory.in_price_range(12, 12), [])
        self.assertEqual(self.inventory.low_stock(10), [(6, "B")])

    def test_low_stock_threshold_and_repeat(self):
        self.assertEqual(self.inventory.low_stock(6), [(3, "C")])
        self.assertEqual(self.inventory.low_stock(6), [(3, "C")])
        self.assertEqual(self.inventory.low_stock(0), [])

    def test_quantity_updates_keep_exact_heap_size(self):
        for quantity in [6, 2, 50, 6]:
            self.inventory.update_quantity("B", quantity)
        self.assertEqual(len(self.inventory._stock_heap), len(self.inventory))
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])

    def test_remove_and_reuse_sku(self):
        self.inventory.remove_product("B")
        self.inventory.add_product("B", "New mouse", "Sale", 5, 6)
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])
        self.assertEqual(self.inventory.in_category("Tech"), ["A"])

    def test_repeated_updates_leave_zero_stale_entries(self):
        for quantity in range(500):
            self.inventory.update_quantity("A", quantity)
        self.assertEqual(len(self.inventory._stock_heap), 3)
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])

    def test_empty_inventory(self):
        empty = InventoryManager()
        self.assertEqual(empty.low_stock(10), [])
        self.assertEqual(empty.in_category("Missing"), [])
        self.assertEqual(empty.in_price_range(0, 100), [])
        self.assertIsNone(empty.find("Missing"))

    def test_immutable_product_uses_slots(self):
        product = self.inventory.find("B")
        self.assertFalse(hasattr(product, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            product.quantity = 100

    def test_invalid_threshold(self):
        for threshold in (-1, True, 1.5):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                self.inventory.low_stock(threshold)

    def test_cache_hits_and_targeted_invalidation(self):
        self.assertEqual(self.inventory.in_category("Tech"), ["A", "B"])
        self.assertEqual(self.inventory.in_category("Office"), ["C"])
        self.assertEqual(self.inventory.in_price_range(5, 15), ["A", "C"])
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])

        # Repeat reads should all hit cache.
        self.assertEqual(self.inventory.in_category("Tech"), ["A", "B"])
        self.assertEqual(self.inventory.in_price_range(5.0, 15.0), ["A", "C"])
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])
        self.assertEqual(self.inventory.stats()["cache_hits"], 3)

        # Updating quantity must not clear price or category caches.
        self.inventory.update_quantity("C", 99)
        self.assertEqual(self.inventory.low_stock(10), [(6, "B")])
        before_hits = self.inventory.stats()["cache_hits"]
        self.assertEqual(self.inventory.in_price_range(5, 15), ["A", "C"])
        self.assertEqual(self.inventory.in_category("Tech"), ["A", "B"])
        self.assertEqual(self.inventory.stats()["cache_hits"], before_hits + 2)

        # Moving C out of Office must leave Tech cached while refreshing Office.
        self.inventory.change_category("C", "Sale")
        before_hits = self.inventory.stats()["cache_hits"]
        self.assertEqual(self.inventory.in_category("Tech"), ["A", "B"])
        self.assertEqual(self.inventory.stats()["cache_hits"], before_hits + 1)
        self.assertEqual(self.inventory.in_category("Office"), [])

    def test_caller_mutating_returned_list_does_not_corrupt_cache(self):
        tech = self.inventory.in_category("Tech")
        tech.append("TAMPERED")
        self.assertEqual(self.inventory.in_category("Tech"), ["A", "B"])

    def test_add_many_bulk_and_incremental(self):
        inv = InventoryManager()
        self.assertEqual(inv.add_many([]), 0)
        count = inv.add_many(
            [
                ("S1", "Item 1", "Tools", 15.0, 8),
                ("S2", "Item 2", "Tools", 5.0, 2),
                ("S3", "Item 3", "Hardware", 15.0, 20),
            ]
        )
        self.assertEqual(count, 3)
        self.assertEqual(inv.in_price_range(5, 15), ["S2", "S1", "S3"])
        self.assertEqual(inv.low_stock(10), [(2, "S2"), (8, "S1")])
        inv.add_many([("S4", "Item 4", "Tools", 1.0, 1)])
        self.assertEqual(inv.low_stock(5), [(1, "S4"), (2, "S2")])

    def test_add_many_atomic_rejection_on_bad_or_duplicate_row(self):
        inv = InventoryManager()
        inv.add_product("EXISTING", "Base", "Core", 10, 5)
        bad_batches = [
            [("N1", "Good", "Core", 5, 5), ("N1", "DupInBatch", "Core", 6, 6)],
            [("N1", "Good", "Core", 5, 5), ("EXISTING", "DupExisting", "Core", 6, 6)],
            [("N1", "Good", "Core", 5, 5), ("N2", "BadPrice", "Core", -3, 6)],
            [("N1", "TooFewFields", "Core", 5)],
        ]
        for batch in bad_batches:
            with self.subTest(batch=batch), self.assertRaises(ValueError):
                inv.add_many(batch)
        self.assertEqual(len(inv), 1)
        self.assertIsNone(inv.find("N1"))
        self.assertEqual(inv.in_category("Core"), ["EXISTING"])

    def test_seeded_sequence_matches_reference(self):
        rng = random.Random(532)
        inventory = InventoryManager(cache_capacity=16, price_leaf_size=6)
        reference = {}
        for _ in range(300):
            sku = f"P{rng.randrange(30)}"
            operation = rng.choice(["add", "remove", "quantity", "price", "category"])
            if sku not in reference:
                record = ["Name", "Tech", rng.randrange(30), rng.randrange(20)]
                inventory.add_product(sku, *record)
                reference[sku] = record
            elif operation == "remove":
                inventory.remove_product(sku)
                del reference[sku]
            elif operation == "quantity":
                quantity = rng.randrange(20)
                inventory.update_quantity(sku, quantity)
                reference[sku][3] = quantity
            elif operation == "price":
                price = rng.randrange(30)
                inventory.update_price(sku, price)
                reference[sku][2] = price
            elif operation == "category":
                category = rng.choice(["Tech", "Sale"])
                inventory.change_category(sku, category)
                reference[sku][1] = category
            self.assertEqual(len(inventory), len(reference))
            expected_stock = sorted((v[3], k) for k, v in reference.items() if v[3] < 10)
            self.assertEqual(inventory.low_stock(10), expected_stock)
            expected_prices = sorted((v[2], k) for k, v in reference.items() if 5 <= v[2] <= 15)
            self.assertEqual(inventory.in_price_range(5, 15), [k for _, k in expected_prices])
            for category in ["Tech", "Sale"]:
                self.assertEqual(
                    inventory.in_category(category),
                    sorted(k for k, v in reference.items() if v[1] == category),
                )

    def test_large_stress_and_shrink_matches_reference(self):
        rng = random.Random(2026)
        inventory = InventoryManager(cache_capacity=64, price_leaf_size=32)
        batch = [
            (f"SKU{i:05d}", f"Product {i}", f"Cat{i % 12}", round((i * 7 % 500) + 0.5, 2), i % 40)
            for i in range(5000)
        ]
        inventory.add_many(batch)
        reference = {sku: [name, cat, price, qty] for sku, name, cat, price, qty in batch}

        for _ in range(1500):
            sku = f"SKU{rng.randrange(5000):05d}"
            action = rng.choice(["qty", "price", "cat", "read"])
            if action == "qty" and sku in reference:
                q = rng.randrange(40)
                inventory.update_quantity(sku, q)
                reference[sku][3] = q
            elif action == "price" and sku in reference:
                p = float(rng.randrange(500))
                inventory.update_price(sku, p)
                reference[sku][2] = p
            elif action == "cat" and sku in reference:
                c = f"Cat{rng.randrange(12)}"
                inventory.change_category(sku, c)
                reference[sku][1] = c
            else:
                inventory.in_category("Cat3")
                inventory.in_price_range(50, 120)
                inventory.low_stock(5)

        expected_low = sorted((v[3], k) for k, v in reference.items() if v[3] < 5)
        self.assertEqual(inventory.low_stock(5), expected_low)
        expected_range = [k for _, k in sorted((v[2], k) for k, v in reference.items() if 50 <= v[2] <= 120)]
        self.assertEqual(inventory.in_price_range(50, 120), expected_range)
        self.assertEqual(inventory.stats()["heap_entries"], len(reference))

        peak_buckets = inventory.stats()["product_buckets"]
        for i in range(4800):
            sku = f"SKU{i:05d}"
            inventory.remove_product(sku)
            del reference[sku]
        self.assertLess(inventory.stats()["product_buckets"], peak_buckets)
        self.assertEqual(len(inventory), 200)
        expected_after = sorted((v[3], k) for k, v in reference.items() if v[3] < 5)
        self.assertEqual(inventory.low_stock(5), expected_after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
