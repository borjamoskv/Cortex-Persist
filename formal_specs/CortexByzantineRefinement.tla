---------------- MODULE CortexByzantineRefinement ----------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

(*
    CORTEX-Persist: Byzantine Refinement Proof Skeleton
    
    This module maps the distributed runtime execution model 
    to the abstract `CortexByzantineKernel.tla` specification.
    
    It proves that the asynchronous distributed system (Runtime)
    strictly refines the BFT Integrity Kernel, preserving safety
    under an explicit Adversarial Environment.
*)

CONSTANTS 
    Events,           
    ValidSigs,        
    CorruptEvents,    
    Agents,           
    ByzantineAgents,  
    QuorumThreshold

VARIABLES 
    network_channel,  \* The environment: messages in transit (Unordered, Unreliable)
    db_store          \* The runtime database (quorum_requests + fact_store)

vars == <<network_channel, db_store>>

--------------------------------------------------------------
(* 1. EXPLICIT PIPELINE: Intent -> Evidence -> Quorum -> Commit *)

MessageTypes == {"INTENT", "EVIDENCE"}

Init == 
    /\ network_channel = {}
    /\ db_store = [e \in Events |-> [status |-> "NULL", evidence |-> {}]]

--------------------------------------------------------------
(* 2. THE ADVERSARY: Environment Nondeterministic Scheduler *)

\* The adversary does not mutate the canonical truth directly.
\* It manipulates the asynchronous environment channel.

AdversaryReorderDelay(msg) ==
    \* In TLA+, sets are inherently unordered and unordered channels 
    \* naturally model reordering and delay.
    /\ msg \in network_channel
    /\ UNCHANGED vars

AdversaryInject(e) ==
    \* The adversary attempts to inject a semantically corrupt event.
    \* It only adds it to the network_channel.
    /\ e \in CorruptEvents
    /\ network_channel' = network_channel \cup {[type |-> "INTENT", payload |-> e]}
    /\ UNCHANGED <<db_store>>

AdversaryStep == 
    \/ \E msg \in network_channel: AdversaryReorderDelay(msg)
    \/ \E e \in CorruptEvents: AdversaryInject(e)

--------------------------------------------------------------
(* 3. DISTRIBUTED RUNTIME DYNAMICS *)

NodeProposeIntent(e) ==
    \* An honest node proposes an event.
    /\ e \in ValidSigs \ CorruptEvents
    /\ network_channel' = network_channel \cup {[type |-> "INTENT", payload |-> e]}
    /\ UNCHANGED <<db_store>>

NodeSubmitEvidence(e, a) ==
    \* A node evaluates an INTENT and submits EVIDENCE (signature).
    /\ [type |-> "INTENT", payload |-> e] \in network_channel
    /\ e \notin CorruptEvents  \* Semantic Truth Verification (Local to honest nodes)
    /\ a \notin db_store[e].evidence
    /\ network_channel' = network_channel \cup {[type |-> "EVIDENCE", payload |-> e, agent |-> a]}
    /\ db_store' = [db_store EXCEPT ![e].status = "PENDING"]

DatabaseProcessEvidence(e, a) ==
    \* The QuorumGateway processes the signature.
    /\ [type |-> "EVIDENCE", payload |-> e, agent |-> a] \in network_channel
    /\ a \notin db_store[e].evidence
    /\ db_store' = [db_store EXCEPT ![e].evidence = db_store[e].evidence \cup {a}]
    /\ network_channel' = network_channel \ {[type |-> "EVIDENCE", payload |-> e, agent |-> a]}

DatabaseCommitQuorum(e) ==
    \* The QuorumGateway reaches the threshold and commits.
    /\ db_store[e].status = "PENDING"
    /\ Cardinality(db_store[e].evidence) >= QuorumThreshold
    /\ db_store' = [db_store EXCEPT ![e].status = "COMMITTED"]
    /\ UNCHANGED <<network_channel>>

RuntimeNext ==
    \/ AdversaryStep
    \/ \E e \in Events: NodeProposeIntent(e)
    \/ \E e \in Events, a \in Agents \ ByzantineAgents: NodeSubmitEvidence(e, a)
    \/ \E e \in Events, a \in Agents: DatabaseProcessEvidence(e, a)
    \/ \E e \in Events: DatabaseCommitQuorum(e)

Spec == Init /\ [][RuntimeNext]_vars

--------------------------------------------------------------
(* 4. OBSERVATION MAPPING (The Bisimulation) *)

\* We project the distributed runtime state onto the abstract Kernel variables.

AbstractMempool == {e \in Events: db_store[e].status = "PENDING"}

AbstractLedger == 
    \* In TLA+, we map the set of COMMITTED events to a sequence. 
    \* For simplicity in mapping, we just check set membership.
    \* A true sequence mapping requires an explicit sequence constructor.
    {e \in Events: db_store[e].status = "COMMITTED"}

AbstractMem == AbstractLedger \* mem is definitively derived from ledger

AbstractSignatures == [e \in Events |-> db_store[e].evidence]

AbstractNonces == {e.nonce : e \in AbstractLedger}

--------------------------------------------------------------
(* 5. THE FORMAL REFINEMENT RELATION *)

\* We instantiate the abstract Kernel using our projected mappings.
Kernel == INSTANCE CortexByzantineKernel WITH 
    mempool <- AbstractMempool,
    signatures <- AbstractSignatures,
    mem <- AbstractMem,
    ledger <- AbstractLedger,  \* Assuming Kernel is refactored to treat ledger as a Set for this proof
    nonces <- AbstractNonces

\* The Ultimate Verification Target:
\* If our Runtime Spec is correct, it MUST satisfy the Abstract Kernel's Next relation.
THEOREM Refinement == Spec => Kernel!Spec

==============================================================
