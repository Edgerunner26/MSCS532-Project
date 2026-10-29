"""Product record used by the inventory system."""
from dataclasses import dataclass


@dataclass
class Product:
    """One item in the store."""
    sku: str          # unique stock keeping unit, used as the key
    name: str
    category: str
    price: float
    quantity: int
