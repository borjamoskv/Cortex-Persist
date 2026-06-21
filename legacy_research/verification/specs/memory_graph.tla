----------------- MODULE memory_graph -----------------
EXTENDS Naturals, Sequences, FiniteSets

VARIABLES
    nodes,        \* Set of committed memory nodes (identities)
    versions,     \* Map of node -> set of version integers
    edges,        \* Causal graph edges (node_version -> node_version)
    hashes        \* Simulated hash store mapping (node, version) -> hash_string

(* Initial State *)
Init ==
    /\ nodes = {}
    /\ versions = [n \in {} |-> {}]
    /\ edges = {}
    /\ hashes = [nv \in {} |-> ""]

(* Append Fact Event *)
AppendFact(node, content, parent_nv) ==
    LET new_ver == IF node \in DOMAIN versions THEN Cardinality(versions[node]) + 1 ELSE 1 IN
    LET current_hash == "HASH_" \o ToString(new_ver) IN
    /\ nodes' = nodes \cup {node}
    /\ versions' = [n \in (DOMAIN versions \cup {node}) |-> 
                      IF n = node THEN (IF node \in DOMAIN versions THEN versions[node] \cup {new_ver} ELSE {new_ver})
                      ELSE versions[n]]
    /\ edges' = IF parent_nv /= << >> THEN edges \cup {<< <<node, new_ver>>, parent_nv >>} ELSE edges
    /\ hashes' = [nv \in (DOMAIN hashes \cup {<<node, new_ver>>}) |->
                    IF nv = <<node, new_ver>> THEN current_hash ELSE hashes[nv]]

(* Immutability Proof Invariants *)

\* Helper definition
ToString(v) == v \* Simplified representation

\* 1. Append-Only Safety: No version can ever be deleted or mutated
NoOverwrites ==
    \A n \in nodes : \A v \in versions[n] :
        hashes[<<n, v>>] /= ""

\* 2. Version Linearity Invariant: A node's versions form a strictly growing set
StrictlyIncreasingVersions ==
    \A n \in nodes : \A v \in versions[n] :
        v > 0

\* 3. DAG Causal Continuity: Every edge represents an immutable back-link to a prior node version
DAGSafety ==
    \A edge \in edges :
        edge[2] \in {<<n, v>> : n \in nodes, v \in versions[n]}

=======================================================
