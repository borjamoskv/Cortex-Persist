from __future__ import annotations

import os

import cortex.adk.tools as adk_tools
import cortex.extensions.adk.tools as ext_adk_tools


def _restore_env(original_db: str | None, original_db_path: str | None) -> None:
    if original_db is None:
        os.environ.pop("CORTEX_DB", None)
    else:
        os.environ["CORTEX_DB"] = original_db

    if original_db_path is None:
        os.environ.pop("CORTEX_DB_PATH", None)
    else:
        os.environ["CORTEX_DB_PATH"] = original_db_path


def test_adk_tools_accept_canonical_and_legacy_db_env_names() -> None:
    original_db = os.environ.get("CORTEX_DB")
    original_db_path = os.environ.get("CORTEX_DB_PATH")

    try:
        os.environ["CORTEX_DB"] = "/tmp/canonical.db"
        os.environ["CORTEX_DB_PATH"] = "/tmp/legacy.db"
        assert adk_tools._get_db_path() == "/tmp/canonical.db"
        assert ext_adk_tools._get_db_path() == "/tmp/canonical.db"

        os.environ.pop("CORTEX_DB", None)
        assert adk_tools._get_db_path() == "/tmp/legacy.db"
        assert ext_adk_tools._get_db_path() == "/tmp/legacy.db"
    finally:
        _restore_env(original_db, original_db_path)
