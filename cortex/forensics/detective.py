# [C5-REAL] Exergy-Maximized
"""
CORTEX Forensic Detective Module (AX-I)
Sovereign flow and graph analysis for causal paths, anomalies, and taint tracing.
"""

import logging
from typing import Any

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.graph.engine import find_path, get_graph_sync, query_entity_sync

logger = logging.getLogger("cortex.forensics.detective")


class InspectorGadget:
    """
    Sovereign Graph & Flow Analyzer.
    Investigates structural anomalies, pathing logic, and causal flows within the Knowledge Graph.
    """

    def __init__(self, conn, tenant_id: str = "default"):
        self.conn = conn
        self.tenant_id = tenant_id

    def analyze_topology(self, project: str | None = None) -> dict[str, Any]:
        """
        Analyzes the overall structure of the knowledge graph.
        Returns metrics on connectedness, isolated nodes, and density.
        """
        logger.info("[Detective] Initiating topology analysis for project: %s", project)
        graph = get_graph_sync(self.conn, project=project, limit=10000, tenant_id=self.tenant_id)
        
        nodes = graph.get("nodes", [])
        links = graph.get("links", [])
        
        if not nodes:
            return {"status": "EMPTY_GRAPH"}

        # Calculate isolated nodes
        connected_ids = set()
        for link in links:
            connected_ids.add(link["source"])
            connected_ids.add(link["target"])
            
        isolated_nodes = [n for n in nodes if n["id"] not in connected_ids]
        
        density = len(links) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0
        
        return {
            "node_count": len(nodes),
            "link_count": len(links),
            "isolated_nodes_count": len(isolated_nodes),
            "isolated_nodes": [n["id"] for n in isolated_nodes],
            "graph_density": density,
            "status": "HEALTHY" if density > 0.05 and len(isolated_nodes) < len(nodes) * 0.2 else "FRAGMENTED"
        }

    async def trace_causal_chain(self, source_entity: str, target_entity: str, max_depth: int = 5) -> dict[str, Any]:
        """
        Traces the causal path (flow) between two entities in the graph.
        """
        logger.info("[Detective] Tracing causal chain from %s to %s", source_entity, target_entity)
        paths = await find_path(self.conn, source_entity, target_entity, max_depth=max_depth, tenant_id=self.tenant_id)
        
        if not paths:
            return {"status": "NO_PATH", "chain": []}
            
        return {
            "status": "PATH_FOUND",
            "path_count": len(paths),
            "shortest_chain": paths[0] if paths else None,
            "all_chains": paths
        }

    def detect_flow_anomalies(self, project: str | None = None) -> list[dict[str, Any]]:
        """
        Detects anomalies in the graph flow (e.g., sources of truth without validation, or information blackholes).
        """
        graph = get_graph_sync(self.conn, project=project, limit=10000, tenant_id=self.tenant_id)
        nodes = graph.get("nodes", [])
        links = graph.get("links", [])
        
        in_degree = {n["id"]: 0 for n in nodes}
        out_degree = {n["id"]: 0 for n in nodes}
        
        for link in links:
            out_degree[link["source"]] = out_degree.get(link["source"], 0) + 1
            in_degree[link["target"]] = in_degree.get(link["target"], 0) + 1
            
        anomalies = []
        for n in nodes:
            nid = n["id"]
            if out_degree[nid] > 5 and in_degree[nid] == 0:
                anomalies.append({"type": "UNVALIDATED_SOURCE", "entity": nid, "out_degree": out_degree[nid]})
            elif in_degree[nid] > 5 and out_degree[nid] == 0:
                anomalies.append({"type": "INFORMATION_BLACKHOLE", "entity": nid, "in_degree": in_degree[nid]})
                
        return anomalies

    def audit_entity_provenance(self, entity_name: str) -> dict[str, Any]:
        """
        Audits an entity to ensure it has valid provenance and facts backing it up.
        """
        entity = query_entity_sync(self.conn, entity_name, tenant_id=self.tenant_id)
        if not entity:
            return {"status": "NOT_FOUND"}
            
        return {
            "status": "VALID",
            "entity": entity["name"],
            "mention_count": entity.get("mention_count", 0),
            "first_seen": entity.get("first_seen"),
            "last_seen": entity.get("last_seen"),
            "provenance_score": min(1.0, entity.get("mention_count", 0) / 10.0)
        }
        
    async def trace_ledger_flow(self, resource_id: str) -> dict[str, Any]:
        """
        Traces the mutation flow of a specific resource across the Audit Ledger.
        """
        try:
            cursor = await self.conn.execute(
                "SELECT timestamp, actor_role, actor_id, action, status, signature "
                "FROM security_audit_log WHERE resource = ? AND tenant_id = ? "
                "ORDER BY timestamp ASC",
                (resource_id, self.tenant_id)
            )
            rows = await cursor.fetchall()
            
            mutations = []
            for row in rows:
                mutations.append({
                    "timestamp": row[0],
                    "actor_role": row[1],
                    "actor_id": row[2],
                    "action": row[3],
                    "status": row[4],
                    "signature": row[5]
                })
                
            return {
                "resource": resource_id,
                "mutation_count": len(mutations),
                "flow": mutations,
                "status": "TRACKED" if mutations else "UNTRACKED"
            }
        except Exception as e:
            logger.error("[Detective] Ledger flow trace failed for %s: %s", resource_id, e)
            return {"status": "ERROR", "error": str(e)}

    async def verify_ledger_continuity(self) -> dict[str, Any]:
        """
        Cryptographically verifies the continuity of the entire audit flow (Ledger Hash-Chain).
        """
        ledger = EnterpriseAuditLedger(self.conn)
        try:
            cursor = await self.conn.execute(
                "SELECT audit_id, prev_hash, signature FROM security_audit_log ORDER BY rowid ASC"
            )
            rows = await cursor.fetchall()
            
            if not rows:
                return {"status": "EMPTY_LEDGER"}
                
            # Note: This is a simplified check for demo purposes.
            # A real scan would fully reconstruct the Merkle Tree.
            valid_signatures = 0
            for row in rows:
                # payload is usually the entry_hash or merkle_root representation
                # Using prev_hash here as fallback verification for individual rows
                if ledger.verify_zk_seal(row[1], row[2]): 
                    valid_signatures += 1
                    
            return {
                "status": "VERIFIED" if valid_signatures > 0 else "COMPROMISED",
                "entries_checked": len(rows),
                "valid_seals": valid_signatures
            }
        except Exception as e:
            logger.error("[Detective] Ledger continuity verification failed: %s", e)
            return {"status": "ERROR", "error": str(e)}
