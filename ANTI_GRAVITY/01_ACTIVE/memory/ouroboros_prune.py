#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Ouroboros Thermodynamic Pruning Engine v2.0

Full lifecycle manager for the CORTEX Knowledge Graph's entropic decay.
Implements the Fact State Lifecycle: ACTIVE → WARM → COLD → TOMBSTONED
with topological barrier protection, quadrant transitions, exergy score
recalculation, and dry-run safety mode.

Architecture:
    1. Scan all non-C5, non-tombstoned facts
    2. Compute exponential decay: exergy = 0.5^(age / half_life)
    3. Protect facts with C5 descendants (topological barrier)
    4. Transition surviving facts through storage tiers (HOT → WARM → COLD)
    5. Tombstone facts below MIN_EXERGY_THRESHOLD
    6. Update exergy_score on all scanned facts for real-time dashboards
    7. Emit statistics

Axioms: Ω2 (Entropic Asymmetry), AX-047 (Anti-Limerence)
"""

import argparse
import json
import logging
import math
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from cortex.engine.semantic_collapse import collapse_eligible, kolmogorov_approx, semantic_collapse, compute_ncd

# ─── Thermodynamic Constants ─────────────────────────────────────────
MIN_EXERGY_THRESHOLD = 0.125  # 3 half-lives → tombstone
WARM_THRESHOLD = 0.50  # 1 half-life  → HOT → WARM
COLD_THRESHOLD = 0.25  # 2 half-lives → WARM → COLD


# setup_cortex_logging()
logger = logging.getLogger("ouroboros_prune")


# ─── Statistics ──────────────────────────────────────────────────────


@dataclass
class PurgeCycleStats:
    """Tracks results of a single Ouroboros cycle."""

    total_scanned: int = 0
    tombstoned: int = 0
    transitioned_warm: int = 0
    transitioned_cold: int = 0
    protected_by_topology: int = 0
    exergy_scores_updated: int = 0
    semantic_collapses: int = 0
    distilled_facts: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_scanned": self.total_scanned,
            "tombstoned": self.tombstoned,
            "transitioned_warm": self.transitioned_warm,
            "transitioned_cold": self.transitioned_cold,
            "protected_by_topology": self.protected_by_topology,
            "exergy_scores_updated": self.exergy_scores_updated,
            "semantic_collapses": self.semantic_collapses,
            "distilled_facts": self.distilled_facts,
            "errors": self.errors,
        }


# ─── Core Engine ─────────────────────────────────────────────────────


def _build_topological_barrier(conn: sqlite3.Connection) -> set[int]:
    """Build set of fact IDs that are ancestors of any live C5 node.

    This performs a recursive upward traversal from every C5 fact,
    collecting all ancestor IDs via parent_id links. These ancestors
    are structurally protected from thermal death.
    """
    cursor = conn.cursor()

    # Seed: all live C5 facts with a parent
    cursor.execute(
        "SELECT id, parent_id FROM facts "
        "WHERE confidence = 'C5' AND is_tombstoned = 0 AND parent_id IS NOT NULL"
    )
    c5_rows = cursor.fetchall()

    protected: set[int] = set()
    frontier: set[int] = set()

    for row in c5_rows:
        if row[1] is not None:
            frontier.add(row[1])

    # BFS upward through parent_id chain
    while frontier:
        protected |= frontier
        placeholders = ",".join("?" for _ in frontier)
        cursor.execute(
            f"SELECT id, parent_id FROM facts "
            f"WHERE id IN ({placeholders}) AND parent_id IS NOT NULL AND is_tombstoned = 0",
            list(frontier),
        )
        next_frontier: set[int] = set()
        for row in cursor.fetchall():
            parent = row[1]
            if parent is not None and parent not in protected:
                next_frontier.add(parent)
        frontier = next_frontier

    return protected


def execute_thermal_purge(
    db_path: str = "~/.cortex/cortex.db",
    *,
    dry_run: bool = False,
    json_output: bool = False,
    enable_semantic_collapse: bool = False,
) -> PurgeCycleStats:
    """Execute the Ouroboros thermodynamic pruning cycle.

    Args:
        db_path: Path to the CORTEX SQLite database.
        dry_run: If True, compute and report but don't mutate state.
        json_output: If True, emit machine-readable JSON instead of logs.

    Returns:
        PurgeCycleStats with full cycle telemetry.
    """
    stats = PurgeCycleStats()
    db_file = Path(db_path).expanduser()

    if not db_file.exists():
        stats.errors.append(f"Database not found at {db_file}")
        logger.error("Database not found at %s", db_file)
        return stats

    mode_label = "DRY-RUN" if dry_run else "C5-REAL"
    logger.info("Igniting Ouroboros Thermal Purge [%s]...", mode_label)

    try:
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Phase 0: Build topological barrier (recursive ancestor protection)
            protected_ids = _build_topological_barrier(conn)
            if protected_ids:
                logger.info(
                    "Topological Barrier: %d ancestor nodes protected by C5 lineage.",
                    len(protected_ids),
                )

            # Phase 1: Scan all prunable candidates
            cursor.execute("PRAGMA table_info(facts)")
            columns = {r["name"] for r in cursor.fetchall()}
            meta_col = "metadata" if "metadata" in columns else ("meta" if "meta" in columns else None)

            cols_to_select = ["id", "content", "confidence", "parent_id", "created_at", "decay_half_life", "quadrant", "storage_tier", "exergy_score"]
            if "access_count" in columns:
                cols_to_select.append("access_count")
            if meta_col:
                cols_to_select.append(meta_col)
                
            select_cols = ", ".join(cols_to_select)

            sql_find = f"""
                SELECT {select_cols},
                       ((strftime('%s', 'now') - strftime('%s', created_at)) / 86400.0) as age_days
                FROM facts
                WHERE confidence != 'C5'
                  AND is_tombstoned = 0
            """
            cursor.execute(sql_find)
            rows = cursor.fetchall()
            stats.total_scanned = len(rows)

            tombstone_ids: list[int] = []
            tombstone_rows: list[sqlite3.Row] = []
            warm_ids: list[int] = []
            cold_ids: list[int] = []
            exergy_updates: list[tuple[float, int]] = []

            for row in rows:
                fact_id = row["id"]
                age_days = float(row["age_days"]) if row["age_days"] else 0.0
                half_life = (
                    float(row["decay_half_life"]) if row["decay_half_life"] is not None else 30.0
                )
                current_tier = row["storage_tier"] or "HOT"
                access_count = int(row["access_count"]) if "access_count" in columns and row["access_count"] is not None else 0

                origin_type = "agent_scratchpad"
                locked_floor = 0.0
                if meta_col and row[meta_col]:
                    try:
                        # Try to parse if plaintext JSON
                        meta = json.loads(row[meta_col])
                        origin_type = meta.get("origin_type", origin_type)
                        locked_floor = meta.get("locked_at_floor", 0.0)
                    except Exception:
                        pass
                
                from cortex.engine.immunity.origin_policy import get_policy
                policy = get_policy(origin_type)
                floor = max(policy.criticality_floor, locked_floor)

                # Compute exergy (exponential decay + Hebbian Multiplier)
                if half_life <= 0:
                    exergy = 0.0
                else:
                    decay_factor = 0.5 ** (age_days / half_life)
                    hebbian_multiplier = 1.0 + (math.log10(access_count + 1) * 1.0)
                    exergy = min(decay_factor * hebbian_multiplier, 1.0)
                    exergy = max(exergy, floor)

                # Always update exergy_score for dashboards
                exergy_updates.append((exergy, fact_id))

                # Check topological barrier
                if fact_id in protected_ids:
                    stats.protected_by_topology += 1
                    continue

                # Classify by thermodynamic tier
                if exergy < MIN_EXERGY_THRESHOLD:
                    tombstone_ids.append(fact_id)
                    tombstone_rows.append(row)
                    if not json_output:
                        logger.info(
                            "☠ Thermal Death: Fact %d (Age: %.1fd, T½: %.1fd, Exergy: %.4f)",
                            fact_id,
                            age_days,
                            half_life,
                            exergy,
                        )
                elif exergy < COLD_THRESHOLD and current_tier != "COLD":
                    cold_ids.append(fact_id)
                elif exergy < WARM_THRESHOLD and current_tier == "HOT":
                    warm_ids.append(fact_id)

            # Phase 2: Apply mutations (unless dry-run)
            if not dry_run:
                # Phase 1.5: Kolmogorov Semantic Collapse / AST Distillation for C4-SIM tombstone candidates
                if tombstone_rows:
                    python_candidates = []
                    text_candidates = []
                    
                    for r in tombstone_rows:
                        # Ignore already C5 facts
                        if r["confidence"] == "C5":
                            continue
                        
                        content = r["content"]
                        if not content or not content.strip():
                            continue
                            
                        # Determine if content is Python
                        is_python = False
                        try:
                            import ast
                            ast.parse(content)
                            is_python = True
                        except Exception:
                            pass
                            
                        if is_python:
                            python_candidates.append(r)
                        else:
                            text_candidates.append(r)
                    
                    # 1. Distill Python code using AST Projector
                    try:
                        import sys
                        from pathlib import Path as DistillPath
                        root_path = DistillPath(__file__).resolve().parent.parent
                        if str(root_path) not in sys.path:
                            sys.path.insert(0, str(root_path))
                        from cortex_ast_projector import project_ast
                    except Exception as e:
                        logger.warning("Failed to import project_ast: %s. Falling back to text distillation.", e)
                        project_ast = None
                        
                    for rc in python_candidates:
                        p_content = rc["content"]
                        parent_id = rc["parent_id"]
                        
                        projected_code = None
                        if project_ast:
                            try:
                                projected_code = project_ast(p_content, [])
                            except Exception as e:
                                logger.info("AST validation failed for fact %d (falling back to text): %s", rc["id"], e)
                        
                        if projected_code and len(projected_code.strip()) > 0:
                            distilled_content = projected_code
                            z_size = kolmogorov_approx(distilled_content)
                            meta_dict = {
                                "origin_type": "saga_decision",
                                "distilled_from": [rc["id"]],
                                "kolmogorov_complexity": z_size,
                                "distillation_method": "ast_projector",
                                "reality_level": "C5-REAL"
                            }
                            
                            meta_json = json.dumps(meta_dict) if meta_col else None
                            insert_cols = "content, confidence, parent_id, quadrant, storage_tier, exergy_score, kinetic_mass"
                            insert_vals = [distilled_content, "C5", parent_id, "ACTIVE", "HOT", 1.0, 1.0]
                            if meta_col:
                                insert_cols += f", {meta_col}"
                                insert_vals.append(meta_json)
                                
                            placeholders = ",".join("?" for _ in insert_vals)
                            cursor.execute(
                                f"INSERT INTO facts ({insert_cols}) VALUES ({placeholders})",
                                insert_vals
                            )
                            stats.distilled_facts += 1
                            logger.info("Distilled Python Fact %d to structural C5-REAL skeleton.", rc["id"])
                        else:
                            text_candidates.append(rc)
                    
                    # 2. Distill and Fuse Text candidates using Zlib NCD
                    fused_groups = []
                    for tc in text_candidates:
                        added_to_group = False
                        for group in fused_groups:
                            lead = group[0]
                            ncd = compute_ncd(tc["content"], lead["content"])
                            if ncd < 0.15:
                                group.append(tc)
                                added_to_group = True
                                break
                        if not added_to_group:
                            fused_groups.append([tc])
                    
                    for group in fused_groups:
                        if len(group) == 1:
                            tc = group[0]
                            z_size = kolmogorov_approx(tc["content"])
                            distilled_content = f"# Distilled Primitive [Kolmogorov: {z_size:.1f}]\n# Source Fact: {tc['id']}\n{tc['content']}"
                            parent_id = tc["parent_id"]
                            source_ids = [tc["id"]]
                        else:
                            sorted_group = sorted(group, key=lambda x: float(x["exergy_score"] or 0.0), reverse=True)
                            winner = sorted_group[0]
                            source_ids = [x["id"] for x in group]
                            
                            merged_lines = [f"# Fused Semantic Primitive [Group Size: {len(group)}]"]
                            merged_lines.append(f"# Winner Fact ID: {winner['id']}")
                            merged_lines.append(f"# Subsumed IDs: {', '.join(str(x['id']) for x in sorted_group[1:])}")
                            merged_lines.append(winner["content"])
                            distilled_content = "\n".join(merged_lines)
                            z_size = kolmogorov_approx(distilled_content)
                            parent_id = winner["parent_id"]
                            
                        meta_dict = {
                            "origin_type": "saga_decision",
                            "distilled_from": source_ids,
                            "kolmogorov_complexity": z_size,
                            "distillation_method": "kolmogorov_semantic_collapse",
                            "reality_level": "C5-REAL"
                        }
                        meta_json = json.dumps(meta_dict) if meta_col else None
                        insert_cols = "content, confidence, parent_id, quadrant, storage_tier, exergy_score, kinetic_mass"
                        insert_vals = [distilled_content, "C5", parent_id, "ACTIVE", "HOT", 1.0, 1.0]
                        if meta_col:
                            insert_cols += f", {meta_col}"
                            insert_vals.append(meta_json)
                            
                        placeholders = ",".join("?" for _ in insert_vals)
                        cursor.execute(
                            f"INSERT INTO facts ({insert_cols}) VALUES ({placeholders})",
                            insert_vals
                        )
                        stats.distilled_facts += 1
                        logger.info("Fused/Distilled text group %s into C5-REAL primitive.", source_ids)

                # Tombstone
                if tombstone_ids:
                    placeholders = ",".join("?" for _ in tombstone_ids)
                    cursor.execute(
                        f"UPDATE facts SET is_tombstoned = 1, quadrant = 'VOID', "
                        f"storage_tier = 'VOID', updated_at = datetime('now') "
                        f"WHERE id IN ({placeholders})",
                        tombstone_ids,
                    )

                # Transition to WARM
                if warm_ids:
                    placeholders = ",".join("?" for _ in warm_ids)
                    cursor.execute(
                        f"UPDATE facts SET storage_tier = 'WARM', "
                        f"updated_at = datetime('now') "
                        f"WHERE id IN ({placeholders})",
                        warm_ids,
                    )

                # Transition to COLD
                if cold_ids:
                    placeholders = ",".join("?" for _ in cold_ids)
                    cursor.execute(
                        f"UPDATE facts SET storage_tier = 'COLD', "
                        f"quadrant = 'ARCHIVE', updated_at = datetime('now') "
                        f"WHERE id IN ({placeholders})",
                        cold_ids,
                    )

                # Update exergy scores for all scanned facts
                if exergy_updates:
                    cursor.executemany(
                        "UPDATE facts SET exergy_score = ? WHERE id = ?",
                        exergy_updates,
                    )

                conn.commit()

            stats.tombstoned = len(tombstone_ids)
            stats.transitioned_warm = len(warm_ids)
            stats.transitioned_cold = len(cold_ids)
            stats.exergy_scores_updated = len(exergy_updates)

            # Phase 3: Semantic Pruning (Zlib NCD)
            if enable_semantic_collapse:
                cursor.execute("""
                    SELECT id, content, exergy_score 
                    FROM facts 
                    WHERE is_tombstoned = 0 AND content IS NOT NULL
                """)
                live_facts = cursor.fetchall()
                
                # Compute Kolmogorov Approximation and bucket
                # Using a 10% sliding window over sorted z_sizes
                z_facts = []
                for f in live_facts:
                    content = f["content"]
                    if not content: continue
                    exergy = float(f["exergy_score"] or 1.0)
                    z_size = kolmogorov_approx(content)
                    if z_size > 0.0:
                        z_facts.append((f["id"], content, exergy, z_size))
                        
                z_facts.sort(key=lambda x: x[3])
                collapsed_losers = set()
                
                for i in range(len(z_facts)):
                    id_a, content_a, exergy_a, z_a = z_facts[i]
                    if id_a in collapsed_losers: continue
                    
                    # Scan forward within 10% z_size tolerance
                    for j in range(i + 1, len(z_facts)):
                        id_b, content_b, exergy_b, z_b = z_facts[j]
                        if id_b in collapsed_losers: continue
                        
                        if (z_b - z_a) / z_a > 0.10: 
                            break # Exceeded 10% size difference bucket
                            
                        # NCD and mass tolerance check
                        if collapse_eligible(content_a, content_b, exergy_a, exergy_b, threshold=0.15, mass_tolerance=0.15):
                            res = semantic_collapse(str(id_a), content_a, exergy_a, str(id_b), content_b, exergy_b)
                            winner_id = int(res["winner"])
                            loser_id = id_b if winner_id == id_a else id_a
                            
                            collapsed_losers.add(loser_id)
                            stats.semantic_collapses += 1
                            
                            if not dry_run:
                                cursor.execute(
                                    "UPDATE facts SET is_tombstoned = 1, quadrant = 'VOID', storage_tier = 'VOID', updated_at = datetime('now') WHERE id = ?",
                                    (loser_id,)
                                )
                                cursor.execute(
                                    "UPDATE facts SET exergy_score = ? WHERE id = ?",
                                    (res["kinetic_mass"], winner_id)
                                )
                                logger.info("Semantic Collapse: Fact %d absorbed by Fact %d (NCD Redundancy)", loser_id, winner_id)
                            break # Move to next outer node
                
                if not dry_run and stats.semantic_collapses > 0:
                    conn.commit()

            # Phase 4: Report
            if json_output:
                print(json.dumps(stats.to_dict(), indent=2))
            else:
                logger.info("─── Ouroboros Cycle Complete [%s] ───", mode_label)
                logger.info("  Scanned:              %d", stats.total_scanned)
                logger.info("  Tombstoned (VOID):    %d", stats.tombstoned)
                logger.info("  Transitioned → WARM:  %d", stats.transitioned_warm)
                logger.info("  Transitioned → COLD:  %d", stats.transitioned_cold)
                logger.info("  Semantic Collapses:   %d", stats.semantic_collapses)
                logger.info("  Distilled (C5-REAL):  %d", stats.distilled_facts)
                logger.info("  Protected (Topology): %d", stats.protected_by_topology)
                logger.info("  Exergy Scores Updated:%d", stats.exergy_scores_updated)

    except sqlite3.Error as e:
        msg = f"Ouroboros encountered a temporal distortion: {e}"
        stats.errors.append(msg)
        logger.error(msg)

    return stats


# ── Graph DB Protocol (duck-typed, no hard dependency) ───────────────────────

@runtime_checkable
class GraphDB(Protocol):
    def get_node(self, node_id: str) -> "FactNode": ...
    def update_node(self, node: "FactNode") -> None: ...
    def get_ancestors(self, node_id: str) -> list[str]: ...


# ── FactNode ─────────────────────────────────────────────────────────────────

BASE_DECAY_HALF_LIFE_DAYS: float = 30.0
HEBBIAN_BOOST_PER_ACCESS: float = 0.15
HEBBIAN_DECAY_HALF_LIFE_DAYS: float = 7.0
MAX_KINETIC_MULTIPLIER: float = 2.0

@dataclass
class FactNode:
    node_id: str
    created_at: float
    last_accessed_at: float
    decay_half_life: float = BASE_DECAY_HALF_LIFE_DAYS
    kinetic_mass: float = 1.0
    last_boosted_at: Optional[float] = None
    access_count: int = 0
    classification: str = "C3"
    is_tombstoned: bool = False
    causal_ancestors: list[str] = field(default_factory=list)
    origin_type: str = "agent_scratchpad"


# ── Exergy Engine ─────────────────────────────────────────────────────────────

def _base_exergy(node: FactNode, now: float) -> float:
    age_days = (now - node.created_at) / 86400.0
    return math.pow(0.5, age_days / node.decay_half_life)


def _kinetic_effective(node: FactNode, now: float) -> float:
    if node.last_boosted_at is None:
        return 1.0
    boost_age_days = (now - node.last_boosted_at) / 86400.0
    decay = math.pow(0.5, boost_age_days / HEBBIAN_DECAY_HALF_LIFE_DAYS)
    return max(1.0, 1.0 + (node.kinetic_mass - 1.0) * decay)


def compute_exergy(node: FactNode, now: Optional[float] = None) -> float:
    t = now or time.time()
    base = _base_exergy(node, t)
    kinetic = _kinetic_effective(node, t)
    # Cap is relative to base: dying nodes cannot be zombie-resurrected
    return min(base * kinetic, MAX_KINETIC_MULTIPLIER * base)


def classify_thermal(exergy: float) -> str:
    if exergy > 0.50:   return "HOT"
    if exergy > 0.25:   return "WARM"
    if exergy > MIN_EXERGY_THRESHOLD: return "COLD"
    return "VOID"


# ── Hebbian Reinforcement ─────────────────────────────────────────────────────

def hebbian_reinforce(node: FactNode, now: Optional[float] = None, depth: int = 0) -> tuple[FactNode, float]:
    """
    Depth-attenuated Hebbian reinforcement.
    Energy decays exponentially with topological distance:
    E(d) = E0 * (0.85 ** d)
    This enforces locality and prevents semantic inflation.

    LTP: invoked ONLY from consolidate_retrieval_graph.
    Never from semantic router — prevents latent space poisoning.
    """
    from cortex.engine.immunity.origin_policy import get_policy

    t = now or time.time()
    node.last_accessed_at = t
    node.access_count += 1
    
    policy = get_policy(node.origin_type)
    delta_injected = 0.0
    if policy.hebbiano_eligible:
        node.last_boosted_at = t
        attenuation_factor = 0.85 ** depth
        boost = HEBBIAN_BOOST_PER_ACCESS * attenuation_factor
        
        old_mass = node.kinetic_mass
        node.kinetic_mass = min(
            node.kinetic_mass + boost,
            MAX_KINETIC_MULTIPLIER
        )
        delta_injected = node.kinetic_mass - old_mass
        
    return node, delta_injected


# ── Causal BFS Consolidation ──────────────────────────────────────────────────

def consolidate_retrieval_graph(
    target_node: FactNode,
    graph_db: GraphDB,
    now: Optional[float] = None,
    max_depth: int = 32,        # Circuit breaker: strict CORTEX depth limit
) -> dict[str, float]:
    """
    Traverses the KRGS upward from a validated mutation target.
    Applies Hebbian LTP to every causal ancestor.

    Returns: {node_id: new_exergy} for audit trail.

    Invoke AFTER:
        1. BFT consensus threshold cleared (2/3)
        2. Deterministic oracle (Z3/AST) veto cleared
        3. SAGA-commit phase initiated

    Never invoke speculatively or from retrieval paths.
    """
    t = now or time.time()
    audit: dict[str, float] = {}
    queue: list[tuple[str, int]] = [(target_node.node_id, 0)]
    visited: set[str] = set()

    total_energy_injected = 0.0
    max_depth_reached = 0

    while queue:
        current_id, depth = queue.pop(0)

        if current_id in visited:
            continue
        if depth > max_depth:
            # Log and raise: Causal depth breached. Indicates runaway topological cycle.
            msg = f"Causal Depth Exceeded ({max_depth}) at node {current_id}. Topology runaway."
            logger.error(msg)
            raise ValueError(msg)

        visited.add(current_id)
        if depth > max_depth_reached:
            max_depth_reached = depth

        node = graph_db.get_node(current_id)
        if node.is_tombstoned:
            # P0 Invariant: A live mutation cannot inherit from a tombstoned ancestor.
            msg = f"Causal Breach: Encountered TOMBSTONED ancestor '{current_id}'. Retrieval Consistency violated."
            logger.error(msg)
            raise ValueError(msg)

        node, delta = hebbian_reinforce(node, t, depth)
        total_energy_injected += delta
        graph_db.update_node(node)
        audit[current_id] = compute_exergy(node, t)

        for ancestor_id in graph_db.get_ancestors(current_id):
            if ancestor_id not in visited:
                queue.append((ancestor_id, depth + 1))

    logger.info(
        "Consolidation Telemetry",
        extra={
            "seed": target_node.node_id,
            "nodes_affected": len(audit),
            "max_depth_reached": max_depth_reached,
            "total_energy_injected": round(total_energy_injected, 4),
            "mean_energy_per_node": round(total_energy_injected / len(audit) if audit else 0.0, 4)
        }
    )

    return audit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ouroboros Thermodynamic Pruning Engine v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Storage Tier Lifecycle:\n"
            "  HOT  (exergy > 0.50) → Active, frequently accessed\n"
            "  WARM (exergy 0.25-0.50) → Aging, reduced priority\n"
            "  COLD (exergy 0.125-0.25) → Archive, pre-tombstone\n"
            "  VOID (exergy < 0.125) → Tombstoned, returned to entropy\n"
        ),
    )
    parser.add_argument(
        "--db",
        default="~/.cortex/cortex.db",
        help="Path to CORTEX SQLite database (default: ~/.cortex/cortex.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the purge without mutating state",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as machine-readable JSON",
    )
    parser.add_argument(
        "--semantic-collapse",
        action="store_true",
        help="Execute Phase 3: Zlib NCD Semantic Pruning to collapse redundant facts",
    )
    args = parser.parse_args()

    stats = execute_thermal_purge(
        db_path=args.db,
        dry_run=args.dry_run,
        json_output=args.json,
        enable_semantic_collapse=args.semantic_collapse,
    )

    if stats.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
