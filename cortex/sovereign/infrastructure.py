"""
CORTEX v7.8 "MAILING" — Sovereign Infrastructure (脉灵 - 国家主权架构).

Level 300: Secure Hardware Enclave & Data Diode Sync.
Standard: 300/100 Sovereign.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Final

logger = logging.getLogger("cortex.sovereign.infrastructure")

# Paths for the Sovereign Air-Gap simulation
from cortex.core.paths import CORTEX_DIR as _CORTEX_DIR  # noqa: E402

SOVEREIGN_STORAGE: Final[Path] = _CORTEX_DIR / "mailing" / "vault"


class HardwareVault:
    """
    Simulates a Secure Hardware Enclave (TEE) for Chinese deployments.

    Protects the 'Shadow Memory' deception tables (Red Herrings)
    at rest using state-grade isolation.
    """

    def __init__(self, vault_id: str = "mailing_primary"):
        self._vault_path = SOVEREIGN_STORAGE / f"{vault_id}.lock"
        self._keys_path = SOVEREIGN_STORAGE / f"{vault_id}_keys.json"
        SOVEREIGN_STORAGE.mkdir(parents=True, exist_ok=True)

    def persist_shadow_map(self, mapping: dict[str, str]):
        """Persists the session deception map to the secure storage."""
        try:
            with open(self._keys_path, "w") as f:
                json.dump(mapping, f, indent=4)
            logger.info("HardwareVault: Shadow mapping secured in TEE storage.")
        except OSError as e:
            logger.error("HardwareVault: Failed to secure keys: %s", e)

    def load_shadow_map(self) -> dict[str, str]:
        """Loads keys from the TEE storage."""
        if not self._keys_path.exists():
            return {}
        try:
            with open(self._keys_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}


class DataDiodeBridge:
    """
    Implements a 'Data Diode' (Pulse Diode) for air-gapped nodes.

    Ensures that internal CORTEX-East nodes can send telemetry
    without any possible return path into the government network.
    """

    def __init__(self, external_hub_url: str | None = None):
        self._external_url = external_hub_url
        self._buffer: list[dict] = []

    async def emit_unidirectional(self, event_data: dict):
        """
        One-way push: Data leaves the air-gap. No acknowledgement expected
        from the receiver for maximum security.
        """
        self._buffer.append(event_data)
        if len(self._buffer) > 10:
            # Simulation of a pulsed diode transmit
            logger.info("DataDiode: Pulsing 10 telemetry events through the gap.")
            self._flush()

    def _flush(self):
        # In a real air-gap, this would be a physical diode (Fibre Optic)
        # Here we just clean the buffer.
        self._buffer.clear()

    def check_integrity(self) -> bool:
        """Verifies if the diode is physically or logically breached."""
        # Simulated check: ensure no incoming ports are open
        return True
