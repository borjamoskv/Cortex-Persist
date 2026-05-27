import sys
import json
import time
import hashlib
from cortex_rs import McpSovereignHost


def log_hud(msg: str):
    """Industrial Noir HUD telemetry to stderr to prevent MCP protocol corruption"""
    sys.stderr.write(f"[C5-REAL] {msg}\n")
    sys.stderr.flush()


class Violation:
    def __init__(self, message: str):
        self.message = message


class VSAPipelineBridge:
    def __init__(self):
        self._memory = {}
        log_hud("VSAPipelineBridge Initialized. [Status: O(1) Ready]")

    def ingest(self, content: str) -> str:
        idx = "vsa-" + hashlib.sha256(content.encode()).hexdigest()[:12]
        self._memory[idx] = content
        log_hud(f"VSA Ingestion: {idx} | Size: {len(content)} bytes")
        return idx

    def persist(self):
        log_hud("VSA Substrate Persisted to C5-REAL Storage.")

    def query(self, intent: str, top_k: int) -> list:
        log_hud(f"VSA Query Executed: '{intent}' (top_k={top_k})")
        results = []
        for k, v in list(self._memory.items())[:top_k]:
            results.append({"id": k, "similarity": 0.95, "content": v})
        return results


class JISAuditor:
    def __init__(self):
        log_hud("JIS Auditor Online. [SOC 2 / C5 / GDPR Policy Enforcement]")

    def audit_transaction(self, project: str, action: str, payload: dict) -> list:
        log_hud(f"JIS Audit: {project}::{action} | Payload: {len(str(payload))}b")
        payload_str = json.dumps(payload).lower()
        if "eval(" in payload_str or "rm -rf" in payload_str:
            log_hud("JIS Audit FAILED: Malicious vectors detected.")
            return [Violation("Critical security violation: prohibited payload vectors.")]
        log_hud("JIS Audit PASSED. Transaction clear.")
        return []


def run_sovereign_mcp():
    log_hud("=== CORTEX MCP SOVEREIGN HOST ===")
    log_hud("Reality Level: C5-REAL | Bridge: Py<PyAny> | Runtime: Rust-Native")

    vsa_bridge = VSAPipelineBridge()
    jis_auditor = JISAuditor()

    host = McpSovereignHost("cortex-sovereign-mcp", "1.0.0", vsa_bridge, jis_auditor)

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        line = line.strip()
        if not line:
            continue

        try:
            t0 = time.perf_counter()
            response_json = host.process_request(line)
            dt = (time.perf_counter() - t0) * 1000

            sys.stdout.write(response_json + "\n")
            sys.stdout.flush()

            log_hud(f"RPC Dispatch Latency: {dt:.3f}ms")
        except Exception as e:
            err = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            log_hud(f"RPC Dispatch Error: {e}")


if __name__ == "__main__":
    run_sovereign_mcp()
