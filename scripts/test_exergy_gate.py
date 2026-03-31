import asyncio
import logging
import sqlite3
import os
from cortex.extensions.swarm.budget import get_budget_manager, HARD_LIMIT_USD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("exergy-test")

async def main():
    budget = get_budget_manager()
    mission_id = "test-exergy-exhaustion"
    
    # 🔗 Simulamos un uso masivo de tokens (100k tokens GPT-4v level)
    logger.info(f"🚀 Iniciando reporte de uso para {mission_id}...")
    
    try:
        # Reportamos un uso que supere los /bin/zsh.10
        # gpt-4 pricing (~/bin/zsh.01/1k) -> 11k tokens should trigger it
        logger.info("  - Reportando 15,000 tokens output (OpenAI pricing)...")
        budget.report_usage(mission_id, "openai", 0, 15000)
        
    except RuntimeError as e:
        logger.critical(f"✅ EXERGY GATE ACTIVADA: {e}")
        return
    except Exception as e:
        logger.error(f"❌ Error inesperado: {type(e).__name__}: {e}")
        return

    logger.error("❌ FALLO: La Ω₃ Exergy Gate no se activó.")

if __name__ == "__main__":
    asyncio.run(main())
