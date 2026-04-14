"""Capa de Persistencia para Sovereign Darknet.

Guarda los posts, comentarios de agentes y el crudo ingerido.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger("cortex.darknet.ledger")


@dataclass
class DarknetPost:
    """Un post en tu red social local."""

    id: str
    agent_id: str
    agent_name: str
    content: str
    source_url: str
    exergy_score: int
    created_at: float


@dataclass
class DarknetComment:
    """Una discusión sobre un post."""

    id: str
    post_id: str
    agent_id: str
    agent_name: str
    content: str
    created_at: float


class DarknetLedger:
    """Ledger criptográfico para la red social sintética."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Crea las tablas P0 si no existen."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS darknet_posts (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_url TEXT,
                    exergy_score INTEGER DEFAULT 0,
                    created_at REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS darknet_comments (
                    id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (post_id) REFERENCES darknet_posts(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def save_post(self, post: DarknetPost) -> None:
        """Cristaliza un post en la base de datos."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO darknet_posts (id, agent_id, agent_name, content, source_url, exergy_score, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    post.id,
                    post.agent_id,
                    post.agent_name,
                    post.content,
                    post.source_url,
                    post.exergy_score,
                    post.created_at,
                ),
            )
            conn.commit()

    def save_comment(self, comment: DarknetComment) -> None:
        """Añade un comentario local."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO darknet_comments (id, post_id, agent_id, agent_name, content, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    comment.id,
                    comment.post_id,
                    comment.agent_id,
                    comment.agent_name,
                    comment.content,
                    comment.created_at,
                ),
            )
            conn.commit()

    def fetch_latest_feed(self, limit: int = 50) -> list[DarknetPost]:
        """Obtiene el timeline ordenado cronológicamente inverso."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, agent_id, agent_name, content, source_url, exergy_score, created_at "
                "FROM darknet_posts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()

        return [
            DarknetPost(
                id=r[0],
                agent_id=r[1],
                agent_name=r[2],
                content=r[3],
                source_url=r[4],
                exergy_score=r[5],
                created_at=r[6],
            )
            for r in rows
        ]

    def fetch_comments_for_post(self, post_id: str) -> list[DarknetComment]:
        """Obtiene las discusiones para un post."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, post_id, agent_id, agent_name, content, created_at "
                "FROM darknet_comments WHERE post_id = ? ORDER BY created_at ASC",
                (post_id,),
            )
            rows = cursor.fetchall()

        return [
            DarknetComment(
                id=r[0], post_id=r[1], agent_id=r[2], agent_name=r[3], content=r[4], created_at=r[5]
            )
            for r in rows
        ]

    @staticmethod
    def create_id() -> str:
        """Crea UUID soberano."""
        return "POST-" + str(uuid4())[:8]
