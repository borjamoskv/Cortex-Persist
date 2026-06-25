from __future__ import annotations

import ast
import json
from dataclasses import asdict, is_dataclass
from typing import Any

from legacy_research.types.evidence import ClosurePayload


class ClosureContractError(RuntimeError):
    pass


class CausalClosureGuard:
    """
    Strict verifier for sealed causal payloads.

    Rules:
    - token_cost is ignored completely.
    - narrative text is rejected.
    - canonical payloads are required.
    - legacy structured input is only accepted if it can be normalized into
      the canonical schema.
    """

    EXPECTED_SCHEMA_VERSION = "v1"
    ALLOWED_PROOF_KINDS = {
        "sealed-claim-set",
        "ast-proof",
        "hash-chain",
        "zk-proof",
    }

    def verify_closure(self, proposal: Any) -> bool:
        payload = self._normalize_input(proposal)
        self._validate_payload(payload)
        return True

    def _normalize_input(self, proposal: Any) -> dict[str, Any]:
        # Preferred path: already sealed.
        if type(proposal).__name__ == "ClosurePayload":
            return proposal.canonical()

        # Dataclass wrapper support.
        if is_dataclass(proposal):
            proposal = asdict(proposal) # type: ignore

        # Proposal-like object with content field.
        if hasattr(proposal, "content"):
            proposal = proposal.content

        # Raw string content.
        if isinstance(proposal, str):
            parsed = self._parse_text_payload(proposal)
            if parsed is None:
                raise ClosureContractError("closure payload is narrative or unparseable")
            return parsed

        # Dict-like structured payload.
        if isinstance(proposal, dict):
            return proposal

        raise ClosureContractError(f"unsupported closure input type: {type(proposal).__name__}")

    def _parse_text_payload(self, text: str) -> dict[str, Any] | None:
        stripped = text.strip()
        if not stripped:
            return None

        # Strict JSON first.
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None

        if parsed is None:
            # Safe fallback for legacy Python literal payloads.
            try:
                parsed = ast.literal_eval(stripped)
            except (ValueError, SyntaxError):
                return None

        if not isinstance(parsed, dict):
            return None

        return parsed

    def _validate_payload(self, payload: dict[str, Any]) -> None:
        required = {"schema_version", "proof_kind", "claims", "evidence_hash", "verdict"}
        missing = required - payload.keys()
        if missing:
            raise ClosureContractError(f"missing required fields: {sorted(missing)}")

        if payload["schema_version"] != self.EXPECTED_SCHEMA_VERSION:
            raise ClosureContractError(
                f"unsupported schema_version: {payload['schema_version']!r}"
            )

        if payload["proof_kind"] not in self.ALLOWED_PROOF_KINDS:
            raise ClosureContractError(
                f"unsupported proof_kind: {payload['proof_kind']!r}"
            )

        if not isinstance(payload["claims"], list) or not payload["claims"]:
            raise ClosureContractError("claims must be a non-empty list")

        if not isinstance(payload["evidence_hash"], str) or len(payload["evidence_hash"]) != 64:
            raise ClosureContractError("evidence_hash must be a 64-char SHA3-256 hex digest")

        if not isinstance(payload["verdict"], bool):
            raise ClosureContractError("verdict must be boolean")

        # Recompute canonical payload hash if present.
        canonical = {
            "schema_version": payload["schema_version"],
            "proof_kind": payload["proof_kind"],
            "claims": payload["claims"],
            "evidence_hash": payload["evidence_hash"],
            "verdict": payload["verdict"],
        }
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

        import hashlib
        expected_payload_hash = hashlib.sha3_256(encoded).hexdigest()

        if "payload_hash" in payload and payload["payload_hash"] != expected_payload_hash:
            raise ClosureContractError("payload_hash mismatch")

        # No token_cost gate. No heuristics. No vibes.
        return
