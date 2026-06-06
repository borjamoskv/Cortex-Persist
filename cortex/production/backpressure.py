# [C5-REAL] Exergy-Maximized
def apply_backpressure(queue_size, max_size=1000):
    if queue_size > max_size:
        return {"accept_requests": False, "drop_ratio": 0.3}

    return {"accept_requests": True}
