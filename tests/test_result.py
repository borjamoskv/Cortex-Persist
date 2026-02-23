"""Tests for cortex.result — Railway Oriented Programming monads."""

from __future__ import annotations

import json

import pytest

from cortex.result import Err, Ok, safe, safe_async

# ─── Ok Tests ─────────────────────────────────────────────────────────


class TestOk:
    def test_is_ok(self):
        assert Ok(42).is_ok() is True

    def test_is_err(self):
        assert Ok(42).is_err() is False

    def test_unwrap(self):
        assert Ok("hello").unwrap() == "hello"

    def test_unwrap_or(self):
        assert Ok(42).unwrap_or(0) == 42

    def test_map(self):
        result = Ok(5).map(lambda x: x * 2)
        assert isinstance(result, Ok)
        assert result.value == 10

    def test_flat_map_success(self):
        result = Ok(5).flat_map(lambda x: Ok(x * 2))
        assert isinstance(result, Ok)
        assert result.value == 10

    def test_flat_map_failure(self):
        result = Ok(5).flat_map(lambda x: Err("boom"))
        assert isinstance(result, Err)
        assert result.error == "boom"

    def test_map_err_noop(self):
        result = Ok(42).map_err(lambda e: e.upper())
        assert isinstance(result, Ok)
        assert result.value == 42

    def test_repr(self):
        assert "Ok(42)" in repr(Ok(42))

    def test_frozen(self):
        ok = Ok(42)
        with pytest.raises(AttributeError):
            ok.value = 99  # type: ignore[misc]


# ─── Err Tests ────────────────────────────────────────────────────────


class TestErr:
    def test_is_ok(self):
        assert Err("fail").is_ok() is False

    def test_is_err(self):
        assert Err("fail").is_err() is True

    def test_unwrap_raises(self):
        with pytest.raises(ValueError, match="Called unwrap"):
            Err("fail").unwrap()

    def test_unwrap_or(self):
        assert Err("fail").unwrap_or(42) == 42

    def test_map_noop(self):
        result = Err("fail").map(lambda x: x * 2)
        assert isinstance(result, Err)
        assert result.error == "fail"

    def test_flat_map_noop(self):
        result = Err("fail").flat_map(lambda x: Ok(x * 2))
        assert isinstance(result, Err)

    def test_map_err(self):
        result = Err("fail").map_err(lambda e: e.upper())
        assert isinstance(result, Err)
        assert result.error == "FAIL"

    def test_repr(self):
        assert "Err('fail')" in repr(Err("fail"))


# ─── Pattern Matching ─────────────────────────────────────────────────


class TestPatternMatching:
    def test_match_ok(self):
        result = Ok(42)
        match result:
            case Ok(value=v):
                assert v == 42
            case Err():
                pytest.fail("Should not match Err")

    def test_match_err(self):
        result = Err("boom")
        match result:
            case Ok():
                pytest.fail("Should not match Ok")
            case Err(error=e):
                assert e == "boom"


# ─── Decorators ───────────────────────────────────────────────────────


class TestSafeDecorator:
    def test_success(self):
        @safe
        def parse(raw: str) -> dict:
            return json.loads(raw)

        result = parse('{"key": "value"}')
        assert isinstance(result, Ok)
        assert result.value == {"key": "value"}

    def test_failure(self):
        @safe
        def parse(raw: str) -> dict:
            return json.loads(raw)

        result = parse("not-json")
        assert isinstance(result, Err)
        assert "JSONDecodeError" in result.error


class TestSafeAsyncDecorator:
    @pytest.mark.asyncio
    async def test_success(self):
        @safe_async
        async def compute(x: int) -> int:
            return x * 2

        result = await compute(21)
        assert isinstance(result, Ok)
        assert result.value == 42

    @pytest.mark.asyncio
    async def test_failure(self):
        @safe_async
        async def compute(x: int) -> int:
            raise ValueError("bad input")

        result = await compute(0)
        assert isinstance(result, Err)
        assert "ValueError" in result.error


# ─── Chaining ─────────────────────────────────────────────────────────


class TestChaining:
    def test_chain_success(self):
        result = Ok(10).map(lambda x: x + 5).map(lambda x: x * 2)
        assert isinstance(result, Ok)
        assert result.value == 30

    def test_chain_stops_on_error(self):
        result = Ok(10).flat_map(lambda _: Err("broken")).map(lambda x: x * 2)
        assert isinstance(result, Err)
        assert result.error == "broken"
