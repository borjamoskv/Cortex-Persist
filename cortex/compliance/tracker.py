"""ComplianceTracker — EU AI Act Article 12 compliance in 3 methods.

Usage:
    from cortex.compliance import ComplianceTracker

    tracker = ComplianceTracker()
    tracker.log_decision("my-agent", "Approved loan #443", agent_id="agent:loan")
    result = tracker.verify_chain()
    report = tracker.export_audit(project="my-agent")
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from cortex.config import DEFAULT_DB_PATH
from cortex.crypto.keys import ZKSwarmIdentity

__all__ = ["ComplianceTracker"]

logger = logging.getLogger("cortex.compliance")

# EU AI Act Article 12 sub-requirements mapped to verifiable checks
_ARTICLE_12_CHECKS = {
    "art_12_1_automatic_logging": "Automatic recording of AI decisions via store()",
    "art_12_2_log_content": "Timestamps, source agent, and project scoping present",
    "art_12_2d_agent_traceability": "Agent source identification on every fact",
    "art_12_3_tamper_proof": "SHA-256 hash chain with Merkle tree checkpoints",
    "art_12_4_periodic_verification": "Integrity verification with recorded results",
}

# EU AI Act Article 14 human-oversight evidence checks.
_ARTICLE_14_CHECKS = {
    "art_14_1_human_machine_interface": "Decision logs expose a human oversight boundary",
    "art_14_2_risk_minimisation": "Oversight metadata records risk mitigation intent",
    "art_14_4a_capacity_limits": "Reviewer can inspect capacities and limitations",
    "art_14_4b_automation_bias": "Reviewer is warned about automation bias",
    "art_14_4d_override": "Reviewer can disregard, override, or reverse the output",
    "art_14_4e_stop": "Reviewer can interrupt or stop the system safely",
}

_ARTICLE_15_CHECKS = {
    "art_15_source_key_custody": "Event-source signing key custody is evidenced",
    "art_15_hardware_backing": "Production event-source keys are HSM/TPM backed",
    "art_15_external_attestation": "External source keys include deployer attestation",
}

_EVENT_SOURCE_KEY_CUSTODY_SCHEMA = "cortex.event_source_key_custody.v1"
_DEPLOYMENT_READINESS_SCHEMA = "cortex.deployment_readiness.v1"


class ComplianceTracker:
    """EU AI Act Article 12 compliance tracker for AI agent decisions.

    Wraps ``CortexEngine`` with a minimal 3-method API designed for
    drop-in compliance. All methods are synchronous for maximum
    developer friendliness.

    Args:
        db_path: Path to the SQLite database. Defaults to ``~/.cortex/cortex.db``.
        project: Default project namespace for all operations.
    """

    __slots__ = (
        "_engine",
        "_default_project",
        "_default_tenant_id",
        "_initialized",
        "_zk_keypair",
    )

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        project: str = "default",
        tenant_id: str = "default",
    ) -> None:
        from cortex.engine import CortexEngine

        self._engine = CortexEngine(db_path=str(db_path), auto_embed=False)
        self._default_project = project
        self._default_tenant_id = tenant_id
        self._initialized = False
        self._zk_keypair = ZKSwarmIdentity.generate_keypair()

    def _ensure_init(self) -> None:
        """Lazy-init the database on first use."""
        if not self._initialized:
            self._engine.init_db_sync()
            self._initialized = True

    # ─── 1. log_decision ──────────────────────────────────────────

    def log_decision(
        self,
        project: str | None = None,
        content: str = "",
        *,
        agent_id: str = "agent:unknown",
        decision_type: str = "decision",
        confidence: str = "C3",
        meta: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        tenant_id: str | None = None,
        risk_level: str = "high",
        human_reviewer_id: str | None = None,
        oversight_action: str | None = None,
        override_available: bool = True,
        stop_available: bool = True,
        automation_bias_notice: bool = True,
    ) -> int:
        """Log an AI decision with EU AI Act Article 12 metadata.

        Args:
            project: Project namespace. Falls back to the tracker default.
            content: Human-readable description of the decision.
            agent_id: Identifier for the agent making the decision.
            decision_type: Category of the decision (e.g. ``"approval"``,
                ``"rejection"``, ``"escalation"``).
            confidence: Epistemic confidence level (``C1``–``C5``).
            meta: Additional metadata to attach. Merged with EU compliance fields.
            tags: Optional tags for categorization.
            tenant_id: Tenant isolation scope. Falls back to tracker default.
            risk_level: AI Act risk label for Article 14 checks.
            human_reviewer_id: Natural person assigned to review the decision.
            oversight_action: Review action, e.g. ``"approved"`` or ``"overridden"``.
            override_available: Whether the reviewer can override/reverse output.
            stop_available: Whether the reviewer can interrupt/stop the system.
            automation_bias_notice: Whether the reviewer is warned about automation bias.

        Returns:
            The ``fact_id`` of the stored decision (int > 0).

        Raises:
            ValueError: If ``content`` is empty or fails validation.
        """
        self._ensure_init()

        proj = project or self._default_project
        resolved_tenant_id = tenant_id or self._default_tenant_id
        now = datetime.now(timezone.utc).isoformat()

        user_meta = dict(meta or {})
        eu_meta: dict[str, Any] = {
            "eu_ai_act": {
                "article": "12",
                "logged_at": now,
                "agent_id": agent_id,
                "decision_type": decision_type,
                "article_14": {
                    "risk_level": risk_level,
                    "human_reviewer_id": human_reviewer_id,
                    "oversight_action": oversight_action,
                    "reviewed_at": now if human_reviewer_id else None,
                    "override_available": override_available,
                    "stop_available": stop_available,
                    "automation_bias_notice": automation_bias_notice,
                    "capacity_limits_visible": bool(human_reviewer_id),
                },
            },
        }
        eu_meta.update(user_meta)
        self._ensure_zk_proof(
            content,
            eu_meta,
            tenant_id=resolved_tenant_id,
            project=proj,
            fact_type="decision",
            source=agent_id,
        )

        return self._engine.store_sync(  # type: ignore[type-error]
            project=proj,
            content=content,
            fact_type="decision",
            source=agent_id,
            confidence=confidence,
            meta=eu_meta,
            tags=tags or ["eu-ai-act", "compliance"],
            tenant_id=resolved_tenant_id,
        )

    def log_human_oversight(
        self,
        decision_fact_id: int,
        reviewer_id: str,
        action: str,
        *,
        rationale: str = "",
        project: str | None = None,
        tenant_id: str | None = None,
        tags: list[str] | None = None,
    ) -> int:
        """Record a natural-person oversight event linked to a decision fact."""
        self._ensure_init()
        if decision_fact_id <= 0:
            raise ValueError("decision_fact_id must be positive")
        if not reviewer_id.strip():
            raise ValueError("reviewer_id is required")
        if not action.strip():
            raise ValueError("action is required")

        proj = project or self._default_project
        resolved_tenant_id = tenant_id or self._default_tenant_id
        now = datetime.now(timezone.utc).isoformat()
        content = (
            f"Human oversight {action.strip()} for decision #{decision_fact_id}"
            + (f": {rationale.strip()}" if rationale.strip() else "")
        )
        meta: dict[str, Any] = {
            "eu_ai_act": {
                "article": "14",
                "logged_at": now,
                "decision_fact_id": decision_fact_id,
                "human_reviewer_id": reviewer_id.strip(),
                "oversight_action": action.strip(),
                "rationale": rationale,
                "override_available": True,
                "stop_available": True,
                "automation_bias_notice": True,
                "capacity_limits_visible": True,
            },
            "previous_fact_id": decision_fact_id,
        }
        self._ensure_zk_proof(
            content,
            meta,
            tenant_id=resolved_tenant_id,
            project=proj,
            fact_type="knowledge",
            source=reviewer_id.strip(),
        )

        return self._engine.store_sync(  # type: ignore[type-error]
            project=proj,
            content=content,
            fact_type="knowledge",
            source=reviewer_id.strip(),
            confidence="C5",
            meta=meta,
            tags=tags or ["eu-ai-act", "article-14", "human-oversight"],
            tenant_id=resolved_tenant_id,
        )

    # ─── 2. verify_chain ──────────────────────────────────────────

    def verify_chain(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Verify the cryptographic integrity of the decision ledger.

        Checks both the SHA-256 hash chain and Merkle tree checkpoints.

        Returns:
            A dict with keys:
            - ``valid`` (bool): ``True`` if no tampering detected.
            - ``tx_checked`` (int): Number of transactions verified.
            - ``roots_checked`` (int): Number of Merkle roots verified.
            - ``violations`` (list): Details of any integrity violations.
        """
        self._ensure_init()
        resolved_tenant_id = tenant_id or self._default_tenant_id

        ledger = self._engine._ledger
        if ledger is None:
            return {
                "valid": True,
                "tx_checked": 0,
                "roots_checked": 0,
                "violations": [],
            }

        return self._engine._run_sync(  # type: ignore[type-error]
            ledger.audit_integrity_async(tenant_id=resolved_tenant_id)
        )

    # ─── 3. export_audit ──────────────────────────────────────────

    def export_audit(
        self,
        project: str | None = None,
        *,
        include_facts: bool = False,
        tenant_id: str | None = None,
        dora_article_28_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate an EU AI Act Article 12 compliance report.

        Args:
            project: Project to scope the report to. Uses tracker default
                if not specified.
            include_facts: If ``True``, includes the full list of facts in
                the report. Defaults to ``False`` to keep reports compact.
            tenant_id: Tenant isolation scope. Falls back to tracker default.
            dora_article_28_evidence: Optional verified DORA evidence status.
                Production readiness only accepts ``status="verified_issued"``.

        Returns:
            A structured dict with:
            - ``eu_ai_act``: Article 12 compliance checks and score.
            - ``integrity``: Hash chain and Merkle verification results.
            - ``facts_summary``: Counts by fact type, date range, etc.
            - ``generated_at``: ISO timestamp of report generation.
        """
        self._ensure_init()

        proj = project or self._default_project
        resolved_tenant_id = tenant_id or self._default_tenant_id

        # 1. Run integrity check
        integrity = self.verify_chain(tenant_id=resolved_tenant_id)

        # 2. Gather facts summary
        facts_summary = cast(
            dict[str, Any],
            self._engine._run_sync(self._gather_facts_summary(proj, resolved_tenant_id)),
        )

        # 3. Evaluate Article 12 and Article 14 evidence
        checks = self._evaluate_article_12(integrity, facts_summary)  # type: ignore[type-error]
        score = sum(1 for v in checks.values() if v["compliant"])
        total = len(checks)
        article_14 = self._evaluate_article_14(facts_summary)
        article_15 = self._evaluate_article_15(facts_summary)
        deployment_readiness = self._evaluate_deployment_readiness(
            article_12_checks=checks,
            article_14=article_14,
            article_15=article_15,
            facts_summary=facts_summary,
            dora_article_28_evidence=dora_article_28_evidence,
        )

        report: dict[str, Any] = {
            "eu_ai_act": {
                "regulation": "EU AI Act (Regulation 2024/1689)",
                "article": "12 — Record-Keeping",
                "enforcement_date": "2026-08-02",
                "score": f"{score}/{total}",
                "status": "COMPLIANT" if score == total else "NON_COMPLIANT",
                "checks": checks,
                "related_articles": {
                    "14": article_14,
                    "15": article_15,
                },
            },
            "integrity": integrity,
            "facts_summary": facts_summary,
            "deployment_readiness": deployment_readiness,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project": proj,
            "tenant_id": resolved_tenant_id,
        }

        if include_facts:
            all_facts = self._engine._run_sync(
                self._gather_facts_list(proj, resolved_tenant_id)
            )
            report["facts"] = all_facts

        return report

    def export_evidence_bundle(
        self,
        project: str | None = None,
        *,
        tenant_id: str | None = None,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        """Generate a redacted forensic evidence bundle for offline review."""
        self._ensure_init()
        proj = project or self._default_project
        resolved_tenant_id = tenant_id or self._default_tenant_id

        from cortex.compliance.evidence_bundle import ForensicEvidenceBundleExporter

        compliance_report = self.export_audit(project=proj, tenant_id=resolved_tenant_id)
        exporter = ForensicEvidenceBundleExporter(self._engine._db_path)
        return exporter.build(
            project=proj,
            tenant_id=resolved_tenant_id,
            compliance_report=compliance_report,
            generated_at=generated_at,
        )

    def write_evidence_bundle(
        self,
        output_path: str | Path,
        project: str | None = None,
        *,
        tenant_id: str | None = None,
        generated_at: str | None = None,
    ) -> dict[str, str]:
        """Write a redacted forensic evidence bundle plus SHA-256 sidecar."""
        from cortex.compliance.evidence_bundle import write_evidence_bundle

        bundle = self.export_evidence_bundle(
            project=project,
            tenant_id=tenant_id,
            generated_at=generated_at,
        )
        return write_evidence_bundle(bundle, output_path)

    # ─── Internal helpers ─────────────────────────────────────────

    async def _gather_facts_summary(self, project: str, tenant_id: str) -> dict[str, Any]:
        """Collect fact statistics for the compliance report."""
        async with self._engine.session() as conn:
            # Total facts
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM facts WHERE tenant_id = ? AND project = ?",
                (tenant_id, project),
            )
            row = await cursor.fetchone()
            total = row[0] if row else 0

            # By type
            cursor = await conn.execute(
                "SELECT fact_type, COUNT(*) FROM facts "
                "WHERE tenant_id = ? AND project = ? GROUP BY fact_type",
                (tenant_id, project),
            )
            by_type = {r[0]: r[1] for r in await cursor.fetchall()}

            # Date range
            cursor = await conn.execute(
                "SELECT MIN(created_at), MAX(created_at) FROM facts "
                "WHERE tenant_id = ? AND project = ?",
                (tenant_id, project),
            )
            row = await cursor.fetchone()
            date_range = {
                "earliest": row[0] if row and row[0] else None,
                "latest": row[1] if row and row[1] else None,
            }

            # Active vs deprecated
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM facts "
                "WHERE tenant_id = ? AND project = ? AND valid_until IS NULL",
                (tenant_id, project),
            )
            row = await cursor.fetchone()
            active = row[0] if row else 0

            # Sources (agent traceability)
            cursor = await conn.execute(
                "SELECT DISTINCT source FROM facts "
                "WHERE tenant_id = ? AND project = ? AND source IS NOT NULL",
                (tenant_id, project),
            )
            sources = [r[0] for r in await cursor.fetchall()]

            cursor = await conn.execute(
                "SELECT id, fact_type, metadata FROM facts WHERE tenant_id = ? AND project = ?",
                (tenant_id, project),
            )
            metadata_rows = await cursor.fetchall()
            article_14 = self._summarize_article_14(metadata_rows, tenant_id)
            key_custody = self._summarize_event_source_key_custody(metadata_rows, tenant_id)

            return {
                "total_facts": total,
                "active_facts": active,
                "deprecated_facts": total - active,
                "by_type": by_type,
                "date_range": date_range,
                "sources": sources,
                "article_14": article_14,
                "event_source_key_custody": key_custody,
            }

    async def _gather_facts_list(self, project: str, tenant_id: str) -> list[dict[str, Any]]:
        """Retrieve facts for export (decrypted content omitted for security)."""
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT id, fact_type, source, confidence, created_at, valid_until "
                "FROM facts WHERE tenant_id = ? AND project = ? ORDER BY id",
                (tenant_id, project),
            )
            return [
                {
                    "id": r[0],
                    "fact_type": r[1],
                    "source": r[2],
                    "confidence": r[3],
                    "created_at": r[4],
                    "valid_until": r[5],
                }
                for r in await cursor.fetchall()
            ]

    def _summarize_article_14(self, rows: Iterable[Any], tenant_id: str) -> dict[str, Any]:
        """Summarize human-oversight evidence from decrypted fact metadata."""
        high_risk_decisions = 0
        inline_reviewed = 0
        oversight_events = 0
        reviewed_decision_ids: set[int] = set()
        risk_levels: set[str] = set()
        flags = {
            "risk_metadata_present": False,
            "capacity_limits_visible": False,
            "automation_bias_notice": False,
            "override_available": False,
            "stop_available": False,
        }

        for fact_id, fact_type, raw_meta in rows:
            meta = self._decode_metadata(raw_meta, tenant_id)
            eu_meta = meta.get("eu_ai_act") if isinstance(meta, dict) else None
            if not isinstance(eu_meta, dict):
                continue

            article_14 = eu_meta.get("article_14")
            if fact_type == "decision" and isinstance(article_14, dict):
                risk_level = str(article_14.get("risk_level") or "high").lower()
                risk_levels.add(risk_level)
                if risk_level == "high":
                    high_risk_decisions += 1
                flags["risk_metadata_present"] = True
                for key in (
                    "capacity_limits_visible",
                    "automation_bias_notice",
                    "override_available",
                    "stop_available",
                ):
                    flags[key] = flags[key] or bool(article_14.get(key))
                if article_14.get("human_reviewer_id"):
                    inline_reviewed += 1
                    reviewed_decision_ids.add(int(fact_id))

            if str(eu_meta.get("article")) == "14":
                oversight_events += 1
                decision_id = eu_meta.get("decision_fact_id")
                if isinstance(decision_id, int):
                    reviewed_decision_ids.add(decision_id)
                for key in (
                    "capacity_limits_visible",
                    "automation_bias_notice",
                    "override_available",
                    "stop_available",
                ):
                    flags[key] = flags[key] or bool(eu_meta.get(key))

        reviewed_decisions = max(inline_reviewed, len(reviewed_decision_ids))
        return {
            "high_risk_decisions": high_risk_decisions,
            "reviewed_decisions": reviewed_decisions,
            "oversight_events": oversight_events,
            "risk_levels": sorted(risk_levels),
            **flags,
        }

    def _decode_metadata(self, raw_meta: Any, tenant_id: str) -> dict[str, Any]:
        """Decode plaintext or encrypted fact metadata."""
        if not raw_meta:
            return {}
        from cortex.crypto import get_default_encrypter
        from cortex.crypto.aes import CortexEncrypter

        meta_str = str(raw_meta)
        if meta_str.startswith(CortexEncrypter.PREFIX):
            return get_default_encrypter().decrypt_json(meta_str, tenant_id=tenant_id) or {}
        try:
            import json

            parsed = json.loads(meta_str)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _summarize_event_source_key_custody(
        self, rows: Iterable[Any], tenant_id: str
    ) -> dict[str, Any]:
        """Summarize event-source key custody evidence from fact metadata."""
        events_with_evidence = 0
        hardware_backed = 0
        pilot_only = 0
        external_unverified = 0
        invalid_evidence = 0
        by_custody_model: dict[str, int] = {}
        by_assurance_level: dict[str, int] = {}

        for _, _, raw_meta in rows:
            meta = self._decode_metadata(raw_meta, tenant_id)
            if not isinstance(meta, dict):
                continue
            custody = meta.get("event_source_key_custody")
            if not isinstance(custody, dict):
                continue

            events_with_evidence += 1
            custody_model = str(custody.get("custody_model") or "unknown")
            assurance_level = str(custody.get("assurance_level") or "unknown")
            by_custody_model[custody_model] = by_custody_model.get(custody_model, 0) + 1
            by_assurance_level[assurance_level] = (
                by_assurance_level.get(assurance_level, 0) + 1
            )

            if custody.get("hardware_backed") is True:
                hardware_backed += 1
            if assurance_level == "pilot_only":
                pilot_only += 1
            if custody_model == "external_unverified":
                external_unverified += 1

            declared_hash = custody.get("public_key_sha256")
            agent_hash = meta.get("agent_public_key_sha256")
            if isinstance(declared_hash, str) and isinstance(agent_hash, str):
                invalid_evidence += int(declared_hash != agent_hash)

        return {
            "events_with_evidence": events_with_evidence,
            "hardware_backed": hardware_backed,
            "pilot_only": pilot_only,
            "external_unverified": external_unverified,
            "invalid_evidence": invalid_evidence,
            "by_custody_model": by_custody_model,
            "by_assurance_level": by_assurance_level,
        }

    def _ensure_zk_proof(
        self,
        content: str,
        meta: dict[str, Any],
        *,
        tenant_id: str,
        project: str,
        fact_type: str,
        source: str,
    ) -> None:
        """Attach or validate the Ed25519 proof required for high-risk decisions."""
        from cortex.crypto.keys import ZKSwarmIdentity

        public_key = meta.get("agent_public_key")
        signature = meta.get("zk_proof_signature")
        if public_key or signature:
            if not (isinstance(public_key, str) and isinstance(signature, str)):
                raise ValueError("Both agent_public_key and zk_proof_signature are required")
            public_key_hash = meta.get("agent_public_key_sha256")
            if public_key_hash is not None and public_key_hash != ZKSwarmIdentity.public_key_sha256(
                public_key
            ):
                raise ValueError("Invalid ZK proof public-key fingerprint")
            resolved_public_key_hash = ZKSwarmIdentity.public_key_sha256(public_key)
            scope = str(meta.get("zk_proof_scope") or meta.get("zk_proof_payload") or "")
            if scope == "store_event_v1":
                valid = ZKSwarmIdentity.verify_store_event(
                    tenant_id=tenant_id,
                    project=project,
                    fact_type=fact_type,
                    source=source,
                    content=content,
                    public_key_b64=public_key,
                    signature_b64=signature,
                )
            else:
                valid = ZKSwarmIdentity.verify_payload(content, public_key, signature)
            if not valid:
                raise ValueError("Invalid ZK proof for compliance decision payload")
            meta["zk_proof_algorithm"] = str(meta.get("zk_proof_algorithm") or "Ed25519")
            meta["agent_public_key_sha256"] = resolved_public_key_hash
            self._attach_key_custody_evidence(
                meta,
                public_key_hash=resolved_public_key_hash,
                generated_by_tracker=False,
            )
            return

        meta["agent_public_key"] = self._zk_keypair.public_key_b64
        public_key_hash = ZKSwarmIdentity.public_key_sha256(self._zk_keypair.public_key_b64)
        meta["agent_public_key_sha256"] = public_key_hash
        meta["zk_proof_signature"] = ZKSwarmIdentity.sign_store_event(
            tenant_id=tenant_id,
            project=project,
            fact_type=fact_type,
            source=source,
            content=content,
            private_key_b64=self._zk_keypair.private_key_b64,
        )
        meta["zk_proof_algorithm"] = "Ed25519"
        meta["zk_proof_scope"] = "store_event_v1"
        self._attach_key_custody_evidence(
            meta,
            public_key_hash=public_key_hash,
            generated_by_tracker=True,
        )

    def _attach_key_custody_evidence(
        self,
        meta: dict[str, Any],
        *,
        public_key_hash: str,
        generated_by_tracker: bool,
    ) -> None:
        """Attach source-key custody evidence without overstating assurance."""
        if generated_by_tracker:
            custody = {
                "schema": _EVENT_SOURCE_KEY_CUSTODY_SCHEMA,
                "algorithm": "Ed25519",
                "public_key_sha256": public_key_hash,
                "custody_model": "software_ephemeral",
                "assurance_level": "pilot_only",
                "hardware_backed": False,
                "private_key_exportable": True,
                "managed_by": "ComplianceTracker",
                "rotation_scope": "tracker_instance",
                "attestation_type": "none",
                "production_use": "not_sufficient_for_hsm_required_deployments",
            }
        else:
            raw_custody = meta.get("event_source_key_custody")
            if raw_custody is None:
                custody = {}
            elif isinstance(raw_custody, dict):
                custody = dict(raw_custody)
            else:
                raise ValueError("event_source_key_custody must be an object")

            declared_hash = custody.get("public_key_sha256") or custody.get(
                "agent_public_key_sha256"
            )
            if declared_hash is not None and declared_hash != public_key_hash:
                raise ValueError("event_source_key_custody public-key fingerprint mismatch")

            custody.setdefault("schema", _EVENT_SOURCE_KEY_CUSTODY_SCHEMA)
            custody.setdefault("algorithm", "Ed25519")
            custody["public_key_sha256"] = public_key_hash
            custody.setdefault("custody_model", "external_unverified")
            custody.setdefault("assurance_level", "attestation_required")
            custody.setdefault("hardware_backed", None)
            custody.setdefault("private_key_exportable", None)
            custody.setdefault("managed_by", "external_agent_or_deployer")
            custody.setdefault("attestation_type", "not_provided")
            custody.setdefault("production_use", "requires_deployer_key_custody_attestation")

        meta["event_source_key_custody"] = custody
        meta["event_source_key_custody_status"] = str(custody["assurance_level"])

    def _evaluate_article_12(
        self,
        integrity: dict[str, Any],
        facts_summary: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Evaluate each Article 12 sub-requirement."""
        total = facts_summary.get("total_facts", 0)
        sources = facts_summary.get("sources", [])
        has_dates = facts_summary.get("date_range", {}).get("earliest") is not None

        return {
            "art_12_1_automatic_logging": {
                "description": _ARTICLE_12_CHECKS["art_12_1_automatic_logging"],
                "compliant": total > 0,
                "evidence": f"{total} facts recorded",
            },
            "art_12_2_log_content": {
                "description": _ARTICLE_12_CHECKS["art_12_2_log_content"],
                "compliant": total > 0 and has_dates,
                "evidence": f"Date range: {facts_summary.get('date_range', {})}",
            },
            "art_12_2d_agent_traceability": {
                "description": _ARTICLE_12_CHECKS["art_12_2d_agent_traceability"],
                "compliant": total > 0 and len(sources) > 0,
                "evidence": f"{len(sources)} distinct sources: {sources}",
            },
            "art_12_3_tamper_proof": {
                "description": _ARTICLE_12_CHECKS["art_12_3_tamper_proof"],
                "compliant": integrity.get("valid", False)
                and integrity.get("tx_checked", 0) > 0,
                "evidence": (
                    f"Chain: {integrity.get('tx_checked', 0)} TX verified, "
                    f"{integrity.get('roots_checked', 0)} Merkle roots checked"
                ),
            },
            "art_12_4_periodic_verification": {
                "description": _ARTICLE_12_CHECKS["art_12_4_periodic_verification"],
                "compliant": total > 0 and integrity.get("tx_checked", 0) > 0,
                "evidence": "Integrity verification executed as part of this report",
            },
        }

    def _evaluate_article_14(self, facts_summary: dict[str, Any]) -> dict[str, Any]:
        """Evaluate Article 14 human-oversight evidence from decrypted metadata."""
        oversight = facts_summary.get("article_14", {})
        reviewed = int(oversight.get("reviewed_decisions", 0))
        total_high_risk = int(oversight.get("high_risk_decisions", 0))
        has_review = total_high_risk == 0 or reviewed >= total_high_risk
        no_high_risk = total_high_risk == 0
        checks = {
            "art_14_1_human_machine_interface": {
                "description": _ARTICLE_14_CHECKS["art_14_1_human_machine_interface"],
                "compliant": has_review,
                "evidence": f"{reviewed}/{total_high_risk} high-risk decisions have reviewer evidence",
            },
            "art_14_2_risk_minimisation": {
                "description": _ARTICLE_14_CHECKS["art_14_2_risk_minimisation"],
                "compliant": no_high_risk or bool(oversight.get("risk_metadata_present", False)),
                "evidence": f"risk labels: {oversight.get('risk_levels', [])}",
            },
            "art_14_4a_capacity_limits": {
                "description": _ARTICLE_14_CHECKS["art_14_4a_capacity_limits"],
                "compliant": no_high_risk or bool(oversight.get("capacity_limits_visible", False)),
                "evidence": "capacity/limits visibility flag observed",
            },
            "art_14_4b_automation_bias": {
                "description": _ARTICLE_14_CHECKS["art_14_4b_automation_bias"],
                "compliant": no_high_risk or bool(oversight.get("automation_bias_notice", False)),
                "evidence": "automation-bias notice flag observed",
            },
            "art_14_4d_override": {
                "description": _ARTICLE_14_CHECKS["art_14_4d_override"],
                "compliant": no_high_risk or bool(oversight.get("override_available", False)),
                "evidence": "override capability flag observed",
            },
            "art_14_4e_stop": {
                "description": _ARTICLE_14_CHECKS["art_14_4e_stop"],
                "compliant": no_high_risk or bool(oversight.get("stop_available", False)),
                "evidence": "safe stop capability flag observed",
            },
        }
        score = sum(1 for item in checks.values() if item["compliant"])
        total = len(checks)
        return {
            "article": "14 — Human Oversight",
            "score": f"{score}/{total}",
            "status": "COMPLIANT" if score == total else "NON_COMPLIANT",
            "checks": checks,
        }

    def _evaluate_article_15(self, facts_summary: dict[str, Any]) -> dict[str, Any]:
        """Evaluate adjacent Article 15 source-authentication evidence."""
        custody = facts_summary.get("event_source_key_custody", {})
        if not isinstance(custody, dict):
            custody = {}
        events = int(custody.get("events_with_evidence", 0) or 0)
        hardware_backed = int(custody.get("hardware_backed", 0) or 0)
        pilot_only = int(custody.get("pilot_only", 0) or 0)
        external_unverified = int(custody.get("external_unverified", 0) or 0)
        invalid_evidence = int(custody.get("invalid_evidence", 0) or 0)

        checks = {
            "art_15_source_key_custody": {
                "description": _ARTICLE_15_CHECKS["art_15_source_key_custody"],
                "compliant": events > 0 and invalid_evidence == 0,
                "evidence": f"{events} events include custody evidence; invalid={invalid_evidence}",
            },
            "art_15_hardware_backing": {
                "description": _ARTICLE_15_CHECKS["art_15_hardware_backing"],
                "compliant": events > 0 and hardware_backed == events,
                "evidence": f"{hardware_backed}/{events} event keys marked hardware-backed",
            },
            "art_15_external_attestation": {
                "description": _ARTICLE_15_CHECKS["art_15_external_attestation"],
                "compliant": external_unverified == 0 and events > 0,
                "evidence": f"{external_unverified} externally signed events lack attestation",
            },
        }
        score = sum(1 for item in checks.values() if item["compliant"])
        total = len(checks)
        if score == total:
            status = "COMPLIANT"
        elif invalid_evidence > 0 or events == 0:
            status = "NON_COMPLIANT"
        elif pilot_only > 0 or hardware_backed < events or external_unverified > 0:
            status = "PILOT_ONLY"
        else:
            status = "NON_COMPLIANT"
        return {
            "article": "15 — Accuracy, Robustness, Cybersecurity",
            "score": f"{score}/{total}",
            "status": status,
            "checks": checks,
        }

    def _evaluate_deployment_readiness(
        self,
        *,
        article_12_checks: dict[str, dict[str, Any]],
        article_14: dict[str, Any],
        article_15: dict[str, Any],
        facts_summary: dict[str, Any],
        dora_article_28_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Separate product deployment posture from individual article checks."""
        total_facts = int(facts_summary.get("total_facts", 0) or 0)
        article_12_compliant = all(
            bool(check.get("compliant")) for check in article_12_checks.values()
        )
        article_14_status = str(article_14.get("status") or "UNKNOWN")
        article_15_status = str(article_15.get("status") or "UNKNOWN")
        dora_status = self._normalise_dora_article_28_status(dora_article_28_evidence)

        blockers: list[str] = []
        pilot_controls: list[str] = []
        production_blockers: list[str] = []

        if total_facts <= 0:
            blockers.append("no scoped compliance facts recorded")
        if not article_12_compliant:
            blockers.append("Article 12 record-keeping evidence incomplete")
        if article_14_status != "COMPLIANT":
            blockers.append("Article 14 human-oversight evidence incomplete")
            production_blockers.append("Article 14 human-oversight evidence incomplete")
        if article_15_status == "PILOT_ONLY":
            pilot_controls.append("software-held event-source keys require deployment controls")
            production_blockers.append("Article 15 event-source key custody is pilot-only")
        elif article_15_status != "COMPLIANT":
            blockers.append("Article 15 source-authentication evidence incomplete")
            production_blockers.append("Article 15 source-authentication evidence incomplete")
        if dora_status != "verified_issued":
            production_blockers.append("DORA Article 28 evidence is not verified issued")

        pilot_ready = (
            total_facts > 0
            and article_12_compliant
            and article_14_status == "COMPLIANT"
            and article_15_status in {"COMPLIANT", "PILOT_ONLY"}
        )
        production_ready = (
            pilot_ready
            and article_15_status == "COMPLIANT"
            and dora_status == "verified_issued"
        )

        if not production_blockers and not production_ready:
            production_blockers.extend(blockers)

        return {
            "schema": _DEPLOYMENT_READINESS_SCHEMA,
            "dora_article_28": {
                "status": dora_status,
                "source": (
                    str(dora_article_28_evidence.get("source"))
                    if isinstance(dora_article_28_evidence, dict)
                    and dora_article_28_evidence.get("source")
                    else None
                ),
                "verification_status": (
                    str(dora_article_28_evidence.get("verification_status"))
                    if isinstance(dora_article_28_evidence, dict)
                    and dora_article_28_evidence.get("verification_status")
                    else None
                ),
            },
            "regulated_pilot": {
                "status": "READY_WITH_CONTROLS" if pilot_ready else "NO_GO",
                "blockers": blockers,
                "required_controls": pilot_controls,
            },
            "tier_1_bank_production": {
                "status": "GO" if production_ready else "NO_GO",
                "blockers": production_blockers,
                "required_controls": [
                    "HSM/TPM-backed event-source signing",
                    "deployer key-custody attestation",
                    "signed Article 14 operational workflow evidence",
                    "issued DORA Article 28 contract annex and exit evidence",
                ]
                if not production_ready
                else [],
            },
        }

    @staticmethod
    def _normalise_dora_article_28_status(
        evidence: dict[str, Any] | None,
    ) -> str:
        """Return the only DORA status accepted by production readiness."""
        if not isinstance(evidence, dict):
            return "missing"
        status = str(evidence.get("status") or "missing").lower()
        if status == "verified_issued":
            return "verified_issued"
        if status in {"missing", "draft", "failed", "expired", "revoked", "superseded"}:
            return status
        return "unverified"

    # ─── Lifecycle ────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying engine and database connection."""
        if self._initialized:
            self._engine.close_sync()

    def __enter__(self) -> ComplianceTracker:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
