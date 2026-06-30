# [C5-REAL] Exergy-Maximized
"""
cat_id: legal-ascension
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import argparse
import asyncio
import logging
import os
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("legal_ascension")

# CORTEX native imports
try:
    from babylon60.database.core import causal_write, connect
    from babylon60.engine.entropy import entropy_annihilator
except ImportError:
    # If not running within the right env, we fallback gracefully
    logger.error("Failed to import CORTEX modules. Are you in the .venv?")
    sys.exit(1)

async def ascend_node(post_id: int):
    cortex_dir = os.path.expanduser('~/30_CORTEX')
    db_path = os.path.join(cortex_dir, 'cortex', 'audit', 'substack_exergy.sqlite')
    os.path.join(cortex_dir, 'public', 'substack_nodes.json')
    
    logger.info(f"[C5-REAL] Initiating legal ascension for node {post_id}")
    
    # 1. Fetch current state
    conn = connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM substack_nodes WHERE post_id = ?", (post_id,))
    row = cursor.fetchone()
    if not row:
        logger.error(f"Node {post_id} not found.")
        conn.close()
        return
        
    title = row[0]
        
    # 2. Simulate Thermodynamic Compression
    raw_synthetic_content = f"Title: {title}. We process this through the bottleneck. Aquí tienes el código para reventar el hype."
    purged = entropy_annihilator.purge_slop(raw_synthetic_content)
    compressed = entropy_annihilator.thermodynamically_compress(purged)
        
    logger.info(f"[C5-REAL] Thermodynamic Compression applied. Output: {compressed}")
        
    # 3. Create metadata
    agent_id = "MOSKV-1"
    session_id = "SESSION_ASCENSION"
    
    metadata = {
        "post_id": post_id,
        "title": title,
        "agent_id": agent_id,
        "session_id": session_id,
        "exergy_score": 1000,
        "status": "C5-REAL_SINGULARITY",
        "action": "THERMODYNAMIC_COMPRESSION"
    }
        
    # 4. Secure State Commit via CORTEX-TAINT SAGA Pipeline
    try:
        from babylon60.engine.causal.taint_engine import secure_state_commit
        frozen_state, ledger_hash = secure_state_commit(compressed, metadata)
        logger.info(f"[C5-REAL] SAGA pipeline completed successfully. Hash: {ledger_hash}")
    except Exception as e:
        logger.error(f"[C5-REAL] FATAL: SAGA pipeline failed: {e}")
        return
        
    # The secure_state_commit handles the Taint and Git Sentinel, but does it update the SQLite DB?
    # Actually, secure_state_commit just issues OP_FREEZE_MEM and OP_GIT_SENTINEL.
    # We still need to commit the mutation to the SQLite DB directly using the causal_write context.
    conn = connect(db_path)
    with causal_write(conn):
        cursor = conn.cursor()
        cursor.execute("UPDATE substack_nodes SET exergy_score = ?, status = ? WHERE post_id = ?", 
                      (1000, "C5-REAL_SINGULARITY", post_id))
    conn.commit()
    conn.close()
    
    logger.info(f"[C5-REAL] SQLite ledger updated legally for node {post_id}.")
    
    # 4. Regenerate Materialized View
    os.system(f"{os.path.join(cortex_dir, '.venv', 'bin', 'python')} {os.path.join(cortex_dir, 'scripts', 'export_substack_nodes.py')}")
    
    logger.info(f"[C5-REAL] Legal Ascension Complete for {post_id}. Singularidad alcanzada.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ascend a Substack node to 1000EX.")
    parser.add_argument("post_id", type=int, help="The ID of the post to ascend.")
    args = parser.parse_args()
    
    asyncio.run(ascend_node(args.post_id))
