"""Demonstration of Phase 3 inventory operations, batch loading, and caching."""

from inventory_manager import InventoryManager


def main():
    inventory = InventoryManager()

    # Load an initial batch atomically using the bulk loader.
    loaded = inventory.add_many(
        [
            ("A100", "USB Cable", "Electronics", 9.99, 40),
            ("A200", "Mouse", "Electronics", 24.50, 6),
            ("B200", "Stapler", "Office", 12.00, 3),
        ]
    )
    assert loaded == 3
    assert len(inventory) == 3
    assert inventory.find("A200").name == "Mouse"
    assert inventory.in_category("Electronics") == ["A100", "A200"]
    assert inventory.in_price_range(5, 20) == ["A100", "B200"]
    assert inventory.low_stock(10) == [(3, "B200"), (6, "A200")]

    print("Products loaded:", len(inventory))
    print("Find A200:", inventory.find("A200").name)
    print("Electronics:", inventory.in_category("Electronics"))
    print("Price 5 to 20:", inventory.in_price_range(5, 20))
    print("Low stock below 10:", inventory.low_stock(10))

    # Update stock, price, and category, then delete a product.
    inventory.update_quantity("B200", 50)
    inventory.update_price("A200", 5.00)
    inventory.change_category("A200", "Sale")
    inventory.remove_product("A100")

    assert inventory.in_price_range(5, 20) == ["A200", "B200"]
    assert inventory.in_category("Sale") == ["A200"]
    assert inventory.find("A100") is None
    assert inventory.low_stock(10) == [(6, "A200")]
    assert inventory.stats()["heap_entries"] == len(inventory)

    print("Low stock after restock:", inventory.low_stock(10))
    print("Price 5 to 20 after sale:", inventory.in_price_range(5, 20))
    print("Sale category:", inventory.in_category("Sale"))

    # Show bulk scaling and table shrinking after mass removal.
    bulk = InventoryManager()
    bulk.add_many(
        [(f"SKU{i:05d}", f"Item {i}", f"Cat{i % 10}", float(i % 200), i % 30) for i in range(5000)]
    )
    peak_buckets = bulk.stats()["product_buckets"]
    first_read = bulk.in_category("Cat1")
    second_read = bulk.in_category("Cat1")
    assert first_read == second_read
    assert bulk.stats()["cache_hits"] >= 1

    for i in range(4950):
        bulk.remove_product(f"SKU{i:05d}")
    shrunk_buckets = bulk.stats()["product_buckets"]
    assert shrunk_buckets < peak_buckets
    print(f"Scaled catalog peak buckets: {peak_buckets}, after shrink: {shrunk_buckets}")
    print("System stats:", bulk.stats())
    print("Demo checks passed.")


if __name__ == "__main__":
    main()
