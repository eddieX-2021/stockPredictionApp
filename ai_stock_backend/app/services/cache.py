import time

class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self.store = {}

    def get(self, key):
        val = self.store.get(key)
        if not val:
            return None
        data, ts = val
        if time.time() - ts > self.ttl:
            del self.store[key]
            return None
        return data

    def set(self, key, value):
        self.store[key] = (value, time.time())
