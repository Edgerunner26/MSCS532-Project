"""Unit tests. Run with: python -m unittest"""
import random
import unittest

from hash_table import HashTable
from min_heap import MinHeap
from price_index import PriceIndex
from inventory_manager import InventoryManager


class TestHashTable(unittest.TestCase):
    def test_put_get_remove_and_resize(self):
        t = HashTable(capacity=2)
        for i in range(100):
            t.put(f"k{i}", i)
        self.assertEqual(len(t), 100)
        self.assertEqual(t.get("k42"), 42)
        t.put("k42", 0)
        self.assertEqual(t.get("k42"), 0)
        self.assertEqual(t.remove("k1"), 1)
        self.assertIsNone(t.get("k1"))
        with self.assertRaises(KeyError):
            t.remove("missing")


class TestMinHeap(unittest.TestCase):
    def test_pops_in_order(self):
        h = MinHeap()
        nums = random.sample(range(1000), 200)
        for n in nums:
            h.push(n)
        self.assertEqual([h.pop() for _ in range(200)], sorted(nums))


class TestPriceIndex(unittest.TestCase):
    def test_range(self):
        p = PriceIndex()
        for price, sku in [(5, "a"), (10, "b"), (15, "c"), (20, "d")]:
            p.add(price, sku)
        self.assertEqual(p.range(10, 15), ["b", "c"])
        p.remove(10, "b")
        self.assertEqual(p.range(0, 100), ["a", "c", "d"])


class TestInventoryManager(unittest.TestCase):
    def setUp(self):
        self.inv = InventoryManager()
        self.inv.add_product("A1", "Cable", "Tech", 9.99, 40)
        self.inv.add_product("A2", "Mouse", "Tech", 24.5, 6)
        self.inv.add_product("B1", "Stapler", "Office", 12.0, 3)

    def test_low_stock_updates(self):
        self.assertEqual(self.inv.low_stock(10), [(3, "B1"), (6, "A2")])
        self.inv.update_quantity("B1", 50)
        self.assertEqual(self.inv.low_stock(10), [(6, "A2")])
        self.inv.remove_product("A2")
        self.assertEqual(self.inv.low_stock(10), [])

    def test_price_and_category_changes(self):
        self.inv.update_price("A2", 5.0)
        self.assertEqual(self.inv.in_price_range(0, 10), ["A2", "A1"])
        self.inv.change_category("A2", "Sale")
        self.assertEqual(self.inv.in_category("Tech"), ["A1"])
        self.assertEqual(self.inv.in_category("Sale"), ["A2"])

    def test_heap_rebuild_after_many_updates(self):
        for q in range(200):
            self.inv.update_quantity("A1", q)
        self.assertLess(len(self.inv.stock_heap), 30)
        self.assertEqual(self.inv.low_stock(10), [(3, "B1"), (6, "A2")])

    def test_duplicate_sku(self):
        with self.assertRaises(ValueError):
            self.inv.add_product("A1", "Copy", "Tech", 1.0, 1)


if __name__ == "__main__":
    unittest.main()
