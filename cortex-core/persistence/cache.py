
import time
from collections import OrderedDict




class ContextCache:
    """L1 Ephemeral Context Cache - O(1) LRU eviction, TTL-bounded."""

    __slots__ = ('_cache', '_ttl', '_capacity')

    def __init__(self, ttl: int = 300, capacity: int = 10000):
        self._cache: OrderedDict = OrderedDict()
        self._ttl = ttl
        self._capacity = capacity

    def put(self, content_key: str, payload: dict):
        now = time.monotonic()
        if content_key in self._cache:
            self._cache.move_to_end(content_key)
        self._cache[content_key] = {"payload": payload, "timestamp": now}
        while len(self._cache) > self._capacity:
            self._cache.popitem(last=False)

    def get(self, content_key: str) -> dict | None:
        if content_key in self._cache:
            entry = self._cache[content_key]
            if time.monotonic() - entry["timestamp"] < self._ttl:
                self._cache.move_to_end(content_key)
                return entry["payload"]
            else:
                del self._cache[content_key]
        return None

    def inject_anthropic_headers(self, message_blocks: list) -> list:
        formatted_blocks = []
        for i, block in enumerate(message_blocks):
            new_block = dict(block)
            if len(str(block.get("text", ""))) > 2048 or i == len(message_blocks) - 1:
                new_block["cache_control"] = {"type": "ephemeral"}
            formatted_blocks.append(new_block)
        return formatted_blocks

    def __len__(self) -> int:
        return len(self._cache)

    def clear(self):
        self._cache.clear()
