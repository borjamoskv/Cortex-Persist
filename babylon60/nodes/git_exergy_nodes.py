#!/usr/bin/env python3
"""
cortex/nodes/git_exergy_nodes.py
═══════════════════════════════════════════════════════════════
GIT-EXERGY: 100 Primitivas de Exergía de Git/GitHub
Motor de inyección en el DAG epistémico C5-REAL (Cortex-Persist)
═══════════════════════════════════════════════════════════════
Protocolo: C5-REAL | AX-041 Trazabilidad Criptográfica
Restricción: Zero entropy commits | BFT-compliant
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from babylon60.database.core import connect as db_connect


class Criticality(Enum):
    CRITICAL = "CRÍTICO"
    HIGH = "ALTO"
    MASTERY = "MAESTRÍA"

class ValidationStatus(Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"

class Block(Enum):
    B1_BASE = "B1"
    B2_CAUSAL = "B2"
    B3_AUDIT = "B3"
    B4_CICD = "B4"
    B5_TOPOLOGY = "B5"
    B6_SECURITY = "B6"
    B7_HOOKS = "B7"

BLOCK_METADATA = {
    Block.B1_BASE: {"name": "Operaciones Atómicas Base", "criticality": Criticality.CRITICAL},
    Block.B2_CAUSAL: {"name": "Control Causal (Rebasing/Merge)", "criticality": Criticality.CRITICAL},
    Block.B3_AUDIT: {"name": "Auditoría y Forense (Reflog/Log)", "criticality": Criticality.CRITICAL},
    Block.B4_CICD: {"name": "Automatización CI/CD (Actions)", "criticality": Criticality.HIGH},
    Block.B5_TOPOLOGY: {"name": "Topología de Ramas (Flow/Trunk)", "criticality": Criticality.HIGH},
    Block.B6_SECURITY: {"name": "Seguridad y Firmas (GPG/SSH)", "criticality": Criticality.CRITICAL},
    Block.B7_HOOKS: {"name": "Hooks y Guardianes Termodinámicos", "criticality": Criticality.MASTERY},
}

@dataclass
class GitExergyNode:
    id: str
    index: int
    name: str
    block: str
    block_name: str
    criticality: str
    dependencies: list[str] = field(default_factory=list)
    verification_method: str = ""
    validation_status: str = "PENDING"
    hash: str = ""
    injected_at: str = ""

    def compute_hash(self) -> str:
        payload = f"{self.id}|{self.name}|{self.block}|{','.join(sorted(self.dependencies))}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def __post_init__(self):
        self.hash = self.compute_hash()
        if not self.injected_at:
            self.injected_at = datetime.now(timezone.utc).isoformat()

def _id(n: int) -> str:
    return f"GIT-EXERGY-{n:03d}"

def _deps(*indices: int) -> list[str]:
    return [_id(i) for i in indices]

def build_all_nodes() -> list[GitExergyNode]:
    raw = [
        # B1: BASE
        (1, "git init", "B1", [], "Check .git folder exists"),
        (2, "git add -p", "B1", [1], "Staged deltas isolated"),
        (3, "git commit -m", "B1", [2], "Commit generated with semver"),
        (4, "git status", "B1", [1], "State read cleanly"),
        (5, "git rm --cached", "B1", [2], "Untracked removed from stage"),
        (6, "git diff", "B1", [1], "Entropy visually confirmed"),
        (7, "git diff --staged", "B1", [2], "Staged entropy confirmed"),
        (8, "git restore", "B1", [1], "State reverted to invariant"),
        (9, "git clone", "B1", [], "Remote state replicated locally"),
        (10, "git fetch", "B1", [9], "Remote state synchronized passively"),
        (11, "git pull --rebase", "B1", [10], "Linear integration confirmed"),
        (12, "git push --force-with-lease", "B1", [3,10], "Remote updated safely"),
        (13, "git mv", "B1", [2], "Topological transmuted"),
        (14, "git commit --amend", "B1", [3], "Last commit amended"),
        (15, "git stash", "B1", [1], "State suspended safely"),

        # B2: CAUSAL
        (16, "git rebase -i", "B2", [14], "Interactive rebase complete"),
        (17, "git merge --no-ff", "B2", [19], "Merge commit generated"),
        (18, "git cherry-pick", "B2", [3], "Isolated commit injected"),
        (19, "git branch", "B2", [3], "Branch created"),
        (20, "git checkout -b", "B2", [19], "Flow active on branch"),
        (21, "git rebase --onto", "B2", [16], "Complex graph transplant"),
        (22, "git merge --squash", "B2", [19], "Squash commit generated"),
        (23, "git reset --soft", "B2", [3], "Head detached, staged kept"),
        (24, "git reset --mixed", "B2", [3], "Head detached, stage dropped"),
        (25, "git reset --hard", "B2", [3], "Total entropy annihilation"),
        (26, "git revert", "B2", [3], "Causal inverse committed"),
        (27, "git checkout --ours", "B2", [17], "Conflict resolved internal"),
        (28, "git checkout --theirs", "B2", [17], "Conflict resolved external"),
        (29, "git worktree add", "B2", [9], "Isolated workspace created"),
        (30, "git worktree prune", "B2", [29], "Ghost workspaces destroyed"),

        # B3: AUDIT
        (31, "git reflog", "B3", [25], "State resurrected from reflog"),
        (32, "git log --graph", "B3", [3], "Dimensional tree rendered"),
        (33, "git bisect start", "B3", [3], "Binary search active"),
        (34, "git blame", "B3", [3], "Lineage extracted"),
        (35, "git shortlog -sn", "B3", [3], "Exergy contribution scored"),
        (36, "git log -S", "B3", [3], "String search in history"),
        (37, "git show", "B3", [3], "Atomic commit examined"),
        (38, "git log --stat", "B3", [3], "Volumetric verification"),
        (39, "git log --author", "B3", [3], "Identity isolated logs"),
        (40, "git verify-commit", "B3", [86], "Cryptographic seal verified"),
        (41, "git fsck", "B3", [1], "Graph integrity valid"),
        (42, "git gc", "B3", [41], "Garbage collection executed"),
        (43, "git prune", "B3", [42], "Loose nodes eradicated"),
        (44, "git diff-tree", "B3", [3], "Deep cross analysis done"),
        (45, "git grep", "B3", [1], "Structural regex matched"),

        # B4: CICD
        (46, "GitHub Actions: on.push", "B4", [12], "Primary trigger active"),
        (47, "actions/checkout", "B4", [46], "Repository ingested in VM"),
        (48, "actions/setup-python", "B4", [47], "Runtime prepped"),
        (49, "matrix strategy", "B4", [46], "Parallel dimensional exec"),
        (50, "concurrency group", "B4", [46], "Redundancies suppressed"),
        (51, "workflow_dispatch", "B4", [], "Manual trigger exposed"),
        (52, "secrets.GITHUB_TOKEN", "B4", [46], "Transient auth mapped"),
        (53, "needs: [job]", "B4", [46], "Causal dependency linked"),
        (54, "if: failure()", "B4", [46], "Chaos intercepted"),
        (55, "actions/cache", "B4", [48], "Exergy retained across runs"),
        (56, "run: pytest", "B4", [48], "Empirical validation gate"),
        (57, "run: ruff", "B4", [48], "Stylistic noise annihilated"),
        (58, "artifacts: upload", "B4", [56], "Evidence persisted"),
        (59, "environment: production", "B4", [56], "Critical path blocked"),
        (60, "workflow_call", "B4", [46], "Modular CI reused"),

        # B5: TOPOLOGY
        (61, "main branch", "B5", [1], "Truth trunk active"),
        (62, "feature/*", "B5", [19], "Injection vector active"),
        (63, "fix/*", "B5", [19], "Patch vector active"),
        (64, "release/*", "B5", [19], "Temporal freeze verified"),
        (65, "git branch -d", "B5", [22], "Branch safely pruned"),
        (66, "git branch -D", "B5", [19], "Branch ruthlessly pruned"),
        (67, "git push -u origin", "B5", [12], "Remote graph linked"),
        (68, "git push --delete", "B5", [67], "Remote branch suppressed"),
        (69, "PR (Pull Request)", "B5", [67], "BFT Consensus Portal created"),
        (70, "Draft PR", "B5", [67], "Early observation mode"),
        (71, "CODEOWNERS", "B5", [69], "Jurisdiction mapped"),
        (72, "Branch Protection", "B5", [61], "Thermodynamic shield on"),
        (73, "Require Linear History", "B5", [72], "Merge chaos forbidden"),
        (74, "Require Status Checks", "B5", [72], "Mandatory CI gate"),
        (75, "Squash merging", "B5", [69], "Crystallized to DAG"),

        # B6: SECURITY
        (76, "git config commit.gpgsign true", "B6", [1], "Mandatory sign config"),
        (77, "gpg --gen-key", "B6", [], "Sovereign entity created"),
        (78, "ssh-keygen -t ed25519", "B6", [], "Elliptic transport key gen"),
        (79, "git crypt", "B6", [1], "Local encryption active"),
        (80, ".gitignore", "B6", [1], "Passive noise barrier set"),
        (81, ".gitattributes", "B6", [1], "Logical normalization LFS/CRLF"),
        (82, "git filter-repo", "B6", [1], "Deep exfiltration surgery"),
        (83, "git config --global core.autocrlf", "B6", [], "Line invariance locked"),
        (84, "Dependabot alerts", "B6", [61], "Automated scanning active"),
        (85, "Secret Scanning", "B6", [61], "Entropy leaks detected"),
        (86, "git commit -S", "B6", [3,76], "Atomic commit signed"),
        (87, "git tag -s", "B6", [86], "Cryptographic perennial seal"),
        (88, "git remote set-url ssh", "B6", [9], "HTTPS transport closed"),
        (89, "GH Advanced Security", "B6", [61], "BFT Matrix activated"),
        (90, "git submodule update --init", "B6", [9], "Physical isolation mapped"),

        # B7: HOOKS
        (91, "pre-commit", "B7", [1], "Primary gatekeeper installed"),
        (92, "pre-push", "B7", [91], "Final integrity validation"),
        (93, "commit-msg", "B7", [91], "Structural linter active"),
        (94, "post-checkout", "B7", [91], "Active environment restored"),
        (95, "post-merge", "B7", [91], "Dependencies adjusted"),
        (96, ".git/info/exclude", "B7", [1], "Dynamic local quarantine"),
        (97, "core.hooksPath", "B7", [91], "Gatekeepers centralized"),
        (98, "git rebase --exec", "B7", [16], "DAG resilience test"),
        (99, "husky", "B7", [91], "Interface hook orchestrator"),
        (100, "lint-staged", "B7", [99], "Minimized thermodynamic sweep"),
    ]

    nodes = []
    for idx, name, block_id, deps, verif in raw:
        block_enum = [b for b in Block if b.value == block_id][0]
        meta = BLOCK_METADATA[block_enum]
        node = GitExergyNode(
            id=_id(idx),
            index=idx,
            name=name,
            block=block_id,
            block_name=meta["name"],
            criticality=meta["criticality"].value,
            dependencies=_deps(*deps),
            verification_method=verif,
        )
        nodes.append(node)

    return nodes

class CortexPersist:
    def __init__(self, db_path: str = "babylon60.db"):
        self.db_path = Path(db_path)
        self.conn = db_connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS git_exergy_nodes (
                id TEXT PRIMARY KEY,
                idx INTEGER NOT NULL,
                name TEXT NOT NULL,
                block TEXT NOT NULL,
                block_name TEXT NOT NULL,
                criticality TEXT NOT NULL,
                dependencies TEXT NOT NULL,
                verification_method TEXT NOT NULL,
                validation_status TEXT NOT NULL DEFAULT 'PENDING',
                hash TEXT NOT NULL,
                injected_at TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def inject_nodes(self, nodes: list[GitExergyNode]) -> dict:
        injected, updated = 0, 0
        for node in nodes:
            existing = self.conn.execute(
                "SELECT hash FROM git_exergy_nodes WHERE id = ?", (node.id,)
            ).fetchone()

            if existing is None:
                self.conn.execute("""
                    INSERT INTO git_exergy_nodes
                    (id, idx, name, block, block_name, criticality,
                     dependencies, verification_method, validation_status,
                     hash, injected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node.id, node.index, node.name, node.block,
                    node.block_name, node.criticality,
                    json.dumps(node.dependencies),
                    node.verification_method, node.validation_status,
                    node.hash, node.injected_at
                ))
                injected += 1
            elif existing[0] != node.hash:
                self.conn.execute("""
                    UPDATE git_exergy_nodes
                    SET name=?, block=?, block_name=?, criticality=?,
                        dependencies=?, verification_method=?,
                        hash=?, injected_at=?
                    WHERE id=?
                """, (
                    node.name, node.block, node.block_name,
                    node.criticality, json.dumps(node.dependencies),
                    node.verification_method, node.hash,
                    node.injected_at, node.id
                ))
                updated += 1

        self.conn.commit()
        return {"injected": injected, "updated": updated, "total": len(nodes)}

    def close(self):
        self.conn.close()

def main():
    print("=" * 70)
    print("🐙 GIT-EXERGY: Inyección de 100 Primitivas en C5-REAL DAG")
    print("=" * 70)

    nodes = build_all_nodes()
    print(f"[1/2] Construidas {len(nodes)} primitivas de Git Exergy.")

    db = CortexPersist("babylon60.db")
    result = db.inject_nodes(nodes)
    print(f"[2/2] Inyección DB completada: Nuevos={result['injected']} | Actualizados={result['updated']}")
    db.close()
    
    print("✅ SISTEMA EXERGÉTICO PREPARADO")

if __name__ == "__main__":
    main()
