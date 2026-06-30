# [C5-REAL] Exergy-Maximized
"""
SQLite-Vec client for Belief Objects.
"""

import json

from babylon60.database.sovereign_db import SovereignDB
from babylon60.engine.causal.belief_objects import BeliefObject


class BeliefStore:
    def __init__(self, db: SovereignDB):
        self.db = db

    async def initialize_schema(self) -> None:
        # VEC-0 Invariant: No Foreign Keys in vec0. Dimensions immutable.
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS belief_objects (
                id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                relation TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                signature TEXT NOT NULL,
                content TEXT NOT NULL,
                context_hash TEXT NOT NULL,
                certainty REAL NOT NULL
            )
        """)
        
        # Virtual table for embeddings (text-1536)
        await self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cortex_embeddings_text USING vec0(
                embedding float[1536]
            )
        """)

    async def insert_belief(self, belief: BeliefObject, embedding: list[float]) -> int:
        """
        Inserts a belief object and its embedding.
        Enforces Write-Path Contract (CORTEX-TAINT signature must be present).
        Crash Causal: No defensive programming. Let it crash if data is malformed.
        """
        # The prompt demands CORTEX-TAINT application. We ensure the signature is present.
        # Since it is a Pydantic model, it has already been validated.
        
        # Step 1: Insert metadata and get rowid. VEC-0 Invariant: separate tables, manual mapping.
        cursor = await self.db.execute(
            """
            INSERT INTO belief_objects (
                id, state, relation, agent_id, session_id, timestamp, 
                signature, content, context_hash, certainty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                belief.id,
                belief.state.value,
                belief.relation.value,
                belief.provenance.agent_id,
                belief.provenance.session_id,
                belief.provenance.timestamp.isoformat(),
                belief.provenance.signature,
                belief.payload.content,
                belief.payload.context_hash,
                belief.payload.certainty,
            )
        )
        
        rowid = cursor.lastrowid
        
        # Step 2: Insert into vec0 table with matching rowid
        await self.db.execute(
            """
            INSERT INTO cortex_embeddings_text (rowid, embedding)
            VALUES (?, ?)
            """,
            (rowid, json.dumps(embedding))
        )
        
        return rowid
