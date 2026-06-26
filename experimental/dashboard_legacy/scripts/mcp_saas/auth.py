"""Deterministic authentication gate for the Sovereign MCP membrane."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from security_config import (
    SecurityConfigurationError,
    dump_yaml_atomically,
    parse_decimal,
    resolve_token_store_path,
)


def _serialize_balance(balance: Decimal) -> str:
    """Persist exergy balances without reintroducing float drift."""
    normalized = balance.normalize()
    if normalized == normalized.to_integral():
        return f"{normalized:.1f}"
    return format(normalized, "f")


def load_tokens(token_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load the runtime token store from an explicit or resolved path."""
    path = token_path or resolve_token_store_path()
    if not path.exists():
        raise SecurityConfigurationError(f"Token store not found at {path}.")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise SecurityConfigurationError("Token store must contain a YAML mapping.")
    return payload


def verify_and_gate(
    token: str,
    capability: str | None = None,
    *,
    token_path: Path | None = None,
) -> dict[str, Any]:
    """Validate a sovereign token and optionally gate a capability call."""
    if not token:
        return {"valid": False, "error": "MISSING_TOKEN"}
    try:
        tokens = load_tokens(token_path)
    except SecurityConfigurationError as exc:
        return {"valid": False, "error": "TOKEN_STORE_UNAVAILABLE", "detail": str(exc)}

    if token not in tokens:
        return {"valid": False, "error": "INVALID_TOKEN"}

    data = tokens[token]
    if not isinstance(data, dict):
        return {"valid": False, "error": "TOKEN_STORE_CORRUPT"}

    balance = parse_decimal(data.get("exergy_balance", 0), field_name="exergy_balance")
    if balance <= 0:
        return {"valid": False, "error": "EXERGY_DEPLETED"}

    capabilities = data.get("capabilities", [])
    if not isinstance(capabilities, list):
        return {"valid": False, "error": "TOKEN_STORE_CORRUPT"}

    if capability:
        if "*" not in capabilities and capability not in capabilities:
            return {"valid": False, "error": "CAPABILITY_UNAUTHORIZED"}

    return {
        "valid": True,
        "tenant_id": data.get("tenant_id", "unknown"),
        "balance": _serialize_balance(balance),
    }


def deduct_exergy(token: str, amount: float, *, token_path: Path | None = None) -> str | None:
    """Debit exergy from a runtime token store using an atomic write."""
    path = token_path or resolve_token_store_path()
    tokens = load_tokens(path)
    if token in tokens:
        balance = parse_decimal(tokens[token].get("exergy_balance", 0), field_name="exergy_balance")
        debit = parse_decimal(amount, field_name="debit_amount")
        tokens[token]["exergy_balance"] = _serialize_balance(max(Decimal("0"), balance - debit))
        dump_yaml_atomically(path, tokens)
        return tokens[token]["exergy_balance"]
    return None
