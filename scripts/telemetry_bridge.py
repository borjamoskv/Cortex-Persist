import asyncio
import json
import os
from pathlib import Path
from cortex.cli.common import get_engine
from cortex.timing.chronos import ChronosEngine

async def bridge():
    # Use default DB
    db_path = Path.home() / ".cortex" / "cortex.db"
    if not db_path.exists():
        print(f"Error: DB not found at {db_path}")
        return

    engine = get_engine(str(db_path))
    try:
        # 1. Base Stats
        stats = await engine.stats()
        
        # 2. Advanced Chronos Aggregation
        # Query all facts that have 'chronos' in meta
        async with engine.session() as conn:
            cursor = await conn.execute(
                "SELECT meta FROM facts WHERE meta LIKE '%chronos%'"
            )
            rows = await cursor.fetchall()
            
            total_human_secs = 0.0
            total_ai_secs = 0.0
            for (meta_raw,) in rows:
                try:
                    meta = json.loads(meta_raw)
                    chronos = meta.get("chronos")
                    if chronos:
                        total_human_secs += chronos.get("human_time_secs", 0)
                        total_ai_secs += chronos.get("ai_time_secs", 0)
                except Exception:
                    continue

        # 3. Format Output
        human_time_saved_hrs = round(total_human_secs / 3600, 1)
        # ROI: Estimating $180/hr (Senior Architect rate)
        economic_roi = round(human_time_saved_hrs * 180, 2)
        
        telemetry = {
            "active_facts": stats["active_facts"],
            "project_count": stats["project_count"],
            "human_time_saved_hrs": human_time_saved_hrs,
            "economic_roi_usd": economic_roi,
            "tactical_asymmetry": round(total_human_secs / total_ai_secs, 1) if total_ai_secs > 0 else 0,
            "db_size_mb": stats["db_size_mb"],
            "timestamp": stats.get("timestamp", "2026-03-01T03:17:00")
        }

        # Save to GordaCorp Data
        output_dir = Path("/Users/borjafernandezangulo/cortex/gordacorp-immersive/data")
        output_dir.mkdir(exist_ok=True)
        
        with open(output_dir / "telemetry.json", "w") as f:
            json.dump(telemetry, f, indent=2)
            
        print(f"✅ Telemetry updated: {telemetry['active_facts']} facts, {human_time_saved_hrs}h saved.")

    finally:
        await engine.close()

if __name__ == "__main__":
    asyncio.run(bridge())
