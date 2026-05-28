"""Security configuration helpers for Cortex-Persist runtime surfaces."""

from __future__ import annotations

import os
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import yaml
from native_paths import PROJECT_ROOT

INSECURE_API_KEY_VALUES = frozenset(
    {
        "",
        "changeme",
        "cortex_default_key",
        "cortex_secret_key_v1",
    }
)

TOKEN_STORE_ENV_VARS = ("CORTEX_MCP_TOKENS_FILE", "CORTEX_TOKEN_STORE")
API_KEY_ENV_VARS = ("CORTEX_API_KEY", "CORTEX_SERVER_API_KEY")


class SecurityConfigurationError(RuntimeError):
    """Raised when a security-critical runtime dependency is misconfigured."""


def get_runtime_env(
    config: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve the effective runtime environment for security checks."""
    env = environ or os.environ
    if env.get("CORTEX_ENV"):
        return env["CORTEX_ENV"].strip().lower()
    if config:
        server = config.get("server", {})
        configured_env = str(server.get("env") or "").strip().lower()
        if configured_env:
            return configured_env
    return "development"


def resolve_api_key(
    config: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve the API key, preferring environment variables over config files."""
    env = environ or os.environ
    for env_var in API_KEY_ENV_VARS:
        secret = env.get(env_var, "").strip()
        if secret:
            return secret

    configured = ""
    if config:
        server = config.get("server", {})
        configured = str(server.get("api_key") or "").strip()

    runtime_env = get_runtime_env(config, env)
    if runtime_env == "production":
        raise SecurityConfigurationError(
            "CORTEX_API_KEY is required in production; config.yaml API keys are disabled."
        )

    if configured and configured not in INSECURE_API_KEY_VALUES:
        return configured

    raise SecurityConfigurationError(
        "No valid API key configured. Set CORTEX_API_KEY before serving authenticated routes."
    )


def resolve_token_store_path(environ: Mapping[str, str] | None = None) -> Path:
    """Resolve the sovereign token store from environment or runtime-only locations."""
    env = environ or os.environ
    for env_var in TOKEN_STORE_ENV_VARS:
        override = env.get(env_var, "").strip()
        if override:
            return Path(override).expanduser()

    runtime_token_file = PROJECT_ROOT / "run" / "tokens.yaml"
    if runtime_token_file.exists():
        return runtime_token_file

    raise SecurityConfigurationError(
        "No MCP token store configured. Set CORTEX_MCP_TOKENS_FILE to a runtime-managed YAML file."
    )


def parse_decimal(value: Any, *, field_name: str) -> Decimal:
    """Parse a positive decimal-like value from YAML or env input."""
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise SecurityConfigurationError(f"{field_name} is not a valid decimal value.") from exc
    return parsed


def dump_yaml_atomically(path: Path, payload: Mapping[str, Any]) -> None:
    """Write YAML to disk atomically to avoid token-store corruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        yaml.safe_dump(dict(payload), handle, sort_keys=True)
        temp_path = Path(handle.name)
    temp_path.replace(path)
