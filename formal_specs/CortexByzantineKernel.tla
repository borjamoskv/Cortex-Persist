---------------- MODULE CortexByzantineKernel ----------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

(* 
    CORTEX-Persist Byzantine-Aware Formal Specification (TLA+)
    - Epistemic State Partitioning: Cryptographic Validity vs Semantic Truth
    - BFT Quorum Consensus (f < n/3)
    - Honest Oracle voting vs Byzantine Injection
*)

CONSTANTS 
    Events,           \* Universal set of all events
    ValidSigs,        \* Events with mathematically valid signatures
    CorruptEvents,    \* A subset of ValidSigs representing semantically corrupt data
    Agents,           \* Set of all participating nodes
    ByzantineAgents,  \* Subset of Agents controlled by the adversary
    QuorumThreshold   \* Integer defining the required votes (n - f)

VARIABLES 
    mempool,          \* Events proposed and gossiped (L1)
    signatures,       \* Mapping: Event -> Set of Agents who voted for it
    mem,              \* Materialized view (persistent state)
    ledger,           \* Canonical truth (hash chain sequence)
    nonces            \* Global uniqueness constraint

vars == <<mempool, signatures, mem, ledger, nonces>>

\* Derived sets defining the epistemic partition
NormalEvents == ValidSigs \ CorruptEvents
HonestAgents == Agents \ ByzantineAgents
LedgerSet == {ledger[i] : i \in 1..Len(ledger)}

--------------------------------------------------------------
(* Initial State *)
Init == 
    /\ mempool = {}
    /\ signatures = [e \in Events |-> {}]
    /\ mem = {}
    /\ ledger = <<>>
    /\ nonces = {}

--------------------------------------------------------------
(* 1. Adversary Model (Byzantine Injection) *)

\* The adversary proposes a cryptographically valid but semantically corrupt event.
\* Byzantine agents immediately vote for it.
AdversaryInject(e) ==
    /\ e \in CorruptEvents
    /\ e \notin mempool
    /\ mempool' = mempool \cup {e}
    /\ signatures' = [signatures EXCEPT ![e] = ByzantineAgents]
    /\ UNCHANGED <<mem, ledger, nonces>>

--------------------------------------------------------------
(* 2. Honest Oracle Voting (Semantic Validation) *)

\* An honest agent proposes a normal event, or votes on a normal event in the mempool.
\* Honest agents will NEVER vote for e \in CorruptEvents.
HonestVote(e, a) ==
    /\ a \in HonestAgents
    /\ e \in NormalEvents
    /\ e \notin mempool \/ e \in mempool \* Either proposing or voting on existing
    /\ a \notin signatures[e] \* Hasn't voted yet
    /\ mempool' = mempool \cup {e}
    /\ signatures' = [signatures EXCEPT ![e] = signatures[e] \cup {a}]
    /\ UNCHANGED <<mem, ledger, nonces>>

--------------------------------------------------------------
(* 3. Quorum Commitment (State Transition) *)

\* An event is committed if it reaches the QuorumThreshold.
Commit(e) == 
    /\ e \in mempool
    /\ Cardinality(signatures[e]) >= QuorumThreshold
    /\ e.nonce \notin nonces \* Concurrency / Replay protection
    /\ ledger' = Append(ledger, e)
    /\ mem' = mem \cup {e}
    /\ nonces' = nonces \cup {e.nonce}
    /\ mempool' = mempool \ {e}
    /\ UNCHANGED <<signatures>>

--------------------------------------------------------------
(* Next State Relation *)
Next == 
    \/ \E e \in CorruptEvents : AdversaryInject(e)
    \/ \E e \in NormalEvents, a \in HonestAgents : HonestVote(e, a)
    \/ \E e \in mempool : Commit(e)

--------------------------------------------------------------
(* Formal Invariants (Safety Properties) *)

TypeOK == 
    /\ mempool \subseteq Events
    /\ mem \subseteq Events
    /\ \A e \in Events: signatures[e] \subseteq Agents

\* The Ultimate BFT Guarantee:
\* A Corrupt event can NEVER enter the canonical truth.
NoCorruptCommit == 
    \A e \in LedgerSet: e \notin CorruptEvents

\* No-Replay Constraint
NoReplay == 
    \A e1, e2 \in LedgerSet: 
        e1 /= e2 => e1.nonce /= e2.nonce

--------------------------------------------------------------
(* Liveness Properties *)

\* If an honest event is proposed, it will eventually be committed.
\* (Assuming enough honest agents vote for it).
EventualHonestCommit ==
    \A e \in NormalEvents : 
        (e \in mempool) ~> (e \in LedgerSet)

==============================================================
