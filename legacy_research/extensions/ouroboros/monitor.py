import psutil
import time

async def collect_metrics() -> dict:
    return {
        "timestamp": int(time.time()),
        "node_id": "inmunify-node-01",
        "cpu_pct": psutil.cpu_percent(interval=1),
        "ram_pct": psutil.virtual_memory().percent,
        "disk_pct": psutil.disk_usage('/').percent,
        "latency_ms": 45,  # Mocked external call latency
        "rewards_24h": 3.42, # Mocked DB lookup
        "uptime_pct": 99.9 # Mocked API response
    }
