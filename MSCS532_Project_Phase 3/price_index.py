"""Balanced leaf linked B plus tree for ordered price and SKU pairs.

Phase 2 stored all price pairs in one flat list, which made every insert and
delete shift up to n items in O(n) time. Grouping pairs into small sorted leaf
nodes with an internal routing tree lowers insert and delete to O(log n) while
keeping range scans at O(log n + k) by walking across linked leaves.
"""

import bisect

from product import check_price, check_text


class _LeafNode:
    __slots__ = ("pairs", "next_leaf")

    def __init__(self, pairs=None, next_leaf=None):
        self.pairs = list(pairs) if pairs is not None else []
        self.next_leaf = next_leaf


class _InternalNode:
    __slots__ = ("keys", "children")

    def __init__(self, keys=None, children=None):
        self.keys = list(keys) if keys is not None else []
        self.children = list(children) if children is not None else []


class PriceIndex:
    """Ordered price index supporting O(log n) updates and O(log n + k) range queries."""

    __slots__ = ("_max_keys", "_min_keys", "_root", "_size")

    def __init__(self, max_keys=128):
        if type(max_keys) is not int or max_keys < 4:
            raise ValueError("max_keys must be an integer of at least 4")
        self._max_keys = max_keys
        self._min_keys = max_keys // 2
        self._root = _LeafNode()
        self._size = 0

    def build_sorted(self, sorted_pairs):
        """Build the tree in O(n) time from unique (price, sku) pairs already in order."""
        pairs = list(sorted_pairs)
        self._size = len(pairs)
        if not pairs:
            self._root = _LeafNode()
            return

        step = max(self._min_keys, (self._max_keys * 3) // 4)
        chunks = [pairs[i : i + step] for i in range(0, len(pairs), step)]
        if len(chunks) > 1 and len(chunks[-1]) < self._min_keys:
            merged = chunks[-2] + chunks[-1]
            if len(merged) <= self._max_keys:
                chunks[-2:] = [merged]
            else:
                half = len(merged) // 2
                chunks[-2] = merged[:half]
                chunks[-1] = merged[half:]

        leaves = [_LeafNode(chunk) for chunk in chunks]
        for i in range(len(leaves) - 1):
            leaves[i].next_leaf = leaves[i + 1]

        level = [(leaf.pairs[0], leaf) for leaf in leaves]
        group_step = step + 1
        while len(level) > 1:
            groups = [level[i : i + group_step] for i in range(0, len(level), group_step)]
            if len(groups) > 1 and len(groups[-1]) < self._min_keys + 1:
                merged = groups[-2] + groups[-1]
                if len(merged) <= self._max_keys + 1:
                    groups[-2:] = [merged]
                else:
                    half = len(merged) // 2
                    groups[-2] = merged[:half]
                    groups[-1] = merged[half:]
            next_level = []
            for group in groups:
                keys = [entry[0] for entry in group[1:]]
                children = [entry[1] for entry in group]
                next_level.append((group[0][0], _InternalNode(keys, children)))
            level = next_level

        self._root = level[0][1]

    def add(self, price, sku):
        """Insert a unique (price, sku) pair in O(log n) time."""
        check_price(price)
        check_text(sku, "sku")
        pair = (price, sku)
        split = self._insert(self._root, pair)
        if split is not None:
            up_key, right_node = split
            self._root = _InternalNode([up_key], [self._root, right_node])

    def _insert(self, node, pair):
        if isinstance(node, _LeafNode):
            index = bisect.bisect_left(node.pairs, pair)
            if index < len(node.pairs) and node.pairs[index] == pair:
                raise ValueError("price pair already exists")
            node.pairs.insert(index, pair)
            self._size += 1
            if len(node.pairs) <= self._max_keys:
                return None
            mid = len(node.pairs) // 2
            right = _LeafNode(node.pairs[mid:], node.next_leaf)
            node.pairs = node.pairs[:mid]
            node.next_leaf = right
            return right.pairs[0], right

        child_index = bisect.bisect_right(node.keys, pair)
        split = self._insert(node.children[child_index], pair)
        if split is None:
            return None
        up_key, right_child = split
        node.keys.insert(child_index, up_key)
        node.children.insert(child_index + 1, right_child)
        if len(node.keys) <= self._max_keys:
            return None
        mid = len(node.keys) // 2
        promoted = node.keys[mid]
        right_internal = _InternalNode(node.keys[mid + 1 :], node.children[mid + 1 :])
        node.keys = node.keys[:mid]
        node.children = node.children[: mid + 1]
        return promoted, right_internal

    def remove(self, price, sku):
        """Remove an exact (price, sku) pair in O(log n) time, or raise KeyError."""
        check_price(price)
        check_text(sku, "sku")
        pair = (price, sku)
        self._delete(self._root, pair)
        if isinstance(self._root, _InternalNode) and not self._root.keys:
            self._root = self._root.children[0]

    def _delete(self, node, pair):
        if isinstance(node, _LeafNode):
            index = bisect.bisect_left(node.pairs, pair)
            if index == len(node.pairs) or node.pairs[index] != pair:
                raise KeyError(pair)
            node.pairs.pop(index)
            self._size -= 1
            return len(node.pairs) < self._min_keys

        child_index = bisect.bisect_right(node.keys, pair)
        underflow = self._delete(node.children[child_index], pair)
        if not underflow:
            return False
        self._rebalance_child(node, child_index)
        return len(node.keys) < self._min_keys

    def _rebalance_child(self, node, idx):
        child = node.children[idx]
        if isinstance(child, _LeafNode):
            if idx > 0 and len(node.children[idx - 1].pairs) > self._min_keys:
                left = node.children[idx - 1]
                child.pairs.insert(0, left.pairs.pop())
                node.keys[idx - 1] = child.pairs[0]
            elif idx + 1 < len(node.children) and len(node.children[idx + 1].pairs) > self._min_keys:
                right = node.children[idx + 1]
                child.pairs.append(right.pairs.pop(0))
                node.keys[idx] = right.pairs[0]
            elif idx > 0:
                left = node.children[idx - 1]
                left.pairs.extend(child.pairs)
                left.next_leaf = child.next_leaf
                node.keys.pop(idx - 1)
                node.children.pop(idx)
            else:
                right = node.children[1]
                child.pairs.extend(right.pairs)
                child.next_leaf = right.next_leaf
                node.keys.pop(0)
                node.children.pop(1)
            return

        if idx > 0 and len(node.children[idx - 1].keys) > self._min_keys:
            left = node.children[idx - 1]
            child.keys.insert(0, node.keys[idx - 1])
            node.keys[idx - 1] = left.keys.pop()
            child.children.insert(0, left.children.pop())
        elif idx + 1 < len(node.children) and len(node.children[idx + 1].keys) > self._min_keys:
            right = node.children[idx + 1]
            child.keys.append(node.keys[idx])
            node.keys[idx] = right.keys.pop(0)
            child.children.append(right.children.pop(0))
        elif idx > 0:
            left = node.children[idx - 1]
            left.keys.append(node.keys.pop(idx - 1))
            left.keys.extend(child.keys)
            left.children.extend(child.children)
            node.children.pop(idx)
        else:
            right = node.children[1]
            child.keys.append(node.keys.pop(0))
            child.keys.extend(right.keys)
            child.children.extend(right.children)
            node.children.pop(1)

    def range(self, low, high):
        """Return SKUs with prices between low and high inclusive in O(log n + k) time."""
        check_price(low)
        check_price(high)
        if low > high:
            raise ValueError("low price must not exceed high price")
        if self._size == 0:
            return []

        node = self._root
        probe = (low, "")
        while isinstance(node, _InternalNode):
            node = node.children[bisect.bisect_right(node.keys, probe)]

        index = bisect.bisect_left(node.pairs, probe)
        result = []
        while node is not None:
            pairs = node.pairs
            while index < len(pairs):
                price, sku = pairs[index]
                if price > high:
                    return result
                result.append(sku)
                index += 1
            node = node.next_leaf
            index = 0
        return result

    def __len__(self):
        return self._size
