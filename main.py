"""Small demo of the inventory system."""
from inventory_manager import InventoryManager


def main():
    inv = InventoryManager()
    inv.add_product("A100", "USB Cable", "Electronics", 9.99, 40)
    inv.add_product("A200", "Wireless Mouse", "Electronics", 24.50, 6)
    inv.add_product("B100", "Notebook", "Office", 3.25, 120)
    inv.add_product("B200", "Stapler", "Office", 12.00, 3)
    inv.add_product("C100", "Water Bottle", "Outdoor", 15.75, 18)

    print("Find A200:", inv.find("A200"))
    print("Office items:", inv.in_category("Office"))
    print("Price $5 to $20:", inv.in_price_range(5, 20))
    print("Low stock (under 10):", inv.low_stock(10))

    inv.update_quantity("B200", 50)     # restocked the stapler
    inv.update_price("C100", 4.99)      # water bottle on sale
    inv.change_category("C100", "Sale")
    inv.remove_product("A100")

    print("\nAfter updates")
    print("Low stock (under 10):", inv.low_stock(10))
    print("Price $5 to $20:", inv.in_price_range(5, 20))
    print("Sale items:", inv.in_category("Sale"))
    print("Products left:", len(inv))


if __name__ == "__main__":
    main()
