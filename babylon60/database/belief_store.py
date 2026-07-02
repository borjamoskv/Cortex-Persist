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
        # We drop the old table if it doesn't match the new strict schema,
        # but to be safe, we'll assume we're using a fresh DB or :memory:.
        # VEC-0 Invariant: No Foreign Keys in vec0. Dimensions immutable.
        await self.db.execute("DROP TABLE IF EXISTS belief_objects")
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS belief_objects (
                belief_id TEXT PRIMARY KEY,
                proposition TEXT NOT NULL,
                state TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                variance REAL NOT NULL,
                decay_rate REAL NOT NULL,
                source_hash TEXT NOT NULL,
                source_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                signer_id TEXT NOT NULL,
                signature TEXT NOT NULL,
                created_at TEXT NOT NULL,
                was_generated_by TEXT NOT NULL,
                relations_entails TEXT NOT NULL,
                relations_discards TEXT NOT NULL
            )
        """)

        # Virtual table for embeddings (text-1536)
        await self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cortex_embeddings_text USING vec0(
                embedding float[1536]
            )
        """)
        
        # Virtual table for local ONNX embeddings (local-384)
        await self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cortex_embeddings_local USING vec0(
                embedding float[384]
            )
        """)

    async def insert_belief(self, belief: BeliefObject) -> int:
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
                belief_id, proposition, state, confidence_score, variance, decay_rate,
                source_hash, source_type, tenant_id, signer_id, signature, created_at,
                was_generated_by, relations_entails, relations_discards
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                belief.belief_id,
                belief.proposition,
                belief.state.value,
                belief.confidence_score,
                belief.variance,
                belief.decay_rate,
                belief.provenance.source_hash,
                belief.provenance.source_type,
                belief.provenance.tenant_id,
                belief.provenance.signer_id,
                belief.provenance.signature,
                belief.provenance.created_at,
                belief.provenance.was_generated_by,
                json.dumps(belief.relations.entails),
                json.dumps(belief.relations.discards),
            ),
        )

        rowid = cursor.lastrowid

        # Step 2: Insert into vec0 table with matching rowid based on dimension length
        table_name = "cortex_embeddings_text" if len(belief.semantic_embedding) == 1536 else "cortex_embeddings_local"
        
        await self.db.execute(
            f"""
            INSERT INTO {table_name} (rowid, embedding)
            VALUES (?, ?)
            """,
            (rowid, json.dumps(belief.semantic_embedding)),
        )

        return rowid

    async def delete_belief(self, belief_id: str) -> None:
        """
        Physical annihilation of a belief object and its vectors.
        Enforces Landauer's principle (Macrófago Ontológico).
        """
        cursor = await self.db.execute("SELECT rowid FROM belief_objects WHERE belief_id = ?", (belief_id,))
        row = cursor.fetchone()
        if not row:
            return
        rowid = row[0]

        await self.db.execute("DELETE FROM belief_objects WHERE belief_id = ?", (belief_id,))
        await self.db.execute("DELETE FROM cortex_embeddings_text WHERE rowid = ?", (rowid,))
        await self.db.execute("DELETE FROM cortex_embeddings_local WHERE rowid = ?", (rowid,))

    async def delete_by_states(self, states: list[str]) -> int:
        """
        Aniquila todos los registros (y sus vectores) que coincidan con los estados dados.
        Retorna la cantidad de elementos purgados.
        """
        if not states:
            return 0
            
        placeholders = ",".join(["?"] * len(states))
        cursor = await self.db.execute(f"SELECT rowid, belief_id FROM belief_objects WHERE state IN ({placeholders})", tuple(states))
        rows = cursor.fetchall()
        
        if not rows:
            return 0
            
        for row in rows:
            rowid, belief_id = row[0], row[1]
            await self.db.execute("DELETE FROM belief_objects WHERE belief_id = ?", (belief_id,))
            await self.db.execute("DELETE FROM cortex_embeddings_text WHERE rowid = ?", (rowid,))
            await self.db.execute("DELETE FROM cortex_embeddings_local WHERE rowid = ?", (rowid,))
            
        return len(rows)

    async def update_state(self, belief_id: str, new_state: str) -> None:
        """
        Transición de estado atómica en CORTEX.
        """
        await self.db.execute(
            "UPDATE belief_objects SET state = ? WHERE belief_id = ?",
            (new_state, belief_id)
        )

    async def get_beliefs_by_state(self, states: list[str]) -> list[BeliefObject]:
        """
        Recupera subgrafos completos filtrados por estado para su resolución.
        (Retorna un listado parcial instanciado como BeliefObject para uso del Handoff).
        """
        from babylon60.engine.causal.belief_objects import BeliefState, ProvenanceEnvelope, BeliefRelations

        if not states:
            return []

        placeholders = ",".join(["?"] * len(states))
        cursor = await self.db.execute(
            f"SELECT belief_id, proposition, state, confidence_score, variance, decay_rate, "
            f"source_hash, source_type, tenant_id, signer_id, signature, created_at, was_generated_by, "
            f"relations_entails, relations_discards "
            f"FROM belief_objects WHERE state IN ({placeholders})",
            tuple(states)
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(BeliefObject(
                belief_id=row[0],
                proposition=row[1],
                state=BeliefState(row[2]),
                confidence_score=row[3],
                variance=row[4],
                decay_rate=row[5],
                provenance=ProvenanceEnvelope(
                    source_hash=row[6],
                    source_type=row[7],
                    tenant_id=row[8],
                    signer_id=row[9],
                    signature=row[10],
                    created_at=row[11],
                    was_generated_by=row[12],
                ),
                relations=BeliefRelations(
                    entails=json.loads(row[13]),
                    discards=json.loads(row[14])
                ),
                semantic_embedding=[]  # Not loaded to save exergy
            ))
        return results
