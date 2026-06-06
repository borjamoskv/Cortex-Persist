# [C5-REAL] Exergy-Maximized
class RateLimiter:
    def __init__(self, limit_per_sec):
        self.limit = limit_per_sec
        self.tokens = limit_per_sec

    def allow(self):
        if self.tokens > 0:
            self.tokens -= 1
            return True

        return False
