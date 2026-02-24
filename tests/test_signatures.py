"""Tests for Ed25519 digital signatures."""

from __future__ import annotations

import base64

import pytest

from cortex.security.signatures import (
    Ed25519Signer,
    SignatureVerificationError,
    generate_keypair,
)


class TestGenerateKeypair:
    def test_returns_tuple_of_bytes(self) -> None:
        priv, pub = generate_keypair()
        assert isinstance(priv, bytes)
        assert isinstance(pub, bytes)

    def test_key_lengths(self) -> None:
        priv, pub = generate_keypair()
        assert len(priv) == 32  # Ed25519 private key is 32 bytes
        assert len(pub) == 32   # Ed25519 public key is 32 bytes

    def test_unique_keys(self) -> None:
        k1 = generate_keypair()
        k2 = generate_keypair()
        assert k1[0] != k2[0]
        assert k1[1] != k2[1]


class TestEd25519Signer:
    @pytest.fixture()
    def keypair(self) -> tuple[bytes, bytes]:
        return generate_keypair()

    @pytest.fixture()
    def signer(self, keypair: tuple[bytes, bytes]) -> Ed25519Signer:
        return Ed25519Signer(private_key_bytes=keypair[0])

    @pytest.fixture()
    def verifier(self, keypair: tuple[bytes, bytes]) -> Ed25519Signer:
        return Ed25519Signer(public_key_bytes=keypair[1])

    def test_can_sign_with_private_key(self, signer: Ed25519Signer) -> None:
        assert signer.can_sign is True
        assert signer.can_verify is True

    def test_cannot_sign_with_only_public_key(self, verifier: Ed25519Signer) -> None:
        assert verifier.can_sign is False
        assert verifier.can_verify is True

    def test_sign_and_verify(self, signer: Ed25519Signer) -> None:
        content = "Chose OAuth2 PKCE for auth"
        fact_hash = "abc123def456"
        sig = signer.sign(content, fact_hash)
        assert isinstance(sig, str)
        assert signer.verify(content, fact_hash, sig)

    def test_verify_fails_on_tampered_content(self, signer: Ed25519Signer) -> None:
        content = "Original decision"
        fact_hash = "hash123"
        sig = signer.sign(content, fact_hash)

        with pytest.raises(SignatureVerificationError):
            signer.verify("Tampered decision", fact_hash, sig)

    def test_verify_fails_on_tampered_hash(self, signer: Ed25519Signer) -> None:
        content = "Decision content"
        sig = signer.sign(content, "original_hash")

        with pytest.raises(SignatureVerificationError):
            signer.verify(content, "tampered_hash", sig)

    def test_verify_with_external_public_key(
        self, signer: Ed25519Signer, verifier: Ed25519Signer
    ) -> None:
        content = "Cross-verify test"
        fact_hash = "hash456"
        sig = signer.sign(content, fact_hash)

        assert verifier.verify(content, fact_hash, sig)

    def test_verify_with_explicit_public_key_b64(self, signer: Ed25519Signer) -> None:
        content = "Explicit key test"
        fact_hash = "hash789"
        sig = signer.sign(content, fact_hash)

        pub_b64 = signer.public_key_b64
        assert pub_b64 is not None

        # Create a verifier with no key, pass public key explicitly
        empty = Ed25519Signer()
        assert empty.verify(content, fact_hash, sig, public_key_b64=pub_b64)

    def test_sign_without_private_key_raises(self) -> None:
        signer = Ed25519Signer()
        with pytest.raises(RuntimeError, match="No private key"):
            signer.sign("content", "hash")

    def test_verify_without_any_key_raises(self) -> None:
        signer = Ed25519Signer()
        with pytest.raises(RuntimeError, match="No public key"):
            signer.verify("content", "hash", "fakesig==")

    def test_public_key_b64(self, signer: Ed25519Signer) -> None:
        b64 = signer.public_key_b64
        assert b64 is not None
        raw = base64.b64decode(b64)
        assert len(raw) == 32

    def test_public_key_b64_none_when_no_key(self) -> None:
        signer = Ed25519Signer()
        assert signer.public_key_b64 is None

    def test_to_dict(self, signer: Ed25519Signer) -> None:
        d = signer.to_dict()
        assert d["algorithm"] == "Ed25519"
        assert d["can_sign"] is True
        assert isinstance(d["public_key"], str)

    def test_wrong_key_rejects_signature(self) -> None:
        priv1, _ = generate_keypair()
        _, pub2 = generate_keypair()

        signer = Ed25519Signer(private_key_bytes=priv1)
        verifier = Ed25519Signer(public_key_bytes=pub2)

        sig = signer.sign("Secret decision", "hash")
        with pytest.raises(SignatureVerificationError):
            verifier.verify("Secret decision", "hash", sig)

    def test_signature_deterministic_for_same_input(self, signer: Ed25519Signer) -> None:
        # Ed25519 is deterministic — same input produces same signature
        content = "Deterministic test"
        fact_hash = "det_hash"
        sig1 = signer.sign(content, fact_hash)
        sig2 = signer.sign(content, fact_hash)
        assert sig1 == sig2

    def test_different_inputs_produce_different_signatures(
        self, signer: Ed25519Signer
    ) -> None:
        sig1 = signer.sign("Content A", "hash1")
        sig2 = signer.sign("Content B", "hash2")
        assert sig1 != sig2
