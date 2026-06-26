# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import os
from typing import Any

from cortex_extensions.llm._models import IntentProfile
from cortex_extensions.llm._presets import check_api_key


def resolve_provider_config(
    provider: str,
    presets: dict[str, Any],
    api_key: str | None,
    model: str | None,
    base_url: str | None,
) -> dict[str, Any]:
    if provider == "custom":
        return _resolve_custom(api_key, model, base_url)
    if provider in presets:
        return _resolve_preset(provider, presets[provider], api_key, model, base_url)
    supported = sorted(list(presets.keys()) + ["custom"])
    raise ValueError(f"Unknown LLM provider '{provider}'. Supported: {supported}")


def _resolve_custom(api_key: str | None, model: str | None, base_url: str | None) -> dict[str, Any]:
    base_url = base_url or os.environ.get("CORTEX_LLM_BASE_URL")
    if not base_url:
        raise ValueError("Custom LLM provider requires CORTEX_LLM_BASE_URL")
    return {
        "provider": "custom",
        "base_url": base_url,
        "model": model or os.environ.get("CORTEX_LLM_MODEL", "gpt-4"),
        "api_key": api_key or os.environ.get("CORTEX_LLM_API_KEY"),
        "context_window": 128000,
        "extra_headers": {},
        "intent_affinity": frozenset({IntentProfile.GENERAL}),
        "intent_model_map": {},
        "tier": "high",
        "cost_class": "medium",
    }


def _resolve_preset(
    provider: str,
    preset: dict[str, Any],
    api_key: str | None,
    model: str | None,
    base_url: str | None,
) -> dict[str, Any]:
    _TAG_MAP = {
        "code": IntentProfile.CODE,
        "reasoning": IntentProfile.REASONING,
        "creative": IntentProfile.CREATIVE,
        "architect": IntentProfile.ARCHITECT,
        "general": IntentProfile.GENERAL,
    }
    raw_specs = preset.get("specialization", ["general"])
    intent_affinity = frozenset(_TAG_MAP[t] for t in raw_specs if t in _TAG_MAP) or frozenset(
        {IntentProfile.GENERAL}
    )
    raw_map = preset.get("intent_model_map", {})
    intent_model_map = {_TAG_MAP[tag]: mid for tag, mid in raw_map.items() if tag in _TAG_MAP}

    resolved_api_key = api_key
    env_key = preset.get("env_key") or preset.get("api_key_env")
    if not resolved_api_key and env_key:
        resolved_api_key = check_api_key(preset)

    if not resolved_api_key and provider not in ["ollama", "lmstudio", "llamacpp", "vllm", "jan"]:
        raise ValueError(f"Provider '{provider}' requires API key ({env_key})")

    return {
        "provider": provider,
        "base_url": base_url or preset["base_url"],
        "model": model or os.environ.get("CORTEX_LLM_MODEL") or preset["default_model"],
        "context_window": preset.get("context_window", 128000),
        "extra_headers": preset.get("extra_headers", {}),
        "api_key": resolved_api_key,
        "tier": preset.get("tier", "high"),
        "cost_class": preset.get("cost_class", "medium"),
        "intent_affinity": intent_affinity,
        "intent_model_map": intent_model_map,
    }
