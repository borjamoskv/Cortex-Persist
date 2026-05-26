"""
CORTEX JIT Compiled Skill: Sortu
Description: JIT skill compiler — Sovereign 500 Cold Forge
"""

import json
import logging


class SortuSkill:
    def __init__(self):
        self.name = "Sortu"
        self.description = "JIT skill compiler \u2014 Sovereign 500 Cold Forge"
        self.instructions = "# SORTU-\u03a9 v12.2.0 \u2014 Sovereign 500 Cold Forge\n\nJIT skill compiler under zero-trust policy. Forges new skills only when mechanically justified, cryptographically registered, and thermodynamically profitable.\n\n> **v12.2.0 Upgrades:** Deterministic Biopsy (zero `random`), GraphStore ontological anchoring, AST-based structural overlap detection.\n\n---\n\n## Objective\n\nForge a new skill if and only if:\n\n1. A **causal gap** exists that no current skill closes.\n2. The **tripartite package** is complete: `SKILL.md` + `schema.json` + `verify_<skill>.py`.\n3. **Mechanical verification** passes (contract + hashes).\n4. The skill is **registered in the CORTEX Ledger** with cryptographic hash.\n5. **Net exergy** (compound yield \u2212 entropy cost) is positive.\n\nIf any condition fails, the forge aborts with a typed reason.\n\n---\n\n## Required Artifacts (Tripartite Package)\n\n| File | Purpose | Required |\n|:---|:---|:---:|\n| `SKILL.md` | Narrative, commands, operational contract | \u2713 |\n| `schema.json` | JSON Schema I/O contract (draft 2020-12) | \u2713 |\n| `verify_<skill>.py` | Deterministic mechanical verifier | \u2713 |\n\nA skill directory missing any artifact is considered **code ghost in latency** and will not be persisted.\n\n---\n\n## Commands\n\n### `/sortu [intent]`\n\nStructural JIT forge. Executes the full pipeline and aborts on any gate failure.\n\n### `/sortu-verify [skill_name]`\n\nMechanical validation. Runs `verify_<skill>.py` against the tripartite package.\n\n### `/sortu-yield [skill_name|target]`\n\nSurvival audit. Evaluates compound yield vs. entropy cost. Executes TTL purge sentences.\n\n---\n\n## State Machine\n\n```\nDRAFT \u2192 AUDITED \u2192 FORGED \u2192 VERIFIED \u2192 LINKED \u2192 LEDGERED \u2192 ACTIVE\n                                                              \u2502\n                                                              \u251c\u2500\u2500 (TTL expired) \u2192 QUARANTINED \u2192 TOMBSTONED \u2192 PURGED\n                                                              \u2502\n                                                              \u2514\u2500\u2500 (any gate failure) \u2192 ABORTED\n```\n\n| State | Entry Condition |\n|:---|:---|\n| `DRAFT` | Intent received |\n| `AUDITED` | Semantic overlap check passed, causal gap confirmed |\n| `FORGED` | Tripartite package generated |\n| `VERIFIED` | `verify_<skill>.py` returns `PASS` |\n| `LINKED` | Causal DAG edge created to parent |\n| `LEDGERED` | Cryptographic hash persisted to CORTEX Ledger |\n| `ACTIVE` | TTL armed, yield tracking begins |\n| `QUARANTINED` | TTL expired or negative net exergy detected |\n| `TOMBSTONED` | Quarantine period expired without recovery |\n| `PURGED` | Artifacts removed from active rotation |\n| `ABORTED` | Any gate failure during forge pipeline |\n\n---\n\n## Abort Reasons\n\n| Code | Trigger |\n|:---|:---|\n| `REDUNDANT_COMPUTATION` | Semantic overlap > threshold AND causal gap insufficient |\n| `MISSING_TRIPARTITE` | Incomplete artifact package |\n| `CONTRACT_VERIFICATION_FAILED` | `verify_<skill>.py` returns `FAIL` |\n| `EPISTEMIC_DRIFT` | Generated artifacts diverge from intent beyond tolerance |\n| `NEGATIVE_NET_EXERGY` | Compound yield < entropy cost |\n| `LEDGER_WRITE_FAILED` | CORTEX Ledger persistence error |\n| `INVALID_CAUSAL_PARENT` | Referenced parent does not exist in DAG |\n\n---\n\n## Forge Pipeline\n\n```\nintent\n  \u2192 [0] CORTEX Audit: AST structural overlap (Jaccard) + causal gap scoring\n  \u2192 [1] Cold Forge: local-first generation (remote fallback with confidence penalty)\n  \u2192 [2] Tripartite generation: SKILL.md + schema.json + verify_<skill>.py\n  \u2192 [3] Mechanical verification: run verify_<skill>.py\n  \u2192 [4] GraphStore linking: inject Skill node + DEPENDS_ON / GOVERNED_BY edges\n  \u2192 [5] Sovereign closure: final contract review\n  \u2192 [6] Ledger store: SHA-256 hash of package \u2192 cortex store\n  \u2192 [7] Biopsy: deterministic compound yield (\u03a9\u2081\u2081) vs. entropy cost (\u03a9\u2081\u2083)\n  \u2192 [8] TTL armed: death-clock starts\n  \u2192 [9] Crystallization: skill enters ACTIVE rotation\n```\n\n---\n\n## Economics\n\n### Compound Yield (\u03a9\u2081\u2081)\n\n```\nYield = \u03a3 (H_i \u00d7 (1 + r)^d_i)\n```\n\nWhere `H_i` = linear hours saved per invocation, `r` = reuse coefficient (default 0.15), `d_i` = chain depth from causal DAG.\n\n### Net Exergy\n\n```\nNet_Exergy = Yield - Entropy_Cost\n```\n\nEntropy cost sources: maintenance minutes, verification failures, dependency weight, token cost.\n\n```\nIF Net_Exergy < 0 \u2192 QUARANTINE\n```\n\n---\n\n## Cold Forge Policy\n\n| Priority | Source | Confidence Impact |\n|:---|:---|:---|\n| 1 | Local model (frontier tier) | No penalty |\n| 2 | Remote model (frontier tier) | \u22121 confidence level on generated artifacts |\n| 3 | Remote model (non-frontier) | **ABORT** \u2014 violates Rule 1.3 |\n\nIf no local model is available, remote frontier is permitted with explicit confidence downgrade logged to ledger.\n\n---\n\n## Operational References\n\n- **Full policy (states, TTL, thresholds, redundancy)**: [`policy.yaml`](policy.yaml)\n- **I/O contract**: [`schema.json`](schema.json)\n- **Tripartite verifier**: [`verify_sortu.py`](verify_sortu.py)\n- **Yield diagnostics**: [`biopsy_report.py`](biopsy_report.py)\n- **Capability genome**: [`genome.yaml`](genome.yaml)\n"

    def get_system_prompt(self):
        return self.instructions

    def execute(self, payload: dict) -> dict:
        """
        O(1) execution wrapper.
        In Cycle 1 (MCP), this will bind via API to Cortex Swarm.
        """
        logging.info(f"[{self.name}] Executing logic...")
        # A wrapper returning the prompt context for Frontier Models
        # or executing underlying local hooks if defined.
        return {
            "status": "success",
            "skill": self.name,
            "injected_knowledge_tokens": len(self.instructions.split()),
            "yield_impact": "O(1) Execution",
            "extracted_payload": payload,
        }
