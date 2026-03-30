"""
tests/guards/test_ast_interceptor.py
─────────────────────────────────────
Tests for the AST Gateway — Zero-Trust Sidecar Interceptor (Ω1, Ω3)
"""

from cortex.guards.ast_interceptor import (
    ASTInterceptor,
    ASTSafetyAnalyzer,
    SchemaConstraint,
    ShadowRun,
    StateQuarantine,
    StrictSchemaEnforcer,
    Verdict,
)

# ─── Schema Enforcer ─────────────────────────────────────────────────────────


class TestStrictSchemaEnforcer:
    def setup_method(self):
        self.enforcer = StrictSchemaEnforcer()
        self.enforcer.register(
            "db_write",
            [
                SchemaConstraint(name="query", type="str", max_length=500),
                SchemaConstraint(name="table", type="str", required=True),
                SchemaConstraint(name="dry_run", type="bool", required=False),
            ],
        )

    def test_valid_payload_passes(self):
        violations = self.enforcer.validate(
            "db_write", {"query": "SELECT 1", "table": "users"}
        )
        assert violations == []

    def test_missing_required_field(self):
        violations = self.enforcer.validate("db_write", {"query": "SELECT 1"})
        assert any("Missing required field" in v for v in violations)

    def test_type_violation(self):
        violations = self.enforcer.validate(
            "db_write", {"query": "SELECT 1", "table": 42}
        )
        assert any("Type violation" in v for v in violations)

    def test_length_violation(self):
        violations = self.enforcer.validate(
            "db_write", {"query": "x" * 600, "table": "users"}
        )
        assert any("Length violation" in v for v in violations)

    def test_undeclared_fields_detected(self):
        violations = self.enforcer.validate(
            "db_write", {"query": "ok", "table": "users", "injected": True}
        )
        assert any("Undeclared fields" in v for v in violations)

    def test_unregistered_tool_fails_closed(self):
        violations = self.enforcer.validate("unknown_tool", {"data": "x"})
        assert any("No schema registered" in v for v in violations)

    def test_optional_field_absent_ok(self):
        violations = self.enforcer.validate(
            "db_write", {"query": "ok", "table": "users"}
        )
        assert violations == []

    def test_optional_field_present_validated(self):
        violations = self.enforcer.validate(
            "db_write", {"query": "ok", "table": "users", "dry_run": "not_a_bool"}
        )
        assert any("Type violation" in v for v in violations)


# ─── AST Safety Analyzer ─────────────────────────────────────────────────────


class TestASTSafetyAnalyzer:
    def test_safe_code_passes(self):
        code = "result = 1 + 2\nprint(result)\n"
        violations = ASTSafetyAnalyzer.analyze(code)
        assert violations == []

    def test_eval_detected(self):
        code = "x = eval('1+1')\n"
        violations = ASTSafetyAnalyzer.analyze(code)
        assert any("eval()" in v for v in violations)

    def test_exec_detected(self):
        code = "exec('import os; os.system(\"rm -rf /\")')\n"
        violations = ASTSafetyAnalyzer.analyze(code)
        assert any("exec()" in v for v in violations)

    def test_os_system_detected(self):
        code = "import os\nos.system('ls')\n"
        violations = ASTSafetyAnalyzer.analyze(code)
        assert len(violations) >= 1  # both import + call

    def test_dunder_access_detected(self):
        code = "x.__class__.__subclasses__()\n"
        violations = ASTSafetyAnalyzer.analyze(code)
        assert any("__class__" in v or "__subclasses__" in v for v in violations)

    def test_syntax_error_reported(self):
        code = "def broken(:\n"
        violations = ASTSafetyAnalyzer.analyze(code)
        assert any("Syntax error" in v for v in violations)

    def test_subprocess_import_caught(self):
        code = "import subprocess\n"
        violations = ASTSafetyAnalyzer.analyze(code)
        assert any("subprocess" in v for v in violations)


# ─── State Quarantine ────────────────────────────────────────────────────────


class TestStateQuarantine:
    def test_quarantine_stores_entry(self):
        q = StateQuarantine()
        entry = q.quarantine("agent-1", "tool-x", {"bad": True}, ["violation-1"])
        assert entry.quarantine_id.startswith("Q-")
        assert q.count == 1

    def test_unresolved_tracking(self):
        q = StateQuarantine()
        q.quarantine("a", "t", {}, ["v"])
        assert len(q.unresolved) == 1

    def test_capacity_eviction(self):
        q = StateQuarantine(max_capacity=3)
        for i in range(5):
            q.quarantine(f"agent-{i}", "tool", {}, [f"v-{i}"])
        assert q.count == 3

    def test_telemetry_snapshot(self):
        q = StateQuarantine()
        q.quarantine("a1", "db_write", {}, ["Type violation"])
        q.quarantine("a2", "api_call", {}, ["Missing required field"])
        snap = q.telemetry_snapshot()
        assert snap["total_quarantined"] == 2
        assert "a1" in snap["by_agent"]
        assert "db_write" in snap["by_tool"]


# ─── ASTInterceptor (Integration) ────────────────────────────────────────────


class TestASTInterceptor:
    def setup_method(self):
        self.interceptor = ASTInterceptor()
        self.interceptor.register_tool_schema(
            "db_write",
            [
                SchemaConstraint(name="query", type="str", max_length=500),
                SchemaConstraint(name="table", type="str"),
            ],
        )

    def test_valid_call_passes(self):
        result = self.interceptor.intercept(
            "agent-1", "db_write", {"query": "SELECT 1", "table": "users"}
        )
        assert result.passed
        assert result.verdict == Verdict.PASS
        assert result.violations == []

    def test_invalid_call_quarantined(self):
        result = self.interceptor.intercept(
            "agent-2", "db_write", {"query": "x" * 600, "table": 42}
        )
        assert not result.passed
        assert result.verdict == Verdict.QUARANTINE
        assert len(result.violations) >= 2
        assert result.quarantine_id is not None

    def test_constraint_feedback_generated(self):
        result = self.interceptor.intercept(
            "agent-3", "db_write", {"wrong_field": "data"}
        )
        assert result.constraint_feedback is not None
        assert result.constraint_feedback["error"] == "CORTEX_AST_INTERCEPTION"
        assert result.constraint_feedback["retry_allowed"] is True

    def test_code_field_ast_analysis(self):
        result = self.interceptor.intercept(
            "agent-4",
            "db_write",
            {"query": "ok", "table": "users", "code": "eval('hack')"},
        )
        # Has undeclared field 'code' + dangerous call eval()
        assert not result.passed

    def test_ledger_entry_format(self):
        result = self.interceptor.intercept(
            "agent-5", "db_write", {"query": "ok", "table": "t"}
        )
        entry = result.to_ledger_entry()
        assert entry["type"] == "ast_interception"
        assert "payload_hash" in entry
        assert "timestamp" in entry

    def test_telemetry_accumulates(self):
        for i in range(5):
            self.interceptor.intercept(
                f"a{i}", "db_write", {"query": "ok", "table": "t"}
            )
        tel = self.interceptor.telemetry()
        assert tel["total_interceptions"] == 5
        assert tel["passed"] == 5
        assert tel["rejected"] == 0

    def test_unregistered_tool_rejects(self):
        result = self.interceptor.intercept(
            "agent-x", "unknown_tool", {"data": "value"}
        )
        assert not result.passed
        assert any("No schema registered" in v for v in result.violations)


# ─── ShadowRun (Proof of Poison) ─────────────────────────────────────────────


class TestShadowRun:
    def test_shadow_always_passes(self):
        interceptor = ASTInterceptor()
        interceptor.register_tool_schema(
            "api", [SchemaConstraint(name="url", type="str")]
        )
        shadow = ShadowRun(interceptor)

        # This payload is invalid (missing 'url', has undeclared 'bad')
        result = shadow.shadow_intercept("rogue", "api", {"bad": "data"})
        assert result.passed  # Shadow mode: always PASS

    def test_proof_of_poison_captures_failures(self):
        interceptor = ASTInterceptor()
        interceptor.register_tool_schema(
            "store", [SchemaConstraint(name="key", type="str")]
        )
        shadow = ShadowRun(interceptor)

        # Send invalid payloads
        shadow.shadow_intercept("a1", "store", {"wrong": 1})
        shadow.shadow_intercept("a2", "store", {"also_wrong": 2})
        # Send valid payload
        shadow.shadow_intercept("a3", "store", {"key": "valid"})

        pop = shadow.proof_of_poison()
        proof = pop["proof_of_poison"]
        assert proof["total_silent_failures_detected"] == 2
        assert proof["chain_hash"]  # non-empty hash
        assert len(proof["entries"]) == 2
        assert all(e["would_have_corrupted"] for e in proof["entries"])

    def test_proof_of_poison_hash_chain(self):
        interceptor = ASTInterceptor()
        interceptor.register_tool_schema(
            "t", [SchemaConstraint(name="x", type="str")]
        )
        shadow = ShadowRun(interceptor)
        shadow.shadow_intercept("a1", "t", {"wrong": 1})

        pop1 = shadow.proof_of_poison()
        pop2 = shadow.proof_of_poison()
        # Same data → same hash
        assert pop1["proof_of_poison"]["chain_hash"] == pop2["proof_of_poison"]["chain_hash"]
