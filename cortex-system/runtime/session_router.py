"""
C5-REAL: Session Router
Author: Borja Moskv / borjamoskv
"""

import sys
import os
import sqlite3
from typing import Dict, Any, Optional

# Inject parent paths to resolve babylon60 imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from babylon60.extensions.artist_cortex.artist_cortex import ArtistCortexEngine

class SessionRouter:
    def __init__(self, db_path: str = "artist_cortex.db"):
        self.db_path = db_path
        self.engine = ArtistCortexEngine(db_path=self.db_path)
        self._ensure_migrations()

    def _ensure_migrations(self):
        """Applies foundational schema if tables are not initialized."""
        # Check if cortex_sessions exists
        cursor = self.engine.conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM cortex_sessions LIMIT 1")
        except sqlite3.OperationalError:
            # Table does not exist, run migrations from the artist_cortex module
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            mig_dir = os.path.join(base_dir, "babylon60", "extensions", "artist_cortex", "migrations")
            paths = [
                os.path.join(mig_dir, "001_init.sql"),
                os.path.join(mig_dir, "002_triggers.sql"),
                os.path.join(mig_dir, "003_seed_agents.sql")
            ]
            self.engine.apply_migrations(paths)

    def route_session(self, operator_id: str, core_vector: str = "ARTE_PURO", notes: Optional[str] = None) -> int:
        """
        Creates a new session record in the DB and returns the ID.
        Ensures strict core_vector constraints.
        """
        if core_vector not in ("ARTE_PURO", "RECONOCIMIENTO_LIQUIDO", "PROTECCION_DE_IDENTIDAD"):
            raise ValueError(f"Invalid core vector: {core_vector}")
        
        cursor = self.engine.conn.cursor()
        cursor.execute("""
            INSERT INTO cortex_sessions (operator_id, core_vector, notes)
            VALUES (?, ?, ?)
        """, (operator_id, core_vector, notes))
        self.engine.conn.commit()
        return cursor.lastrowid

    def end_session(self, session_id: int):
        """Closes the session setting ended_at timestamp."""
        cursor = self.engine.conn.cursor()
        cursor.execute("""
            UPDATE cortex_sessions
            SET ended_at = datetime('now')
            WHERE id = ?
        """, (session_id,))
        self.engine.conn.commit()

    def close(self):
        self.engine.close()
