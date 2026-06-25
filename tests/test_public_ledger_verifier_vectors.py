# [C5-REAL] Exergy-Maximized
import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from cortex.utils.canonical import canonical_json, compute_tx_hash

FIXTURES = Path(__file__).parent / "fixtures" / "ledger_verifier"
STRICT = FIXTURES / "public_v1_strict"
MUTATIONS = FIXTURES / "public_v1_strict_mutations"
STRICT_REQUIRED_FIELDS = {
    "schema_version",
    "stream_id",
    "tenant_id",
    "sequence",
    "event_id",
    "nonce",
    "issued_at",
    "recorded_at",
    "actor_id",
    "actor_key_id",
    "action",
    "project",
    "target",
    "detail",
    "prev_hash",
    "hash_alg",
    "hash",
    "signature_alg",
    "origin_signature",
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key: {key}")
        seen.add(key)
        out[key] = value
    return out


def load_json_strict(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def load_jsonl_one(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    value = json.loads(lines[0], object_pairs_hook=_reject_duplicate_keys)
    assert isinstance(value, dict)
    return value


def assert_no_float(value: Any) -> None:
    if isinstance(value, float):
        raise AssertionError("public-v1 fixtures must not contain floats")
    if isinstance(value, dict):
        for child in value.values():
            assert_no_float(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_float(child)


def public_canonical_json(value: Any) -> str:
    assert_no_float(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def event_hash(event: dict[str, Any]) -> str:
    scope = dict(event)
    scope.pop("hash", None)
    scope.pop("origin_signature", None)
    return sha256_bytes(public_canonical_json(scope).encode("utf-8"))


def key_by_id(registry: dict[str, Any], key_id: str) -> dict[str, Any]:
    for key in registry["keys"]:
        if key["key_id"] == key_id:
            return key
    raise AssertionError(f"missing key {key_id}")


def verify_signature(payload: bytes, signature_b64url: str, public_key_b64url: str) -> None:
    public_key = Ed25519PublicKey.from_public_bytes(b64url_decode(public_key_b64url))
    public_key.verify(b64url_decode(signature_b64url), payload)


def event_signature_scope(event: dict[str, Any]) -> bytes:
    scope = dict(event)
    scope.pop("origin_signature")
    return public_canonical_json(scope).encode("utf-8")


def manifest_signature_scope(manifest: dict[str, Any]) -> bytes:
    scope = dict(manifest)
    scope.pop("signature")
    return public_canonical_json(scope).encode("utf-8")


def merkle_root_v1(event_hashes: list[str]) -> str:
    nodes = [
        sha256_bytes(("CORTEX-MERKLE-LEAF-v1:" + event_hash_hex).encode("utf-8"))
        for event_hash_hex in event_hashes
    ]
    if not nodes:
        return sha256_bytes(b"CORTEX-MERKLE-EMPTY-v1")

    while len(nodes) > 1:
        next_nodes: list[str] = []
        for index in range(0, len(nodes), 2):
            left = nodes[index]
            right = nodes[index + 1] if index + 1 < len(nodes) else None
            if right is None:
                next_nodes.append(left)
            else:
                payload = "CORTEX-MERKLE-NODE-v1:" + left + right
                next_nodes.append(sha256_bytes(payload.encode("utf-8")))
        nodes = next_nodes

    return nodes[0]


@pytest.mark.parametrize(
    "fixture_name",
    ["legacy_v0_vector_1.json", "legacy_v0_vector_2.json"],
)
def test_legacy_v0_vectors_match_current_compute_tx_hash(fixture_name: str) -> None:
    vector = load_json_strict(FIXTURES / fixture_name)
    detail_json = canonical_json(vector["detail"])
    actual = compute_tx_hash(
        vector["prev_hash"],
        vector["project"],
        vector["action"],
        detail_json,
        vector["timestamp"],
    )
    assert actual == vector["expected_hash"]


def test_public_v1_strict_event_hash_matches_fixture() -> None:
    event = load_jsonl_one(STRICT / "events.jsonl")
    assert event.keys() >= STRICT_REQUIRED_FIELDS
    assert event_hash(event) == event["hash"]
    assert event["hash"] == "518375b3ebdb916e0a779eb2baa6c9fcfbe4ae246a18eda9b4dfad0f32d2d59b"


def test_public_v1_strict_origin_signature_verifies() -> None:
    event = load_jsonl_one(STRICT / "events.jsonl")
    registry = load_json_strict(STRICT / "public-keys.json")
    key = key_by_id(registry, event["actor_key_id"])

    assert event["actor_id"] == key["actor_id"]
    assert event["action"] in key["permissions"]
    verify_signature(event_signature_scope(event), event["origin_signature"], key["public_key"])


def test_public_v1_strict_manifest_signature_verifies() -> None:
    manifest = load_json_strict(STRICT / "manifest.json")
    registry = load_json_strict(STRICT / "public-keys.json")
    signature = manifest["signature"]
    key = key_by_id(registry, signature["key_id"])

    assert "ledger.export" in key["permissions"]
    verify_signature(manifest_signature_scope(manifest), signature["value"], key["public_key"])


def test_public_v1_strict_manifest_file_hashes_match() -> None:
    manifest = load_json_strict(STRICT / "manifest.json")
    hashes = manifest["hashes"]

    assert sha256_file(STRICT / "events.jsonl") == hashes["events_file_sha256"]
    assert sha256_file(STRICT / "schema.json") == hashes["schema_file_sha256"]
    assert sha256_file(STRICT / "public-keys.json") == hashes["public_keys_file_sha256"]
    assert sha256_file(STRICT / "key-events.jsonl") == hashes["key_events_file_sha256"]
    assert (
        sha256_file(STRICT / "verification-profile.json") == hashes["verification_profile_sha256"]
    )


def test_public_v1_strict_merkle_root_matches() -> None:
    event = load_jsonl_one(STRICT / "events.jsonl")
    manifest = load_json_strict(STRICT / "manifest.json")

    assert merkle_root_v1([event["hash"]]) == manifest["hashes"]["merkle_root"]


def test_public_v1_strict_expected_report_keeps_truth_and_online_freshness_false() -> None:
    expected = load_json_strict(STRICT / "expected-report.json")

    assert expected["result"] == "VALID_FULL_STRICT"
    assert expected["guarantees"]["truth_verified"] is False
    assert expected["guarantees"]["online_freshness_verified"] is False
    assert expected["guarantees"]["completeness_verified"] is True


def test_missing_nonce_fixture_is_invalid_strict_schema() -> None:
    event = load_jsonl_one(MUTATIONS / "missing_nonce" / "events.jsonl")

    assert "nonce" not in event
    assert not event.keys() >= STRICT_REQUIRED_FIELDS


def test_tampered_detail_changes_event_hash() -> None:
    event = load_jsonl_one(MUTATIONS / "tampered_detail" / "events.jsonl")

    assert event_hash(event) != event["hash"]


def test_missing_manifest_expected_result_is_not_full_strict() -> None:
    expected = load_json_strict(MUTATIONS / "missing_manifest" / "expected-report.json")

    assert expected["result"] == "VALID_WITH_LIMITATIONS"
    assert expected["guarantees"]["completeness_verified"] is False
    assert expected["guarantees"]["truth_verified"] is False


def test_bad_manifest_signature_fixture_does_not_verify() -> None:
    manifest = load_json_strict(MUTATIONS / "bad_manifest_signature" / "manifest.json")
    registry = load_json_strict(STRICT / "public-keys.json")
    signature = manifest["signature"]
    key = key_by_id(registry, signature["key_id"])

    with pytest.raises(InvalidSignature):
        verify_signature(manifest_signature_scope(manifest), signature["value"], key["public_key"])


def test_fixtures_do_not_contain_private_key_material() -> None:
    forbidden = ["private_key", "seed_hex", "BEGIN PRIVATE KEY"]
    for path in FIXTURES.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert not any(token in text for token in forbidden), path
