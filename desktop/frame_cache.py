"""Bounded, short-lived reuse for byte-identical, completely recognized feeds.

Never reuse uncertain reads: independent OCR retries can recover missing rows.
Retain no screenshot, and never treat a cached reading as a new loot event.
"""
import copy
import hashlib
import time


class FeedCache:
    def __init__(self, seconds=15, max_entries=3):
        self.seconds = seconds
        self.max_entries = max_entries
        self.entries = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(image, tess, kind, crafting):
        return (kind, bool(crafting), str(tess), image.mode, image.size,
                hashlib.sha256(image.tobytes()).digest())

    def get(self, key, now=None):
        now = time.monotonic() if now is None else now
        for old in list(self.entries):
            if now - self.entries[old][0] >= self.seconds:
                del self.entries[old]
        entry = self.entries.get(key)
        if entry is None:
            self.misses += 1
            return None
        self.hits += 1
        result = copy.deepcopy(entry[1])
        result['cache_hit'] = True
        return result

    def put(self, key, result, now=None):
        # Chat requires a complete ordered consensus, not just some valid items.
        # Popups need a fresh read: a scrolling/fading panel can look unchanged.
        slots = result.get('slots')
        if (key[0] != 'chat' or result.get('error') or result.get('unresolved')
                or not slots or not all(slots)):
            return
        if key not in self.entries and len(self.entries) >= self.max_entries:
            del self.entries[min(self.entries, key=lambda k: self.entries[k][0])]
        self.entries[key] = (time.monotonic() if now is None else now, copy.deepcopy(result))

    def clear(self):
        self.entries.clear()
