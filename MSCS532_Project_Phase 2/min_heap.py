"""An array based binary min heap.

The smallest item is always at index 0. For the item at index i,
its children are at 2i + 1 and 2i + 2, and its parent is at (i - 1) // 2.
"""


class MinHeap:
    def __init__(self):
        self._data = []

    def push(self, item):
        """Add an item and move it up into place. O(log n)."""
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def pop(self):
        """Remove and return the smallest item. O(log n)."""
        if not self._data:
            raise IndexError("pop from empty heap")
        smallest = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            self._sift_down(0)
        return smallest

    def peek(self):
        """Look at the smallest item without removing it. O(1)."""
        return self._data[0] if self._data else None

    def _sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if self._data[i] < self._data[parent]:
                self._data[i], self._data[parent] = self._data[parent], self._data[i]
                i = parent
            else:
                break

    def _sift_down(self, i):
        n = len(self._data)
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            smallest = i
            if left < n and self._data[left] < self._data[smallest]:
                smallest = left
            if right < n and self._data[right] < self._data[smallest]:
                smallest = right
            if smallest == i:
                break
            self._data[i], self._data[smallest] = self._data[smallest], self._data[i]
            i = smallest

    def __len__(self):
        return len(self._data)
