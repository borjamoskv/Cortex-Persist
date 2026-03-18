from __future__ import annotations

from cortex.auth.manager import AuthManager


def test_infer_plan_from_rate_limit() -> None:
    assert AuthManager._infer_plan(100) == "free"
    assert AuthManager._infer_plan(299) == "free"
    assert AuthManager._infer_plan(300) == "pro"
    assert AuthManager._infer_plan(999) == "pro"
    assert AuthManager._infer_plan(1000) == "team"
