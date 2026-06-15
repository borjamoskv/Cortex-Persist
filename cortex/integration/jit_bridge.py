from __future__ import annotations

import ast
import hashlib
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class BridgeArtifact:
    bridge_id: str
    agent_id: str
    expected_signature: dict[str, Any]
    actual_signature: dict[str, Any]
    adapter_code: str
    compiled_at: float
    compile_latency_ms: float


class JITBridgeCompiler:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir
        self.cache: dict[str, BridgeArtifact] = {}

    def compile_bridge(
        self,
        agent_id: str,
        expected_signature: dict[str, Any],
        actual_signature: dict[str, Any],
    ) -> BridgeArtifact:
        adapter_code = self._generate_adapter_code(expected_signature, actual_signature)
        bridge_id = _sha256_text(
            f"{agent_id}:{expected_signature}:{actual_signature}:{adapter_code}"
        )
        if bridge_id in self.cache:
            return self.cache[bridge_id]

        t0 = time.perf_counter()
        ast.parse(adapter_code)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        artifact = BridgeArtifact(
            bridge_id=bridge_id,
            agent_id=agent_id,
            expected_signature=expected_signature,
            actual_signature=actual_signature,
            adapter_code=adapter_code,
            compiled_at=time.time(),
            compile_latency_ms=latency_ms,
        )
        self.cache[bridge_id] = artifact
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            (self.output_dir / f"{bridge_id}.py").write_text(adapter_code, encoding="utf-8")
        return artifact

    def invalidate_cache(self) -> None:
        self.cache.clear()

    def _generate_adapter_code(
        self,
        expected_signature: dict[str, Any],
        actual_signature: dict[str, Any],
    ) -> str:
        expected_params = expected_signature.get("params", [])
        actual_params = actual_signature.get("params", [])
        route = expected_signature.get("route", "unknown_route")

        mappings = []
        for p in expected_params:
            if p in actual_params:
                mappings.append(f'"{p}": kwargs.get("{p}")')
            else:
                mappings.append(f'"{p}": kwargs.get("{p}", None)')

        body = ", ".join(mappings) if mappings else ""
        return f'''
def bridge_adapter(actual_fn, **kwargs):
    payload = {{{body}}}
    return actual_fn(**payload)
'''.strip()
