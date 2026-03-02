"""Tests for cortex.utils.result — Railway Oriented Programming monads."""

from __future__ import annotations

import pytest

from cortex.utils.result import Err, Ok, safe, safe_async


# ─── Ok / Err Construction ───────────────────────────────────────────


class TestOk:
    def test_ok_value(self):
        r = Ok(42)
        assert r.value == 42

    def test_ok_is_ok(self):
        assert Ok("x").is_ok() is True

    def test_ok_is_not_err(self):
        assert Ok("x").is_err() is False

    def test_ok_unwrap(self):
        assert Ok("data").unwrap() == "data"

    def test_ok_unwrap_or_returns_value(self):
        assert Ok(10).unwrap_or(99) == 10

    def test_ok_repr(self):
        assert repr(Ok(7)) == "Ok(7)"


class TestErr:
    def test_err_error(self):
        r = Err("boom")
        assert r.error == "boom"

    def test_err_is_err(self):
        assert Err("x").is_err() is True

    def test_err_is_not_ok(self):
        assert Err("x").is_ok() is False

    def test_err_unwrap_raises(self):
        with pytest.raises(ValueError, match="Called unwrap"):
            Err("fail").unwrap()

    def test_err_unwrap_or_returns_default(self):
        assert Err("fail").unwrap_or(42) == 42

    def test_err_repr(self):
        assert repr(Err("oops")) == "Err('oops')"


# ─── Railway Chaining ────────────────────────────────────────────────


class TestRailway:
    def test_ok_map(self):
        result = Ok(5).map(lambda x: x * 2)
        assert isinstance(result, Ok)
        assert result.value == 10

    def test_err_map_noop(self):
        result = Err("e").map(lambda x: x * 2)
        assert isinstance(result, Err)
        assert result.error == "e"

    def test_ok_flat_map(self):
        result = Ok(3).flat_map(lambda x: Ok(x + 1))
        assert isinstance(result, Ok)
        assert result.value == 4

    def test_ok_flat_map_to_err(self):
        result = Ok(3).flat_map(lambda _: Err("nope"))
        assert isinstance(result, Err)

    def test_err_flat_map_noop(self):
        result = Err("e").flat_map(lambda x: Ok(x + 1))
        assert isinstance(result, Err)

    def test_ok_map_err_noop(self):
        result = Ok(1).map_err(lambda e: f"wrapped: {e}")
        assert isinstance(result, Ok)
        assert result.value == 1

    def test_err_map_err(self):
        result = Err("raw").map_err(lambda e: f"wrapped: {e}")
        assert isinstance(result, Err)
        assert result.error == "wrapped: raw"


# ─── Pattern Matching ────────────────────────────────────────────────


class TestPatternMatching:
    def test_match_ok(self):
        result = Ok(99)
        match result:
            case Ok(v):
                assert v == 99
            case Err(_):
                pytest.fail("Should not match Err")

    def test_match_err(self):
        result = Err("bad")
        match result:
            case Ok(_):
                pytest.fail("Should not match Ok")
            case Err(e):
                assert e == "bad"


# ─── @safe / @safe_async Decorators ──────────────────────────────────


class TestSafeDecorators:
    def test_safe_success(self):
        @safe
        def divide(a: int, b: int) -> float:
            return a / b

        result = divide(10, 2)
        assert isinstance(result, Ok)
        assert result.value == 5.0

    def test_safe_failure(self):
        @safe
        def divide(a: int, b: int) -> float:
            return a / b

        result = divide(10, 0)
        assert isinstance(result, Err)
        assert "ZeroDivisionError" in result.error

    async def test_safe_async_success(self):
        @safe_async
        async def fetch(x: int) -> int:
            return x + 1

        result = await fetch(5)
        assert isinstance(result, Ok)
        assert result.value == 6

    async def test_safe_async_failure(self):
        @safe_async
        async def blow_up() -> None:
            raise RuntimeError("async boom")

        result = await blow_up()
        assert isinstance(result, Err)
        assert "RuntimeError" in result.error
        assert "async boom" in result.error
