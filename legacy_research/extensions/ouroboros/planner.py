def detect_anomalies(state: dict, health: dict) -> list:
    anomalies = []
    if state["cpu_pct"] > 90:
        anomalies.append("high_cpu")
    if state["ram_pct"] > 90:
        anomalies.append("high_ram")
    if health["health_score"] < 0.6:
        anomalies.append("low_health")
    return anomalies

def generate_plan(anomalies: list, state: dict) -> dict | None:
    if "high_cpu" in anomalies:
        return {"name": "restart_container", "target": state["node_id"], "risk": "medium"}
    if "low_health" in anomalies:
        return {"name": "flush_cache", "target": state["node_id"], "risk": "low"}
    return None
