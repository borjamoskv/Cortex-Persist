"""
CORTEX-PERSIST: Ouroboros Node Keeper
C5-REAL MVP
"""
import asyncio
import logging
from fastapi import FastAPI
import uvicorn
from .monitor import collect_metrics
from .evaluator import evaluate_health
from .planner import detect_anomalies, generate_plan
from .executor import execute_plan
from .memory import save_heartbeat, save_memory
from .telegram_bot import notify_human

app = FastAPI(title="Ouroboros Node Keeper")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ouroboros")

@app.get("/health")
def read_health():
    return {"status": "active", "ouroboros": "eating_tail"}

async def ouroboros_loop():
    logger.info("Starting Ouroboros Loop...")
    while True:
        try:
            state = await collect_metrics()
            health = evaluate_health(state)
            anomalies = detect_anomalies(state, health)

            if anomalies:
                plan = generate_plan(anomalies, state)
                if plan:
                    result = await execute_plan(plan)
                    new_state = await collect_metrics()
                    outcome = "improved" if evaluate_health(new_state)["health_score"] > health["health_score"] else "worse"
                    save_memory(state, plan, result, outcome)

                    if outcome == "worse":
                        await notify_human(f"⚠️ Action {plan['name']} made things worse. Requires attention.")
            else:
                save_heartbeat(state)

            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ouroboros loop error: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ouroboros_loop())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
