# [C5-REAL] Exergy-Maximized
import os
import base64
import stat
import pytest
from unittest.mock import patch, MagicMock

from babylon60.ledger.store import LedgerStore
from babylon60.ledger.verifier import LedgerVerifier
from babylon60.crypto.aes import reset_default_encrypter


@pytest.fixture
def temp_store(tmp_path):
    db_path = tmp_path / "test_ledger.db"
    return LedgerStore(db_path)


def test_mldsa_key_permissions_and_encryption(temp_store, tmp_path):
    """Verify ML-DSA key generation enforces chmod 600 and encrypts when master key is active."""
    verifier = LedgerVerifier(temp_store)

    # 1. Reset encrypter and mock active Master Key
    reset_default_encrypter()
    mock_master_key = b"A" * 32

    with patch("cortex.crypto.keyring.get_master_key", return_value=mock_master_key):
        # Generate the private key
        pk = verifier._get_mldsa_private_key()
        assert pk is not None

        # Check that the file was created
        key_path = os.path.join(str(tmp_path), "cortex_mldsa_sovereign.bin")
        assert os.path.exists(key_path)

        # Check permissions are chmod 600
        mode = os.stat(key_path).st_mode
        assert stat.S_IMODE(mode) == 0o600

        # Check file content is encrypted (starts with v6_aesgcm:)
        with open(key_path, "rb") as f:
            content = f.read()
        assert content.startswith(b"v6_aesgcm:")

        # 2. Check we can load it back
        pk_loaded = verifier._get_mldsa_private_key()
        assert pk_loaded.private_bytes_raw() == pk.private_bytes_raw()


def test_mldsa_key_legacy_fallback(temp_store, tmp_path):
    """Verify we can load a legacy unencrypted ML-DSA key, and it auto-migrates when master key is active."""
    verifier = LedgerVerifier(temp_store)
    key_path = os.path.join(str(tmp_path), "cortex_mldsa_sovereign.bin")

    # Generate a dummy raw seed (32 bytes)
    legacy_seed = os.urandom(32)
    with open(key_path, "wb") as f:
        f.write(legacy_seed)

    # Set some open permissions to check if chmod 600 is enforced on read/load
    os.chmod(key_path, 0o666)

    reset_default_encrypter()
    mock_master_key = b"B" * 32

    with patch("cortex.crypto.keyring.get_master_key", return_value=mock_master_key):
        # Load key (should read legacy format and automatically migrate it to encrypted)
        pk = verifier._get_mldsa_private_key()
        assert pk.private_bytes_raw() == legacy_seed

        # Confirm permissions updated to 600
        mode = os.stat(key_path).st_mode
        assert stat.S_IMODE(mode) == 0o600

        # Confirm file is now encrypted
        with open(key_path, "rb") as f:
            content = f.read()
        assert content.startswith(b"v6_aesgcm:")

        # Reload to make sure decrypted version still matches
        pk_reloaded = verifier._get_mldsa_private_key()
        assert pk_reloaded.private_bytes_raw() == legacy_seed


def test_mldsa_key_keyring_vaulting(temp_store, tmp_path):
    """Verify we try to vault the ML-DSA key in keyring if keyring is available."""
    verifier = LedgerVerifier(temp_store)

    reset_default_encrypter()
    mock_keyring = MagicMock()
    mock_keyring.get_password.return_value = None

    with (
        patch("cortex.crypto.keyring.keyring", mock_keyring),
        patch("os.environ", {"CORTEX_TESTING": ""}),
    ):  # Enable keyring mock usage
        pk = verifier._get_mldsa_private_key()

        # Verify keyring.set_password was called with generated seed
        mock_keyring.set_password.assert_called_once()
        args = mock_keyring.set_password.call_args[0]
        assert args[0] == "cortex_v6"
        assert args[1] == "mldsa_sovereign_seed"
        # Seed should be base64 encoded string
        seed_bytes = base64.b64decode(args[2])
        assert len(seed_bytes) == 32
        assert seed_bytes == pk.private_bytes_raw()
