"""Run a small demonstration with checks of the expected results."""
from inventory_manager import InventoryManager


def main():
    inventory = InventoryManager()
    inventory.add_product("A100", "USB Cable", "Electronics", 9.99, 40)
    inventory.add_product("A200", "Mouse", "Electronics", 24.50, 6)
    inventory.add_product("B200", "Stapler", "Office", 12.00, 3)
    assert len(inventory) == 3
    assert inventory.find("A200").name == "Mouse"
    assert inventory.in_category("Electronics") == ["A100", "A200"]
    assert inventory.in_price_range(5, 20) == ["A100", "B200"]
    print("Products inserted:", len(inventory))
    print("Find A200:", inventory.find("A200").name)
    print("Electronics:", inventory.in_category("Electronics"))
    print("Price 5 to 20:", inventory.in_price_range(5, 20))
    assert inventory.low_stock(10) == [(3, "B200"), (6, "A200")]
    print("Low stock before changes:", inventory.low_stock(10))

    inventory.update_quantity("B200", 50)
    inventory.update_price("A200", 5.00)
    inventory.change_category("A200", "Sale")
    inventory.remove_product("A100")
    assert inventory.in_price_range(5, 20) == ["A200", "B200"]
    assert inventory.in_category("Sale") == ["A200"]
    assert inventory.find("A100") is None
    assert inventory.low_stock(10) == [(6, "A200")]
    print("Low stock after restock:", inventory.low_stock(10))
    print("Price 5 to 20 after sale:", inventory.in_price_range(5, 20))
    print("Sale category:", inventory.in_category("Sale"))
    print("Deleted A100:", inventory.find("A100"))

    try:
        inventory.add_product("A200", "Duplicate", "Sale", 5, 1)
    except ValueError as error:
        print("Duplicate rejected:", error)
    try:
        inventory.update_quantity("A200", -1)
    except ValueError as error:
        print("Invalid quantity rejected:", error)
    assert inventory.find("A200").quantity == 6
    print("Empty price search:", inventory.in_price_range(100, 200))
    print("Demo checks passed.")


if __name__ == "__main__":
    main()
