import logging
import time
from typing import Any

logger = logging.getLogger("babylon60.engine.api_keys")

# C5-REAL: Base-60 rate limit evaluation
BABYLON_BASE = 60

class TierRateLimits:
    DEVELOPER = 10000 / (30 * 24 * 60 * 60) # Events per second
    PRO = 1000000 / (30 * 24 * 60 * 60)
    ENTERPRISE = float('inf')

class APIKeyManager:
    """
    MTK-Compliant API Key and SaaS Tier Validator.
    """
    def __init__(self, db_conn):
        self.conn = db_conn
        self._ensure_tables()

    def _ensure_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_api_keys (
                api_key TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                tier TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                last_event_time REAL DEFAULT 0,
                token_bucket REAL DEFAULT 0
            )
        """)
        self.conn.commit()

    def register_tenant(self, api_key: str, tenant_id: str, tier: str = "DEVELOPER"):
        cursor = self.conn.cursor()
        bucket_size = self._get_bucket_size(tier)
        cursor.execute("""
            INSERT OR IGNORE INTO tenant_api_keys (api_key, tenant_id, tier, token_bucket)
            VALUES (?, ?, ?, ?)
        """, (api_key, tenant_id, tier, bucket_size))
        self.conn.commit()

    def _get_bucket_size(self, tier: str) -> float:
        if tier == "DEVELOPER":
            return 10.0
        elif tier == "PRO":
            return 1000.0
        return 10000.0

    def _get_refill_rate(self, tier: str) -> float:
        if tier == "DEVELOPER":
            return TierRateLimits.DEVELOPER
        elif tier == "PRO":
            return TierRateLimits.PRO
        return TierRateLimits.ENTERPRISE

    def validate_and_consume(self, api_key: str) -> dict[str, Any]:
        """
        Validates API key and applies Tier-based rate limiting using Token Bucket algorithm.
        Returns tenant details if valid, raises Exception if rate limited or invalid.
        """
        cursor = self.conn.cursor()
        # Enforce WAL strict transaction
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute("""
                SELECT tenant_id, tier, is_active, last_event_time, token_bucket
                FROM tenant_api_keys WHERE api_key = ?
            """, (api_key,))
            row = cursor.fetchone()

            if not row:
                raise ValueError("Invalid API Key")

            tenant_id, tier, is_active, last_event_time, token_bucket = row

            if not is_active:
                raise ValueError("API Key is revoked or suspended")

            now = time.monotonic()
            elapsed = now - last_event_time
            refill_rate = self._get_refill_rate(tier)
            bucket_size = self._get_bucket_size(tier)

            # Refill
            new_tokens = min(bucket_size, token_bucket + elapsed * refill_rate)

            if new_tokens < 1.0:
                logger.warning(f"Tenant {tenant_id} rate limited (Tier: {tier})")
                raise ValueError("Rate limit exceeded")

            new_tokens -= 1.0

            cursor.execute("""
                UPDATE tenant_api_keys
                SET last_event_time = ?, token_bucket = ?
                WHERE api_key = ?
            """, (now, new_tokens, api_key))
            
            self.conn.commit()
            return {"tenant_id": tenant_id, "tier": tier}
        except Exception as e:
            self.conn.rollback()
            raise e
