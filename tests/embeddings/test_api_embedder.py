"""Tests for CORTEX API Embedder — Gemini Embedding 2 Multimodal."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cortex.embeddings.api_embedder import (
    PROVIDER_CONFIGS,
    SUPPORTED_IMAGE_MIMES,
    APIEmbedder,
)

# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def gemini_key_env(monkeypatch):
    """Set up GEMINI_API_KEY."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")


@pytest.fixture
def openai_key_env(monkeypatch):
    """Set up OPENAI_API_KEY."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-456")


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("POST", "https://test.example.com"),
    )


def _embedding_response(values: list[float]) -> dict:
    """Standard Gemini embedding response shape."""
    return {"embedding": {"values": values}}


# ─── Provider Config Tests ────────────────────────────────────────────


class TestProviderConfigs:
    def test_gemini_v2_exists(self):
        assert "gemini-v2" in PROVIDER_CONFIGS

    def test_gemini_v2_multimodal(self):
        cfg = PROVIDER_CONFIGS["gemini-v2"]
        assert cfg["supports_multimodal"] is True
        assert cfg["supports_mrl"] is True
        assert cfg["native_dimension"] == 3072

    def test_gemini_v1_no_multimodal(self):
        cfg = PROVIDER_CONFIGS["gemini"]
        assert cfg["supports_multimodal"] is False
        assert cfg["supports_mrl"] is False
        assert cfg["native_dimension"] == 768

    def test_openai_no_multimodal(self):
        cfg = PROVIDER_CONFIGS["openai"]
        assert cfg["supports_multimodal"] is False

    def test_mrl_dimensions_list(self):
        cfg = PROVIDER_CONFIGS["gemini-v2"]
        assert 768 in cfg["mrl_dimensions"]
        assert 1536 in cfg["mrl_dimensions"]
        assert 3072 in cfg["mrl_dimensions"]


# ─── Constructor Tests ────────────────────────────────────────────────


class TestAPIEmbedderInit:
    def test_unknown_provider_raises(self, gemini_key_env):
        with pytest.raises(ValueError, match="Unknown provider"):
            APIEmbedder(provider="nonexistent")

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
            APIEmbedder(provider="gemini")

    def test_default_provider(self, gemini_key_env):
        e = APIEmbedder()
        assert e.provider == "gemini"
        assert e.dimension == 768

    def test_gemini_v2_provider(self, gemini_key_env):
        e = APIEmbedder(provider="gemini-v2", target_dimension=768)
        assert e.provider == "gemini-v2"
        assert e.supports_multimodal is True
        assert e.supports_mrl is True
        assert e.native_dimension == 3072
        assert e.dimension == 768

    def test_custom_task_type(self, gemini_key_env):
        e = APIEmbedder(task_type="SEMANTIC_SIMILARITY")
        assert e.task_type == "SEMANTIC_SIMILARITY"


# ─── Text Embedding Tests ────────────────────────────────────────────


class TestTextEmbed:
    @pytest.mark.asyncio
    async def test_embed_gemini_text(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini", target_dimension=768)
        fake_values = [0.1] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed("test text")

        assert len(result) == 768
        assert result == fake_values
        # Verify taskType is sent
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["taskType"] == "RETRIEVAL_DOCUMENT"

    @pytest.mark.asyncio
    async def test_embed_gemini_v2_with_mrl(self, gemini_key_env):
        """gemini-v2 should send outputDimensionality when target < native."""
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        fake_values = [0.2] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed("MRL test")

        assert len(result) == 768
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["outputDimensionality"] == 768

    @pytest.mark.asyncio
    async def test_embed_gemini_v2_full_dimension(self, gemini_key_env):
        """gemini-v2 at native 3072 should NOT send outputDimensionality."""
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=3072)
        fake_values = [0.3] * 3072
        mock_resp = _mock_response(_embedding_response(fake_values))

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed("full dim test")

        assert len(result) == 3072
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "outputDimensionality" not in payload

    @pytest.mark.asyncio
    async def test_embed_empty_raises(self, gemini_key_env):
        embedder = APIEmbedder()
        with pytest.raises(ValueError, match="text cannot be empty"):
            await embedder.embed("")

    @pytest.mark.asyncio
    async def test_embed_batch_gemini(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini", target_dimension=768)
        fake_values = [0.1] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed_batch(["text1", "text2"])

        assert len(result) == 2
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_embed_batch_empty(self, gemini_key_env):
        embedder = APIEmbedder()
        result = await embedder.embed_batch([])
        assert result == []


# ─── Multimodal Embedding Tests ───────────────────────────────────────


class TestMultimodalEmbed:
    @pytest.mark.asyncio
    async def test_multimodal_text_only(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        fake_values = [0.5] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed_multimodal([{"text": "multimodal text"}])

        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_multimodal_image(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        fake_values = [0.6] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))
        fake_img = b"\x89PNG\r\n" + b"\x00" * 100

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed_multimodal(
                [
                    {"text": "a cat"},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(fake_img).decode(),
                        }
                    },
                ]
            )

        assert len(result) == 768
        # Verify the payload structure
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        parts = payload["content"]["parts"]
        assert len(parts) == 2
        assert "text" in parts[0]
        assert "inline_data" in parts[1]

    @pytest.mark.asyncio
    async def test_multimodal_with_task_type_override(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        fake_values = [0.7] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            await embedder.embed_multimodal(
                [{"text": "query"}],
                task_type="RETRIEVAL_QUERY",
            )

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["taskType"] == "RETRIEVAL_QUERY"

    @pytest.mark.asyncio
    async def test_multimodal_gemini_v1_raises(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini", target_dimension=768)
        with pytest.raises(ValueError, match="does not support multimodal"):
            await embedder.embed_multimodal([{"text": "nope"}])

    @pytest.mark.asyncio
    async def test_multimodal_empty_parts_raises(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        with pytest.raises(ValueError, match="parts list cannot be empty"):
            await embedder.embed_multimodal([])


# ─── Convenience Method Tests ─────────────────────────────────────────


class TestConvenienceMethods:
    @pytest.mark.asyncio
    async def test_embed_image(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        fake_values = [0.8] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))
        fake_img = b"\xff\xd8\xff" + b"\x00" * 100  # JPEG header

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed_image(fake_img, mime_type="image/jpeg")

        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_embed_image_bad_mime(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        with pytest.raises(ValueError, match="Unsupported image MIME type"):
            await embedder.embed_image(b"data", mime_type="image/bmp")

    @pytest.mark.asyncio
    async def test_embed_document_text_only(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        fake_values = [0.9] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed_document("document text")

        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_embed_document_with_images(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        fake_values = [0.95] * 768
        mock_resp = _mock_response(_embedding_response(fake_values))
        fake_img = b"\x89PNG" + b"\x00" * 50

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await embedder.embed_document(
                "doc with image",
                images=[(fake_img, "image/png")],
            )

        assert len(result) == 768
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        parts = payload["content"]["parts"]
        assert len(parts) == 2  # text + image

    @pytest.mark.asyncio
    async def test_embed_document_bad_image_mime(self, gemini_key_env):
        embedder = APIEmbedder(provider="gemini-v2", target_dimension=768)
        with pytest.raises(ValueError, match="Unsupported image MIME type"):
            await embedder.embed_document(
                "text",
                images=[(b"data", "image/tiff")],
            )


# ─── Properties Tests ────────────────────────────────────────────────


class TestProperties:
    def test_repr_gemini(self, gemini_key_env):
        e = APIEmbedder(provider="gemini")
        assert "gemini" in repr(e)
        assert "multimodal" not in repr(e)

    def test_repr_gemini_v2(self, gemini_key_env):
        e = APIEmbedder(provider="gemini-v2")
        assert "gemini-v2" in repr(e)
        assert "multimodal=True" in repr(e)
        assert "mrl=True" in repr(e)

    def test_supported_image_mimes(self):
        assert "image/png" in SUPPORTED_IMAGE_MIMES
        assert "image/jpeg" in SUPPORTED_IMAGE_MIMES
        assert "image/webp" in SUPPORTED_IMAGE_MIMES
