# [C5-REAL] Exergy-Maximized
import asyncio
import logging
from cortex.engine import CortexEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def f():
    e = CortexEngine()
    logger.info("init_db...")
    try:
        conn = await e._get_or_create_conn()
        logger.info("got conn")
        await e._ensure_schema_ready(conn)
        logger.info("schema ready")
        await e._persistence.start()
        logger.info("persistence started")
    except Exception as ex:
        logger.error(ex)
    logger.info("done!")


if __name__ == "__main__":
    asyncio.run(f())
