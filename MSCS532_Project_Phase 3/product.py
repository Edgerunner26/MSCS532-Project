"""Product record and input validation helpers for the inventory system."""

from dataclasses import dataclass
from math import isfinite


def check_text(value, field):
    """Make sure a text field is a real string with no extra spaces on the ends."""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be text without surrounding spaces")


def check_quantity(value):
    """Allow zero or positive whole numbers only, and reject booleans."""
    if type(value) is not int or value < 0:
        raise ValueError("quantity must be a nonnegative integer")


def check_price(value):
    """Allow finite zero or positive numbers only, and reject booleans."""
    if type(value) not in (int, float) or value < 0:
        raise ValueError("price must be a finite nonnegative number")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("price must be a finite nonnegative number")


@dataclass(frozen=True, slots=True)
class Product:
    """Immutable product record that uses slots to keep memory usage low.

    Every update goes through InventoryManager so all indexes stay in sync.
    """

    sku: str
    name: str
    category: str
    price: float
    quantity: int

    def __post_init__(self):
        check_text(self.sku, "sku")
        check_text(self.name, "name")
        check_text(self.category, "category")
        check_price(self.price)
        check_quantity(self.quantity)
