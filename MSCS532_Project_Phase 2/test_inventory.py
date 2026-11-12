"""Deterministic tests for the structures and their combined behavior."""
from dataclasses import FrozenInstanceError
import random
import unittest

from hash_table import HashTable
from inventory_manager import InventoryManager
from min_heap import MinHeap
from price_index import PriceIndex


class CollisionKey:
    """Force different keys into the same bucket for a collision test."""
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


class TestMinHeap(unittest.TestCase):
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
        for low, high in [(20, 10), (-1, 10), (0, float("nan")), (0, "bad")]:
            with self.subTest(low=low, high=high), self.assertRaises(ValueError):
                self.index.range(low, high)


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

    def test_quantity_revisions(self):
        for quantity in [6, 2, 6, 6]:
            self.inventory.update_quantity("B", quantity)
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])

    def test_remove_and_reuse_sku(self):
        self.inventory.remove_product("B")
        self.inventory.add_product("B", "New mouse", "Sale", 5, 6)
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])
        self.assertEqual(self.inventory.in_category("Tech"), ["A"])

    def test_heap_compaction(self):
        for quantity in range(200):
            self.inventory.update_quantity("A", quantity)
        self.assertLessEqual(len(self.inventory._stock_heap), 2 * len(self.inventory) + 16)
        self.assertEqual(self.inventory.low_stock(10), [(3, "C"), (6, "B")])

    def test_empty_inventory(self):
        empty = InventoryManager()
        self.assertEqual(empty.low_stock(10), [])
        self.assertEqual(empty.in_category("Missing"), [])
        self.assertEqual(empty.in_price_range(0, 100), [])
        self.assertIsNone(empty.find("Missing"))

    def test_immutable_product(self):
        with self.assertRaises(FrozenInstanceError):
            self.inventory.find("B").quantity = 100

    def test_invalid_threshold(self):
        for threshold in (-1, True, 1.5):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                self.inventory.low_stock(threshold)

    def test_seeded_sequence_matches_reference(self):
        """Check 200 mixed operations against a simple reference dictionary."""
        rng = random.Random(532)
        inventory = InventoryManager()
        reference = {}
        for _ in range(200):
            sku = f"P{rng.randrange(20)}"
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
            for key, value in reference.items():
                product = inventory.find(key)
                self.assertEqual(
                    [product.name, product.category, product.price, product.quantity],
                    value,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
