import json
import stat
from pathlib import Path

import pytest

import cortex.extensions.daemon.utils as daemon_utils
import cortex.extensions.security.honeypot as honeypot_module
from cortex.extensions.security.threat_feed import ThreatFeedEngine
import cortex.extensions.sovereign.infrastructure as infrastructure_module


def test_get_gmail_credentials_refresh_writes_token_atomically(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    google_credentials = pytest.importorskip("google.oauth2.credentials")
    google_requests = pytest.importorskip("google.auth.transport.requests")

    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(daemon_utils, "TOKEN_PATH", token_path)

    class DummyCreds:
        expired = True
        refresh_token = "refresh-token"

        def refresh(self, request) -> None:
            self.refreshed = True

        def to_json(self) -> str:
            return '{"access":"token"}'

    dummy_creds = DummyCreds()

    monkeypatch.setattr(
        google_credentials.Credentials,
        "from_authorized_user_file",
        staticmethod(lambda path, scopes: dummy_creds),
    )
    monkeypatch.setattr(google_requests, "Request", lambda: object())

    creds = daemon_utils.get_gmail_credentials()

    assert creds is dummy_creds
    assert json.loads(token_path.read_text(encoding="utf-8")) == {"access": "token"}
    assert stat.S_IMODE(token_path.stat().st_mode) == 0o600


def test_hardware_vault_persists_shadow_map_with_restricted_permissions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(infrastructure_module, "SOVEREIGN_STORAGE", tmp_path)
    vault = infrastructure_module.HardwareVault("test_vault")

    vault.persist_shadow_map({"alpha": "beta"})

    data = json.loads((tmp_path / "test_vault_keys.json").read_text(encoding="utf-8"))
    assert data == {"alpha": "beta"}
    assert stat.S_IMODE((tmp_path / "test_vault_keys.json").stat().st_mode) == 0o600


def test_honeypot_manager_saves_storage_with_restricted_permissions(tmp_path: Path) -> None:
    storage_path = tmp_path / "security_honeypots.json"
    manager = honeypot_module.HoneypotManager(storage_path=str(storage_path))

    decoy = manager.generate_decoy("demo")

    stored = json.loads(storage_path.read_text(encoding="utf-8"))
    assert stored[0]["id"] == decoy.id
    assert stored[0]["project"] == "demo"
    assert stat.S_IMODE(storage_path.stat().st_mode) == 0o600


def test_threat_feed_engine_saves_feed_atomically_with_permissions(tmp_path: Path) -> None:
    engine = ThreatFeedEngine(data_dir=str(tmp_path), hmac_key="k")
    engine._custom_signatures = [
        {
            "id": "sig-1",
            "pattern": "attack",
            "category": "prompt_injection",
            "severity": "high",
            "description": "demo",
        }
    ]

    engine._save_custom_signatures()

    feed_path = tmp_path / "threat_intel.json"
    payload = json.loads(feed_path.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["signatures"][0]["id"] == "sig-1"
    assert stat.S_IMODE(feed_path.stat().st_mode) == 0o600
