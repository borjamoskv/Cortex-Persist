"""
CORTEX v5.0 — Configuration.

Shared settings and paths for the entire codebase.
Modernized: frozen dataclass with env-var loading + backwards-compat module proxy.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ─── Base Paths (constant, never env-overridden) ─────────────────────

CORTEX_DIR = Path.home() / ".cortex"
AGENT_DIR = Path.home() / ".agent"
DEFAULT_DB_PATH = CORTEX_DIR / "cortex.db"


# ─── Configuration Dataclass ─────────────────────────────────────────


@dataclass(slots=True)
class CortexConfig:
    """Immutable configuration loaded from environment variables."""

    # Database
    DB_PATH: str = ""
    PG_URL: str = ""  # PostgreSQL/AlloyDB URL for v6 L3

    # Security
    ALLOWED_ORIGINS: list[str] = field(default_factory=list)

    # Boot Mode (v6)
    RUNBOOT_MODE: str = "local"  # local | cloud

    # Rate Limiting
    RATE_LIMIT: int = 300
    RATE_WINDOW: int = 60

    # Graph
    GRAPH_BACKEND: str = "sqlite"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Ledger
    CHECKPOINT_BATCH_SIZE: int = 1000
    CHECKPOINT_MIN: int = 100
    CHECKPOINT_MAX: int = 1000
    CONNECTION_POOL_SIZE: int = 5

    # Federation
    FEDERATION_MODE: str = "single"
    SHARD_DIR: Path = field(default_factory=lambda: CORTEX_DIR / "shards")

    # MCP Guard
    MCP_MAX_CONTENT_LENGTH: int = 50000
    MCP_MAX_TAGS: int = 50
    MCP_MAX_QUERY_LENGTH: int = 2000

    # Cloud Storage
    STORAGE_MODE: str = "local"
    TURSO_DATABASE_URL: str = ""
    TURSO_AUTH_TOKEN: str = ""

    # Embeddings
    EMBEDDINGS_MODE: str = "local"
    EMBEDDINGS_PROVIDER: str = "gemini"
    EMBEDDINGS_DIMENSION: int = 384

    # L2 Vector Store
    VECTOR_STORE_PATH: str = ""
    VECTOR_STORE_MODE: str = "local"  # local | remote
    QDRANT_CLOUD_URL: str = ""
    QDRANT_API_KEY: str = ""

    # LLM Provider
    LLM_PROVIDER: str = ""
    LLM_MODEL: str = ""
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""

    # Langbase
    LANGBASE_API_KEY: str = ""
    LANGBASE_BASE_URL: str = "https://api.langbase.com/v1"

    # Stripe (SaaS billing)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_TABLE: dict[str, str] = field(default_factory=dict)

    # Notifications
    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    NOTIFICATIONS_MIN_SEVERITY: str = "warning"  # debug|info|warning|error|critical

    # Deployment
    DEPLOY_MODE: str = "local"

    # Context Engine
    CONTEXT_MAX_SIGNALS: int = 20
    CONTEXT_WORKSPACE_DIR: str = ""
    CONTEXT_GIT_ENABLED: bool = True

    @property
    def PROD(self) -> bool:
        """Helper to check if we are in cloud/production mode."""
        return self.DEPLOY_MODE == "cloud"

    @property
    def IS_PROD(self) -> bool:
        """Alias for PROD."""
        return self.PROD

    @classmethod
    def from_env(cls) -> CortexConfig:
        """Build configuration from environment variables."""
        storage_mode = os.environ.get("CORTEX_STORAGE", "local")
        return cls(
            DB_PATH=os.environ.get("CORTEX_DB", str(DEFAULT_DB_PATH)),
            PG_URL=os.environ.get("CORTEX_PG_URL", ""),
            RUNBOOT_MODE=os.environ.get("CORTEX_RUNBOOT", "local"),
            ALLOWED_ORIGINS=os.environ.get(
                "CORTEX_ALLOWED_ORIGINS",
                "http://localhost:3000,http://localhost:5173",
            ).split(","),
            RATE_LIMIT=int(os.environ.get("CORTEX_RATE_LIMIT", "300")),
            RATE_WINDOW=int(os.environ.get("CORTEX_RATE_WINDOW", "60")),
            GRAPH_BACKEND=os.environ.get("CORTEX_GRAPH_BACKEND", "sqlite"),
            NEO4J_URI=os.environ.get("CORTEX_NEO4J_URI", "bolt://localhost:7687"),
            NEO4J_USER=os.environ.get("CORTEX_NEO4J_USER", "neo4j"),
            NEO4J_PASSWORD=os.environ.get("CORTEX_NEO4J_PASSWORD", ""),
            CHECKPOINT_BATCH_SIZE=int(os.environ.get("CORTEX_CHECKPOINT_BATCH", "1000")),
            CHECKPOINT_MIN=int(os.environ.get("CORTEX_CHECKPOINT_MIN", "100")),
            CHECKPOINT_MAX=int(os.environ.get("CORTEX_CHECKPOINT_MAX", "1000")),
            CONNECTION_POOL_SIZE=int(os.environ.get("CORTEX_POOL_SIZE", "5")),
            FEDERATION_MODE=os.environ.get("CORTEX_FEDERATION_MODE", "single"),
            SHARD_DIR=Path(os.environ.get("CORTEX_SHARD_DIR", str(CORTEX_DIR / "shards"))),
            MCP_MAX_CONTENT_LENGTH=int(os.environ.get("CORTEX_MCP_MAX_CONTENT", "50000")),
            MCP_MAX_TAGS=int(os.environ.get("CORTEX_MCP_MAX_TAGS", "50")),
            MCP_MAX_QUERY_LENGTH=int(os.environ.get("CORTEX_MCP_MAX_QUERY", "2000")),
            STORAGE_MODE=storage_mode,
            TURSO_DATABASE_URL=os.environ.get("TURSO_DATABASE_URL", ""),
            TURSO_AUTH_TOKEN=os.environ.get("TURSO_AUTH_TOKEN", ""),
            EMBEDDINGS_MODE=os.environ.get("CORTEX_EMBEDDINGS", "local"),
            EMBEDDINGS_PROVIDER=os.environ.get("CORTEX_EMBEDDINGS_PROVIDER", "gemini"),
            EMBEDDINGS_DIMENSION=int(os.environ.get("CORTEX_EMBEDDINGS_DIM", "384")),
            VECTOR_STORE_PATH=os.environ.get(
                "CORTEX_VECTOR_STORE_PATH", str(CORTEX_DIR / "vectors")
            ),
            VECTOR_STORE_MODE=os.environ.get("CORTEX_VECTOR_STORE_MODE", "local"),
            QDRANT_CLOUD_URL=os.environ.get("QDRANT_CLOUD_URL", ""),
            QDRANT_API_KEY=os.environ.get("QDRANT_API_KEY", ""),
            LLM_PROVIDER=os.environ.get("CORTEX_LLM_PROVIDER", ""),
            LLM_MODEL=os.environ.get("CORTEX_LLM_MODEL", ""),
            LLM_BASE_URL=os.environ.get("CORTEX_LLM_BASE_URL", ""),
            LLM_API_KEY=os.environ.get("CORTEX_LLM_API_KEY", ""),
            LANGBASE_API_KEY=os.environ.get("LANGBASE_API_KEY", ""),
            LANGBASE_BASE_URL=os.environ.get("LANGBASE_BASE_URL", "https://api.langbase.com/v1"),
            STRIPE_SECRET_KEY=os.environ.get("STRIPE_SECRET_KEY", ""),
            STRIPE_WEBHOOK_SECRET=os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
            STRIPE_PRICE_TABLE=json.loads(
                os.environ.get("STRIPE_PRICE_TABLE", '{"pro": "", "team": ""}')
            ),
            DEPLOY_MODE=os.environ.get("CORTEX_DEPLOY", "local"),
            CONTEXT_MAX_SIGNALS=int(os.environ.get("CORTEX_CONTEXT_MAX_SIGNALS", "20")),
            CONTEXT_WORKSPACE_DIR=os.environ.get("CORTEX_CONTEXT_WORKSPACE", str(Path.home())),
            CONTEXT_GIT_ENABLED=os.environ.get("CORTEX_CONTEXT_GIT", "1") == "1",
            TELEGRAM_TOKEN=os.environ.get("CORTEX_TELEGRAM_TOKEN", ""),
            TELEGRAM_CHAT_ID=os.environ.get("CORTEX_TELEGRAM_CHAT_ID", ""),
            NOTIFICATIONS_MIN_SEVERITY=os.environ.get("CORTEX_NOTIFY_MIN_SEVERITY", "warning"),
        )


# ─── Module-level singleton ──────────────────────────────────────────

_cfg = CortexConfig.from_env()


def reload() -> None:
    """Reload configuration from environment variables."""
    global _cfg
    _cfg = CortexConfig.from_env()
    # Update module-level attributes for backwards compat
    _module = sys.modules[__name__]
    for attr in CortexConfig.__dataclass_fields__:
        setattr(_module, attr, getattr(_cfg, attr))

    # Set properties/helpers
    _module.PROD = _cfg.PROD
    _module.IS_PROD = _cfg.IS_PROD


# Initialize module-level attributes for backwards compatibility
# (so `from cortex.config import DB_PATH` still works)
reload()
