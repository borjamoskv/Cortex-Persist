import asyncio
import logging
import os
import sys
import time

import aiosqlite

# Set up cortex module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from cortex.graph.engine import process_fact_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("heal_graph")

async def main():
    db_path = os.path.expanduser("~/.cortex/cortex.db")
    
    async with aiosqlite.connect(db_path) as conn:
        logger.info("Starting graph healing process...")
        
        # Select all valid facts
        cursor = await conn.execute(
            "SELECT id, content, project, timestamp, tenant_id FROM facts WHERE is_tombstoned = 0"
        )
        facts = await cursor.fetchall()
        
        logger.info(f"Found {len(facts)} facts to process.")
        
        total_entities = 0
        total_relations = 0
        total_processed = 0
        
        for fact_id, content, project, timestamp, tenant_id in facts:
            # We must pass the timestamp as a string since sqlite native timestamp is REAL/TEXT
            ts_str = str(timestamp) if timestamp else str(time.time())
            
            e_count, r_count = await process_fact_graph(
                conn, 
                fact_id=fact_id, 
                content=content, 
                project=project, 
                timestamp=ts_str,
                tenant_id=tenant_id
            )
            
            total_entities += e_count
            total_relations += r_count
            total_processed += 1
            
            if total_processed % 50 == 0:
                logger.info(f"Processed {total_processed}/{len(facts)} facts. Added {total_entities} entities, {total_relations} relations.")
                await conn.commit()
                
        await conn.commit()
        logger.info(f"Healing complete. Processed {total_processed} facts.")
        logger.info(f"Total entities extracted: {total_entities}")
        logger.info(f"Total relationships extracted: {total_relations}")

if __name__ == "__main__":
    asyncio.run(main())
