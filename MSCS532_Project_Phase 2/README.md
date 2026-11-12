# Phase 2 Inventory Proof of Concept

This folder contains the Phase 2 version of the inventory project.

## Run in VS Code

```powershell
cd phase2
python main.py
python test_inventory.py
```


The demonstration ends with `Demo checks passed.` The test script runs 30 tests and should end with `OK`.

## Files

| File | Purpose |
| :--- | :--- |
| product.py | Immutable product records and input checks |
| hash_table.py | Custom separate chaining hash table |
| min_heap.py | Custom binary min heap |
| price_index.py | Sorted price pairs and inclusive range search |
| inventory_manager.py | Shared operations that keep the indexes consistent |
| main.py | Demonstration with expected result checks |
| test_inventory.py | Thirty automated tests |
| evidence | Saved output from the supplied execution environment |

## What changed

1. Input checks now reject negative quantities, invalid prices, empty text, and duplicate products.
2. Frozen product records prevent callers from changing values without updating the indexes.
3. Price queries walk the list by position instead of copying its entire remaining section.
4. Heap entries carry a revision number. Old entries are rejected even when a SKU is removed and reused.
5. Heap cleanup runs after quantity changes and deletions.
6. Empty categories are removed.
7. Tests cover individual structures and a sequence of 200 mixed inventory operations.

## Contracts

SKUs, names, and categories must contain text with no surrounding spaces. SKUs and categories are case sensitive. Quantities are nonnegative integers. Prices are finite nonnegative integers or floats. Booleans are not accepted as quantities or prices.

Price range bounds are inclusive. Low stock means strictly below the threshold. Searching for an absent SKU returns `None`. Changing or deleting an absent SKU raises `KeyError`. Duplicate SKUs and invalid values raise `ValueError`.

Use InventoryManager for application changes. A leading underscore marks internal attributes that callers should not change.

## Scope and cost

Let n be the current number of products, h the heap size, k the result count, and B the product table bucket count.

* SKU lookup is expected O(1) under well distributed hashes and worst case O(n).
* Inserting into the hash table is expected amortized O(1). A resize has linear cost.
* The sorted price index has O(n) insertion and deletion and O(log n + k) search.
* Category output is sorted, so returning k SKUs costs O(k log k).
* A normal quantity update costs expected O(log h). A cleanup scans the table and pushes all live entries, costing O(B + n log n).
* A stock report that removes m entries and restores k valid entries costs expected O((m + k) log(h + 1)), including expected hash lookups.
* Heap cleanup keeps h at most 2n + 16 after stock updates and deletions. Hash tables grow but do not shrink, so retained space depends on their historical peak size.

These are code based bounds, not measured performance results. The tests check correctness, not response time.

## Remaining work

This is a single user prototype. It does not save data after exit, coordinate concurrent users, provide transaction rollback after resource failures, or include a graphical interface. Prices remain floats for continuity with Phase 1. Decimal values or integer cents are planned before financial calculations are added.

## Evidence

The saved outputs were produced with Python 3.14.8 in the supplied Linux environment. The report uses the test count and demonstrated values, not the elapsed test time as a speed claim. Running tests on your computer may change timing and hash bucket placement.



