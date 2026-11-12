"""A product record and shared input checks."""
from dataclasses import dataclass
from math import isfinite


def check_text(value, field):
    """Require a meaningful string with no surrounding spaces."""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be text without surrounding spaces")


def check_quantity(value):
    """Reject negative stock, fractions, strings, and booleans."""
    if type(value) is not int or value < 0:
        raise ValueError("quantity must be a nonnegative integer")


def check_price(value):
    """Accept only finite, nonnegative numbers."""
    if type(value) not in (int, float) or value < 0:
        raise ValueError("price must be a finite nonnegative number")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("price must be a finite nonnegative number")


@dataclass(frozen=True)
class Product:
    """An immutable record. Changes must go through InventoryManager."""
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
