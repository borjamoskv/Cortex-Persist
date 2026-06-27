# [C5-REAL] Exergy-Maximized
class CircuitBreaker:
    def __init__(self, threshold=5):
        self.failures = 0
        self.threshold = threshold
        self.open = False

    def call(self, fn, *args, **kwargs):
        if self.open:
            raise Exception("CIRCUIT OPEN")

        try:
            result = fn(*args, **kwargs)
            self.failures = 0
            return result

        except (ValueError, TypeError, OSError, RuntimeError, ConnectionError, TimeoutError) as e:
            self.failures += 1

            if self.failures >= self.threshold:
                self.open = True

            raise e
