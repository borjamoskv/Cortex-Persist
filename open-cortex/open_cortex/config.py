"""Open CORTEX — Configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All config via env vars. Prefix: OCORTEX_."""

    # Database
    database_url: str = "sqlite:///open_cortex.db"

    # Search
    embedding_dim: int = 384
    default_k: int = 5
    bm25_weight: float = 0.4
    ann_weight: float = 0.6

    # Metamemory thresholds
    jol_force_recall_threshold: float = 0.4
    fok_void_threshold: float = 0.3
    fok_uncertain_threshold: float = 0.6
    brier_target: float = 0.15

    # Reconsolidation
    min_evidence_sources: int = 2
    min_confidence_new: float = 0.7
    canary_window_seconds: float = 300.0  # 5 min

    # Observability
    metrics_enabled: bool = True

    model_config = {"env_prefix": "OCORTEX_"}


settings = Settings()
