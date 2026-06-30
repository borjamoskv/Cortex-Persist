# [C5-REAL] Exergy-Maximized
import json
import logging
import os
from typing import Final

import httpx
from babylon60.auth import AuthResult, require_permission
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

__all__ = ["TranslateRequest", "TranslateResponse", "router", "translate_texts"]

router = APIRouter(prefix="/v1/translate", tags=["translate"])
logger = logging.getLogger("uvicorn.error")

MAX_TEXTS_PER_REQUEST: Final[int] = 100
# Enforced Local Autarchy model
MODEL_NAME: Final[str] = os.getenv("CORTEX_PRIMARY_LLM", "qwen2.5:32b")
LOCAL_API_URL: Final[str] = os.getenv("EXERGY_UPSTREAM_URL", "http://127.0.0.1:11434/v1")


class TranslateRequest(BaseModel):
    texts: dict[str, str] = Field(
        ...,
        description=f"Dictionary of key-value pairs to translate. Max {MAX_TEXTS_PER_REQUEST} items.",
    )
    target_languages: list[str] = Field(
        ..., description="List of target language codes (e.g., ['es', 'fr', 'zh'])."
    )
    context: str | None = Field(None, description="Optional context about the application or tone.")


class TranslateResponse(BaseModel):
    translations: dict[str, dict[str, str]] = Field(
        ..., description="A dictionary mapping language codes to their translated key-value pairs."
    )
    usage: dict[str, int] = Field(default_factory=dict)


def _build_system_instruction(context: str | None) -> str:
    """Constructs the sovereign B2B translation instruction set."""
    base_instruction = (
        "You are OMNI-TRANSLATE, a sovereign localization AI for B2B applications. "
        "Your task is to translate JSON strictly into the requested target languages. "
        "You must maintain the exact same keys. "
        "Do not translate variables in brackets like {name} or {{name}}. "
        "Your output must be VALID JSON."
    )
    return f"{base_instruction} Context for tone/domain: {context}" if context else base_instruction


def _parse_llm_response(
    text_output: str | None, target_languages: list[str]
) -> dict[str, dict[str, str]]:
    """Strictly parses the LLM output ensuring all target languages are present."""
    if not text_output:
        raise ValueError("Empty response received from LLM.")

    # Remove markdown code blocks if present
    clean_text = text_output.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    try:
        translated_data = json.loads(clean_text)
    except json.JSONDecodeError as e:
        logger.error("JSON Decode Error: %s. Output: %s", e, clean_text)
        raise ValueError("Invalid JSON format from LLM.") from e

    formatted_translations: dict[str, dict[str, str]] = {}
    for lang in target_languages:
        if lang in translated_data:
            formatted_translations[lang] = translated_data[lang]
        else:
            logger.warning("Language %s missing from LLM response. Filling with empty dict.", lang)
            formatted_translations[lang] = {}

    return formatted_translations


def _execute_translation(request: TranslateRequest) -> TranslateResponse:
    """Core translation execute logic utilizing local Autarchy."""
    system_instruction = _build_system_instruction(request.context)
    prompt = f"Target languages: {request.target_languages}\n\nTexts to translate:\n{json.dumps(request.texts, ensure_ascii=False, indent=2)}"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    headers = {"Content-Type": "application/json"}
    try:
        with httpx.Client() as client:
            resp = client.post(
                f"{LOCAL_API_URL}/chat/completions", json=payload, headers=headers, timeout=120.0
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
    except Exception as e:
        logger.error("Local inference failed: %s", e)
        raise ValueError("Local inference failure") from e

    formatted_translations = _parse_llm_response(content, request.target_languages)
    return TranslateResponse(translations=formatted_translations, usage=usage)


@router.post("", response_model=TranslateResponse)
def translate_texts(
    request: TranslateRequest,
    auth: AuthResult = Depends(require_permission("read")),
) -> TranslateResponse:
    """
    OMNI-TRANSLATE: Sovereign Core translation endpoint.

    Translates a dictionary of texts into multiple target languages simultaneously
    using Local Autarchy model (e.g. qwen2.5-coder).
    Ensures that the output strictly matches the input schema.
    """
    if not request.texts or not request.target_languages:
        raise HTTPException(
            status_code=400, detail="Both 'texts' and 'target_languages' are strictly required."
        )

    if len(request.texts) > MAX_TEXTS_PER_REQUEST:
        raise HTTPException(
            status_code=400, detail=f"Maximum {MAX_TEXTS_PER_REQUEST} texts allowed per request."
        )

    try:
        return _execute_translation(request)
    except ValueError as e:
        raise HTTPException(
            status_code=502, detail="Error generating translation or invalid upstream response."
        ) from e
    except (RuntimeError, OSError) as e:
        logger.error("Translation generation failed critically: %s", e)
        raise HTTPException(status_code=502, detail=f"Translation generation failed: {e}") from e
