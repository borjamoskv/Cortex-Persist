import pytest
import time
from legacy_research.reality.rul import RealityClaim, Source, submit_claim


def now_ms():
    return int(time.time() * 1000)


class TestRealityUpdateLayer:

    def test_sourceless_claim_is_rejected(self):
        """
        Lo que hice en mi respuesta anterior:
        afirmar capacidades de Gemini 3.5 sin fuente.
        Resultado esperado: rejected.
        """
        claim = RealityClaim(
            statement="Gemini 3.5 Flash tiene regulador epistémico nativo",
            domain="llm",
            sources=[],  # sin fuente → rechazado
        )
        status = submit_claim(claim)
        assert status == "rejected"

    def test_official_source_is_verified(self):
        claim = RealityClaim(
            statement="Gemini API disponible en ai.google.dev",
            domain="llm",
            sources=[
                Source(
                    url="https://ai.google.dev/gemini-api/docs",
                    fetch_hash="sha256:abc123",
                    fetched_at_epoch_ms=now_ms(),
                )
            ],
        )
        status = submit_claim(claim)
        assert status == "verified"

    def test_weak_source_is_rejected(self):
        claim = RealityClaim(
            statement="Gemini 3.5 es mejor según Reddit",
            domain="llm",
            sources=[
                Source(
                    url="https://reddit.com/r/MachineLearning/...",
                    fetch_hash="sha256:def456",
                    fetched_at_epoch_ms=now_ms(),
                )
            ],
        )
        status = submit_claim(claim)
        # reddit score = 0.20 < minimum 0.60 → rejected
        assert status == "rejected"

    def test_multi_source_boosts_trust(self):
        claim = RealityClaim(
            statement="Gemini context window documentado",
            domain="llm",
            sources=[
                Source(
                    url="https://ai.google.dev/gemini-api/docs/models",
                    fetch_hash="sha256:aaa",
                    fetched_at_epoch_ms=now_ms(),
                ),
                Source(
                    url="https://cloud.google.com/vertex-ai/docs",
                    fetch_hash="sha256:bbb",
                    fetched_at_epoch_ms=now_ms(),
                ),
            ],
        )
        status = submit_claim(claim)
        assert status == "verified"
