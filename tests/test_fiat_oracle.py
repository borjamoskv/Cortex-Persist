"""
Tests for Zero-Trust FiatOracle.
"""

import json
import logging
from pathlib import Path

import pytest

from cortex.daemon.sidecar.telemetry.fiat_oracle import FiatOracle

# We configure an isolated queue path for tests
TEST_QUEUE_DIR = Path("/tmp/cortex_test_fiat_queue")

class MockEngine:
    """Simulates CORTEX engine."""
    def __init__(self):
        self.stored_facts = []

    async def store(self, project, content, fact_type, meta):
        self.stored_facts.append(
            {"project": project, "content": content, "type": fact_type, "meta": meta}
        )

@pytest.fixture
def test_dir():
    TEST_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    yield TEST_QUEUE_DIR
    for f in TEST_QUEUE_DIR.glob("*.json"):
        f.unlink()
    TEST_QUEUE_DIR.rmdir()

@pytest.fixture
def oracle(test_dir):
    engine = MockEngine()
    # We patch the oracle queue property to use the test dir
    oracle_instance = FiatOracle(engine=engine, interval=0.1)
    oracle_instance.queue_dir = test_dir
    return oracle_instance

@pytest.mark.asyncio
class TestFiatOracle:
    async def test_invalid_signature_discarded(self, oracle, test_dir):
        """Test spoofed file is rejected."""
        fake_payload = {
            "tx_id": "spoof_1",
            "amount": "1000",
            "currency": "EUR",
            "source": "BUNQ",
            "signature": "invalid_sig", # Fails zero-trust check
        }
        test_file = test_dir / "tx_spoof.json"
        test_file.write_text(json.dumps(fake_payload))

        await oracle._check_signals()

        assert len(oracle.engine.stored_facts) == 0
        assert not test_file.exists() # The file should be discarded (quarantined/deleted)

    async def test_valid_transaction_processed(self, oracle, test_dir):
        """Test legitimate transaction is processed and stored."""
        payload_str = json.dumps({
            "tx_id": "valid_1",
            "amount": "99",
            "currency": "EUR",
            "source": "BUNQ"
        })
        import hashlib
        valid_sig = hashlib.sha256((payload_str + "SOVEREIGN_KEY_MOCK").encode()).hexdigest()
        
        valid_payload = {
            "tx_id": "valid_1",
            "amount": "99",
            "currency": "EUR",
            "source": "BUNQ",
            "signature": valid_sig,
        }
        test_file = test_dir / "tx_valid.json"
        test_file.write_text(json.dumps(valid_payload))

        await oracle._check_signals()

        assert len(oracle.engine.stored_facts) == 1
        assert oracle.engine.stored_facts[0]["meta"]["amount"] == "99"
        assert not test_file.exists()

    async def test_idempotency(self, oracle, test_dir, caplog):
        """Test duplicate transactions are not stored twice."""
        payload_str = json.dumps({
            "tx_id": "idem_1",
            "amount": "50",
            "currency": "USD",
            "source": "STRIPE"
        })
        import hashlib
        valid_sig = hashlib.sha256((payload_str + "SOVEREIGN_KEY_MOCK").encode()).hexdigest()
        
        valid_payload = {
            "tx_id": "idem_1",
            "amount": "50",
            "currency": "USD",
            "source": "STRIPE",
            "signature": valid_sig,
        }
        # First pass
        test_dir.joinpath("tx_idem_a.json").write_text(json.dumps(valid_payload))
        await oracle._check_signals()
        assert len(oracle.engine.stored_facts) == 1

        # Second pass with same tx_id
        test_dir.joinpath("tx_idem_b.json").write_text(json.dumps(valid_payload))
        with caplog.at_level(logging.WARNING):
            await oracle._check_signals()
            
        assert len(oracle.engine.stored_facts) == 1 # Still 1
        assert "prevented replay attack" in caplog.text.lower()
