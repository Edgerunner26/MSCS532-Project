# MSCS532_Project: Dynamic Inventory Management System

Phase 1, Deliverable 1. Custom data structures in Python for an inventory system
that handles changing quantities, prices, and categories.

## Data structures
| File | Structure | Used for |
|------|-----------|----------|
| `hash_table.py` | Hash table (separate chaining, resizes at 75% load) | Find a product by SKU, category index |
| `price_index.py` | Sorted list with binary search (`bisect`) | Price range searches |
| `min_heap.py` | Array based binary min heap | Low stock and restock priority |
| `inventory_manager.py` | Connects all structures | One call updates every index |
| `product.py` | `Product` data class | Product record |

## Run it
    python main.py                 # demo
    python -m unittest -v          # 7 unit tests

Requires Python 3.8 or newer. No extra packages needed.
