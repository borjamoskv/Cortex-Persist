import importlib.util
import json
from pathlib import Path


def _load_module(module_name: str, file_name: str):
    module_path = Path(__file__).resolve().parents[1] / "engine-c5" / file_name
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cortex_chaos_stellar_updates_ledger(tmp_path: Path) -> None:
    module = _load_module("cortex_chaos_stellar_module", "cortex_chaos_stellar.py")
    module.LEDGER_PATH = str(tmp_path / "vanguard_ledger.json")

    module.update_ledger("fracture detected")

    data = json.loads(Path(module.LEDGER_PATH).read_text(encoding="utf-8"))
    assert data["stellar_endpoint_v2"]["status"] == "FRACTURED"
    assert data["stellar_endpoint_v2"]["details"] == "fracture detected"


def test_cortex_bounty_radar_persists_bounties(tmp_path: Path) -> None:
    module = _load_module("cortex_bounty_radar_module", "cortex_bounty_radar.py")
    output_path = tmp_path / "active_bounties.json"
    bounties = [{"title": "demo", "labels": ["bounty"], "url": "https://example.com"}]

    module.persist_bounties(bounties, str(output_path))

    assert json.loads(output_path.read_text(encoding="utf-8")) == bounties


def test_moskv_10k_crystallize_ledger_persists_results(monkeypatch, tmp_path: Path) -> None:
    module = _load_module("moskv_10k_swarm_module", "moskv_10k_swarm.py")
    output_path = tmp_path / "mev_rpc_routing.json"
    monkeypatch.setattr(module.os.path, "expanduser", lambda _: str(output_path))
    results = [{"name": "Ethereum-Cloudflare", "best_rtt": 12.5, "winning_agent": 42}]

    module.crystallize_ledger(results)

    assert json.loads(output_path.read_text(encoding="utf-8")) == results
