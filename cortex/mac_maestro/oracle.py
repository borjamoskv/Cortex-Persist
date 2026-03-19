from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OracleVerdict:
    verified: bool
    reason: str | None = None


class VerificationOracle:
    def __init__(
        self,
        rescan_fn: Callable[[], dict[str, Any]],
        matcher_fn: Callable[[dict[str, Any]], bool],
    ) -> None:
        self.rescan_fn = rescan_fn
        self.matcher_fn = matcher_fn

    def verify(self) -> OracleVerdict:
        try:
            state = self.rescan_fn()
            ok = self.matcher_fn(state)
            return OracleVerdict(verified=ok, reason=None if ok else "state_not_changed")
        except Exception as exc:
            return OracleVerdict(verified=False, reason=str(exc))
