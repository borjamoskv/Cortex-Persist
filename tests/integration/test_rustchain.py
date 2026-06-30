# [C5-REAL] Exergy-Maximized
"""Unit and integration tests for RustChain Staking & Judge ecosystem."""

from __future__ import annotations

import ast
import json
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from babylon60.integration.rustchain.client import RustChainClient
from babylon60.integration.rustchain.wallet import RustChainWallet
from babylon60.integration.rustchain.staking import (
    stake_and_acquire,
    StakingError,
    GateUnavailableError,
)
from babylon60.integration.rustchain.mcp_tool import register_rustchain_tools
from babylon60.integration.rustchain.judge import (
    Judge,
    ASTLintJudge,
    TestRunnerJudge,
    PolicyJudge,
)
from mcp.server.fastmcp import FastMCP


# ─── Wallet Tests ──────────────────────────────────────────────────


def test_rustchain_wallet_creation() -> None:
    wallet = RustChainWallet.create()
    assert wallet.address.startswith("RTC")
    assert len(wallet.address) > 20
    assert len(wallet.public_key_bytes) == 32
    assert len(wallet.public_key_hex) == 64

    # From private key bytes
    priv_bytes = wallet._private_key.private_bytes(
        encoding=pytest.importorskip("cryptography.hazmat.primitives.serialization").Encoding.Raw,
        format=pytest.importorskip(
            "cryptography.hazmat.primitives.serialization"
        ).PrivateFormat.Raw,
        encryption_algorithm=pytest.importorskip(
            "cryptography.hazmat.primitives.serialization"
        ).NoEncryption(),
    )
    imported = RustChainWallet.from_private_key_bytes(priv_bytes)
    assert imported.address == wallet.address
    assert imported.public_key_hex == wallet.public_key_hex


def test_rustchain_wallet_signing() -> None:
    wallet = RustChainWallet.create()
    message = b"hello world"
    sig = wallet.sign(message)
    assert len(sig) == 64

    # Sign transfer
    tx = wallet.sign_transfer("RTCrecipientaddress", 100, fee=1)
    assert tx["from"] == wallet.address
    assert tx["to"] == "RTCrecipientaddress"
    assert tx["amount"] == 100
    assert tx["fee"] == 1
    assert "signature" in tx


# ─── Client Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rustchain_client_mock_mode() -> None:
    client = RustChainClient(mock_mode=True)
    health = await client.health()
    assert health["healthy"] is True
    assert health["epoch"] == 42

    balance = await client.get_balance("RTCaddress")
    assert balance["balance"] == 1000000

    stake = await client.stake_rtc("RTCaddress", 100, "skill_x", "signature_hex", 123456)
    assert stake["status"] == "success"
    assert "tx_hash" in stake
    assert stake["attestation"]["verdict"] == "approved"
    await client.close()


# ─── Staking Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stake_and_acquire_success() -> None:
    wallet = RustChainWallet.create()
    client = RustChainClient(mock_mode=True)
    res = await stake_and_acquire(wallet, client, "cortex_cognitive", 50)
    assert res["status"] == "success"
    assert res["attestation"]["skill"] == "cortex_cognitive"
    assert res["attestation"]["amount"] == 50


@pytest.mark.asyncio
async def test_stake_and_acquire_gate_unavailable() -> None:
    wallet = RustChainWallet.create()

    # Mock client indicating unhealthy status
    class UnhealthyClient(RustChainClient):
        async def health(self) -> dict:
            return {"healthy": False, "error": "Connection timed out"}

    client = UnhealthyClient(mock_mode=True)
    with pytest.raises(GateUnavailableError, match="RustChain gate is unhealthy or offline"):
        await stake_and_acquire(wallet, client, "cortex_cognitive", 50)


# ─── LangChain & MCP Tool Tests ───────────────────────────────────


def test_mcp_tool_registration() -> None:
    mcp = FastMCP("Test MCP")
    wallet = RustChainWallet.create()
    client = RustChainClient(mock_mode=True)

    register_rustchain_tools(mcp, wallet, client)
    # Verify the tool was registered
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "stake_and_acquire_skill" in tool_names


# ─── Judge Interface & Implementation Tests ───────────────────────


@pytest.mark.asyncio
async def test_ast_lint_judge() -> None:
    judge = ASTLintJudge()

    # Pass case
    pass_code = """
def process_data(x):
    \"\"\"Docstring info.\"\"\"
    try:
        return int(x)
    except ValueError as e:
        return None
"""
    passed, reasons = await judge.judge(pass_code)
    assert passed is True
    assert len(reasons) == 0

    # Fail cases: banned terms (eval, exec), bare except
    fail_code = """
def bad_func(x):
    eval(x)
    try:
        y = x + 1
    except:
        pass
"""
    passed, reasons = await judge.judge(fail_code)
    assert passed is False
    assert any("banned term: eval" in r for r in reasons)
    assert any("bare except" in r for r in reasons)


@pytest.mark.asyncio
async def test_policy_judge() -> None:
    judge = PolicyJudge()

    code = """# Inline comment
import os
import sys

def func():
    # Another comment
    pass
"""
    config = {
        "max_lines": 50,
        "banned_imports": ["subprocess"],
        "min_comment_ratio": 0.1,
    }
    # Pass case
    passed, reasons = await judge.judge(code, config)
    assert passed is True

    # Fail: max lines
    failed_lines, reasons_lines = await judge.judge(code, {"max_lines": 2})
    assert failed_lines is False
    assert any("exceeds maximum permitted" in r for r in reasons_lines)

    # Fail: banned imports
    failed_imports, reasons_imports = await judge.judge(code, {"banned_imports": ["os"]})
    assert failed_imports is False
    assert any("banned library: os" in r for r in reasons_imports)


@pytest.mark.asyncio
async def test_test_runner_judge() -> None:
    judge = TestRunnerJudge()

    # Pass case
    code = """
def add(a, b):
    return a + b
"""
    test_code = """
from solution import add
def test_add():
    assert add(2, 3) == 5
"""
    passed, reasons = await judge.judge(code, {"test_code": test_code})
    assert passed is True, f"Reasons: {reasons}"
    assert len(reasons) == 0

    # Fail case
    fail_test_code = """
from solution import add
def test_add():
    assert add(2, 3) == 99
"""
    passed_fail, reasons_fail = await judge.judge(code, {"test_code": fail_test_code})
    assert passed_fail is False
    assert len(reasons_fail) > 0
    assert any("pytest failed" in r for r in reasons_fail)


def test_verdict_signing_and_verification() -> None:
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()

    priv_bytes = priv_key.private_bytes(
        encoding=pytest.importorskip("cryptography.hazmat.primitives.serialization").Encoding.Raw,
        format=pytest.importorskip(
            "cryptography.hazmat.primitives.serialization"
        ).PrivateFormat.Raw,
        encryption_algorithm=pytest.importorskip(
            "cryptography.hazmat.primitives.serialization"
        ).NoEncryption(),
    )
    pub_bytes = pub_key.public_bytes(
        encoding=pytest.importorskip("cryptography.hazmat.primitives.serialization").Encoding.Raw,
        format=pytest.importorskip("cryptography.hazmat.primitives.serialization").PublicFormat.Raw,
    )

    reasons = ["Use of banned term: eval", "bare except"]
    verdict = Judge.sign_verdict(priv_bytes, passed=False, reasons=reasons)

    assert verdict["passed"] is False
    assert verdict["reasons"] == reasons
    assert "signature" in verdict

    # Verify signature
    assert Judge.verify_verdict(verdict, pub_bytes) is True

    # Tampered signature check
    tampered = verdict.copy()
    tampered["passed"] = True
    assert Judge.verify_verdict(tampered, pub_bytes) is False
