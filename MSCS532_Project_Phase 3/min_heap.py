"""Binary min heaps for general values and keyed in place priority updates.

MinHeap keeps full support for simple values and adds bottom up O(n) building.
IndexedMinHeap tracks each SKU slot and uses hole sifting so stock updates and
deletions run in O(log n) time in place without leaving stale duplicates behind.
"""


class MinHeap:
    __slots__ = ("_data",)

    def __init__(self, items=None):
        self._data = list(items) if items is not None else []
        if len(self._data) > 1:
            self.heapify()

    def heapify(self):
        """Arrange existing items into heap order in O(n) time from the bottom up."""
        for i in range(len(self._data) // 2 - 1, -1, -1):
            self._sift_down(i)

    def push(self, item):
        """Append item and move it up into heap order in O(log n) time."""
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def pop(self):
        """Remove and return the smallest item in O(log n) time."""
        if not self._data:
            raise IndexError("pop from empty heap")
        smallest = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            self._sift_down(0)
        return smallest

    def peek(self):
        """Return the smallest item without removing it, or None when empty."""
        return self._data[0] if self._data else None

    def _sift_up(self, i):
        data = self._data
        item = data[i]
        while i > 0:
            parent = (i - 1) // 2
            if item < data[parent]:
                data[i] = data[parent]
                i = parent
            else:
                break
        data[i] = item

    def _sift_down(self, i):
        data = self._data
        n = len(data)
        item = data[i]
        half = n // 2
        while i < half:
            child = 2 * i + 1
            right = child + 1
            if right < n and data[right] < data[child]:
                child = right
            if data[child] < item:
                data[i] = data[child]
                i = child
            else:
                break
        data[i] = item

    def __len__(self):
        return len(self._data)


class IndexedMinHeap:
    """Binary min heap that maps each unique key to its current array slot.

    Entries are stored as (priority, key) tuples so ties break by key in the
    same order as Phase 2. Because updates edit the slot in place, heap size
    always equals the live product count and no rebuild pass is ever needed.
    """

    __slots__ = ("_data", "_positions")

    def __init__(self):
        self._data = []
        self._positions = {}

    def build(self, pairs):
        """Load (priority, key) pairs in O(n) time using bottom up heap construction."""
        self._data = list(pairs)
        for i in range(len(self._data) // 2 - 1, -1, -1):
            self._sift_down_init(i)
        self._positions = {key: i for i, (_, key) in enumerate(self._data)}

    def _sift_down_init(self, i):
        data = self._data
        n = len(data)
        item = data[i]
        half = n // 2
        while i < half:
            child = 2 * i + 1
            right = child + 1
            if right < n and data[right] < data[child]:
                child = right
            if data[child] < item:
                data[i] = data[child]
                i = child
            else:
                break
        data[i] = item

    def push_or_update(self, key, priority):
        """Insert a new key or update an existing key priority in O(log n) time."""
        entry = (priority, key)
        positions = self._positions
        index = positions.get(key)
        if index is None:
            index = len(self._data)
            self._data.append(entry)
            self._sift_up(index, entry)
            return
        old_entry = self._data[index]
        if entry < old_entry:
            self._sift_up(index, entry)
        elif entry > old_entry:
            self._sift_down(index, entry)

    def remove_key(self, key):
        """Delete key from the heap in O(log n) time, or raise KeyError."""
        index = self._positions.pop(key)
        last_entry = self._data.pop()
        if index < len(self._data):
            old_entry = self._data[index]
            if last_entry < old_entry:
                self._sift_up(index, last_entry)
            else:
                self._sift_down(index, last_entry)

    def peek(self):
        """Return the smallest (priority, key) pair without removing it."""
        return self._data[0] if self._data else None

    def below_threshold(self, threshold):
        """Collect all (priority, key) pairs below threshold without changing the heap.

        Walking only branches whose priority is below threshold visits at most
        2k + 1 heap slots for k matches, then sorts the k matches in O(k log k).
        """
        data = self._data
        n = len(data)
        if n == 0 or data[0][0] >= threshold:
            return []
        matches = []
        stack = [0]
        while stack:
            i = stack.pop()
            if data[i][0] < threshold:
                matches.append(data[i])
                left = 2 * i + 1
                right = left + 1
                if left < n:
                    stack.append(left)
                if right < n:
                    stack.append(right)
        matches.sort()
        return matches

    def _sift_up(self, i, entry):
        data = self._data
        positions = self._positions
        while i > 0:
            parent = (i - 1) // 2
            parent_entry = data[parent]
            if entry < parent_entry:
                data[i] = parent_entry
                positions[parent_entry[1]] = i
                i = parent
            else:
                break
        data[i] = entry
        positions[entry[1]] = i

    def _sift_down(self, i, entry):
        data = self._data
        positions = self._positions
        n = len(data)
        half = n // 2
        while i < half:
            child = 2 * i + 1
            right = child + 1
            if right < n and data[right] < data[child]:
                child = right
            child_entry = data[child]
            if child_entry < entry:
                data[i] = child_entry
                positions[child_entry[1]] = i
                i = child
            else:
                break
        data[i] = entry
        positions[entry[1]] = i

    def __len__(self):
        return len(self._data)
