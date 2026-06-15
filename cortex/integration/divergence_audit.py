from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class DivergenceReport:
    agent_id: str
    observed_fingerprint: str
    expected_fingerprint: str
    route_deltas: list[dict[str, Any]]
    severity: str
    timestamp: float
    proof_hash: str


class DivergenceAuditor:
    def diff_capabilities(
        self,
        expected: dict[str, Any],
        actual: dict[str, Any],
    ) -> list[dict[str, Any]]:
        deltas: list[dict[str, Any]] = []

        expected_routes = expected.get("routes", {})
        actual_routes = actual.get("routes", {})

        missing = sorted(set(expected_routes) - set(actual_routes))
        extra = sorted(set(actual_routes) - set(expected_routes))
        for route in missing:
            deltas.append({"type": "missing_route", "route": route})
        for route in extra:
            deltas.append({"type": "unexpected_route", "route": route})

        for route in sorted(set(expected_routes) & set(actual_routes)):
            if expected_routes[route] != actual_routes[route]:
                deltas.append(
                    {
                        "type": "route_signature_mismatch",
                        "route": route,
                        "expected": expected_routes[route],
                        "actual": actual_routes[route],
                    }
                )

        exp_caps = set(expected.get("capabilities", []))
        act_caps = set(actual.get("capabilities", []))

        for cap in sorted(exp_caps - act_caps):
            deltas.append({"type": "missing_capability", "capability": cap})

        for cap in sorted(act_caps - exp_caps):
            deltas.append({"type": "unexpected_capability", "capability": cap})

        return deltas

    def severity_for(self, deltas: list[dict[str, Any]]) -> str:
        if not deltas:
            return "ok"
        kinds = {d["type"] for d in deltas}
        if "missing_route" in kinds or "route_signature_mismatch" in kinds:
            return "high"
        if "missing_capability" in kinds:
            return "medium"
        return "low"

    def build_report(
        self,
        agent_id: str,
        observed_fingerprint: str,
        expected_fingerprint: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
        timestamp: float,
    ) -> DivergenceReport:
        deltas = self.diff_capabilities(expected, actual)
        severity = self.severity_for(deltas)
        import json
        payload = {
            "agent_id": agent_id,
            "observed_fingerprint": observed_fingerprint,
            "expected_fingerprint": expected_fingerprint,
            "route_deltas": deltas,
            "severity": severity,
            "timestamp": timestamp,
        }
        proof_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        proof_hash = hashlib.sha256(proof_payload.encode()).hexdigest()

        return DivergenceReport(
            agent_id=agent_id,
            observed_fingerprint=observed_fingerprint,
            expected_fingerprint=expected_fingerprint,
            route_deltas=deltas,
            severity=severity,
            timestamp=timestamp,
            proof_hash=proof_hash,
        )
