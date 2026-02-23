import json
import logging
from typing import Any, Final

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cortex.auth import AuthResult, require_permission

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

__all__ = ["router", "TranslateRequest", "TranslateResponse", "translate_texts"]

router = APIRouter(prefix="/v1/translate", tags=["translate"])
logger = logging.getLogger("uvicorn.error")

MAX_TEXTS_PER_REQUEST: Final[int] = 100
MODEL_NAME: Final[str] = "gemini-2.0-flash"


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


def _get_genai_client() -> Any:
    """Initialize and return the Gemini 2.0 client securely."""
    if genai is None:
        raise HTTPException(status_code=500, detail="google-genai package is not installed.")

    try:
        return genai.Client()
    except (ValueError, OSError, RuntimeError) as e:
        logger.error("Failed to initialize Gemini Client: %s", e)
        raise HTTPException(status_code=500, detail="LLM configuration error.") from e


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

    try:
        translated_data = json.loads(text_output)
    except json.JSONDecodeError as e:
        logger.error("JSON Decode Error: %s. Output: %s", e, text_output)
        raise ValueError("Invalid JSON format from LLM.") from e

    formatted_translations: dict[str, dict[str, str]] = {}
    for lang in target_languages:
        if lang in translated_data:
            formatted_translations[lang] = translated_data[lang]
        else:
            logger.warning("Language %s missing from LLM response. Filling with empty dict.", lang)
            formatted_translations[lang] = {}

    return formatted_translations


def _extract_usage(response) -> dict[str, int]:
    """Helper to safely extract usage metadata if available."""
    if not response.usage_metadata:
        return {}

    return {
        "prompt_tokens": response.usage_metadata.prompt_token_count,
        "candidates_tokens": response.usage_metadata.candidates_token_count,
        "total_tokens": response.usage_metadata.total_token_count,
    }


def _execute_translation(request: TranslateRequest, client: Any) -> TranslateResponse:
    """Core translation execute logic isolated from router wrapper."""
    system_instruction = _build_system_instruction(request.context)
    prompt = f"Target languages: {request.target_languages}\n\nTexts to translate:\n{json.dumps(request.texts, ensure_ascii=False, indent=2)}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,  # Low temp for high determinism
            response_mime_type="application/json",
        ),
    )

    formatted_translations = _parse_llm_response(response.text, request.target_languages)
    usage_metadata = _extract_usage(response)

    return TranslateResponse(translations=formatted_translations, usage=usage_metadata)


@router.post("", response_model=TranslateResponse)
def translate_texts(
    request: TranslateRequest,
    auth: AuthResult = Depends(require_permission("read")),
) -> TranslateResponse:
    """
    OMNI-TRANSLATE: Sovereign Core translation endpoint.

    Translates a dictionary of texts into multiple target languages simultaneously
    using Gemini 2.0 Flash for optimal speed and cost.
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

    client = _get_genai_client()

    try:
        return _execute_translation(request, client)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except (RuntimeError, OSError) as e:
        logger.error("Translation generation failed critically: %s", e)
        raise HTTPException(status_code=502, detail=f"Translation generation failed: {e}") from e
