def evaluate_health(state: dict) -> dict:
    cpu_score = max(0, 100 - state["cpu_pct"]) / 100
    ram_score = max(0, 100 - state["ram_pct"]) / 100
    
    # Base formula from MVP requirements
    health_score = (cpu_score * 0.4) + (ram_score * 0.4) + 0.2
    
    return {
        "health_score": round(health_score, 2),
        "status": "healthy" if health_score > 0.6 else "degraded"
    }
