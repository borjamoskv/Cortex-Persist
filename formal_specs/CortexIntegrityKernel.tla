---------------- MODULE CortexIntegrityKernel ----------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

(* 
    CORTEX-Persist Formal Specification (TLA+)
    - Explicit Derived Function for Ledger Truth
    - Formal adversary injection mapping
    - Deterministic abstract repair step
*)

CONSTANTS 
    Events,         \* Set of all possible events
    ValidSigs,      \* Subset of Events with valid Ed25519 signatures
    CorruptEvents   \* Subset of Events representing semantically corrupt data (Adversary injected)

VARIABLES 
    gateway,        \* Transient buffer of proposed events
    mem,            \* Materialized view (persistent state)
    ledger,         \* Canonical truth (hash chain sequence)
    nonces,         \* Global uniqueness constraint
    status          \* Mapping from Event -> Status string

vars == <<gateway, mem, ledger, nonces, status>>

STATES == {"PROPOSED", "VALIDATED", "TAINTED", "COMMITTED", "REJECTED", "FAILED", "NULL"}

\* Explicit Derived Function for Ledger Elements (No ambiguous inline sets)
LedgerSet == {ledger[i] : i \in 1..Len(ledger)}

--------------------------------------------------------------
(* Initial State *)
Init == 
    /\ gateway = {}
    /\ mem = {}
    /\ ledger = <<>>
    /\ nonces = {}
    /\ status = [e \in Events |-> "NULL"]

--------------------------------------------------------------
(* State Transitions (SAGA Contract) *)

Propose(e) == 
    /\ status[e] = "NULL"
    /\ gateway' = gateway \cup {e}
    /\ status' = [status EXCEPT ![e] = "PROPOSED"]
    /\ UNCHANGED <<mem, ledger, nonces>>

AuthGate(e) == 
    /\ status[e] = "PROPOSED"
    /\ e \in gateway
    /\ IF e \in ValidSigs /\ e.nonce \notin nonces
       THEN status' = [status EXCEPT ![e] = "VALIDATED"]
       ELSE status' = [status EXCEPT ![e] = "REJECTED"]
    /\ UNCHANGED <<gateway, mem, ledger, nonces>>

Taint(e) == 
    /\ status[e] = "VALIDATED"
    /\ status' = [status EXCEPT ![e] = "TAINTED"]
    /\ UNCHANGED <<gateway, mem, ledger, nonces>>

\* SUCCESSFUL ATOMIC COMMIT (Ledger as Truth)
Commit(e) == 
    /\ status[e] = "TAINTED"
    /\ e.nonce \notin nonces \* F1 Concurrency check 
    /\ ledger' = Append(ledger, e)
    /\ mem' = mem \cup {e}
    /\ nonces' = nonces \cup {e.nonce}
    /\ status' = [status EXCEPT ![e] = "COMMITTED"]
    /\ gateway' = gateway \ {e}

--------------------------------------------------------------
(* Adversary Model *)

\* ADVERSARY INJECTION: Key Compromise
\* The adversary possesses a compromised key, meaning they can produce
\* an event that is mathematically valid (e \in ValidSigs) but semantically corrupt.
AdversaryInject(e) ==
    /\ e \in ValidSigs
    /\ e \in CorruptEvents
    /\ status[e] = "NULL"
    /\ gateway' = gateway \cup {e}
    /\ status' = [status EXCEPT ![e] = "PROPOSED"]
    /\ UNCHANGED <<mem, ledger, nonces>>

--------------------------------------------------------------
(* Explicit Failure Modes *)

\* FAILURE MODE 1: Lock Contention (F1)
CommitFailsLock(e) ==
    /\ status[e] = "TAINTED"
    /\ e.nonce \in nonces 
    /\ status' = [status EXCEPT ![e] = "REJECTED"] 
    /\ gateway' = gateway \ {e}
    /\ UNCHANGED <<mem, ledger, nonces>>

\* FAILURE MODE 2: Partial Commit Crash (F2)
PartialCommitCrash(e) ==
    /\ status[e] = "TAINTED"
    /\ e.nonce \notin nonces
    /\ mem' = mem \cup {e}
    /\ nonces' = nonces \cup {e.nonce}
    /\ status' = [status EXCEPT ![e] = "FAILED"]
    /\ gateway' = gateway \ {e}
    /\ UNCHANGED <<ledger>>

--------------------------------------------------------------
(* Recovery Semantics *)

\* F2 Recovery: Abstract Repair Step (Total Correction)
\* Destructive reconciliation of mem back to ledger state.
RecoveryRollback ==
    /\ mem /= LedgerSet  \* Trigger condition: inconsistency exists
    /\ mem' = {e \in mem : e \in LedgerSet}
    /\ nonces' = {e.nonce : e \in mem'} 
    /\ status' = [e \in Events |-> IF status[e] = "FAILED" THEN "REJECTED" ELSE status[e]]
    /\ UNCHANGED <<gateway, ledger>>

--------------------------------------------------------------
(* Next State Relation *)
Next == 
    \/ \E e \in Events : Propose(e) \/ AuthGate(e) \/ Taint(e) \/ Commit(e) \/ CommitFailsLock(e) \/ PartialCommitCrash(e) \/ AdversaryInject(e)
    \/ RecoveryRollback

--------------------------------------------------------------
(* Formal Invariants (Safety Properties) *)

TypeOK == 
    /\ gateway \subseteq Events
    /\ mem \subseteq Events
    /\ \A e \in Events: status[e] \in STATES

\* Write-Path Integrity: Nothing enters memory without Valid Ed25519
WritePathIntegrity == 
    \A e \in mem: e \in ValidSigs

\* No-Replay Constraint: Nonces are globally unique in truth
NoReplay == 
    \A e1, e2 \in LedgerSet: 
        e1 /= e2 => e1.nonce /= e2.nonce

\* The Fundamental Weakness of Symmetric/Single Key models:
\* If a key is compromised, corrupt events WILL enter the ledger.
\* This invariant WILL BE VIOLATED by TLC if AdversaryInject runs.
NoCorruptEvents ==
    \A e \in LedgerSet: e \notin CorruptEvents

--------------------------------------------------------------
(* Liveness Properties (Temporal Logic) *)

\* Eventually Stable: The system will always eventually return to a state where mem = LedgerSet
EventuallyStable == 
    <>[](mem = LedgerSet)

\* Terminal State Reachability
EventualResolution ==
    \A e \in Events : 
        (status[e] = "PROPOSED") ~> (status[e] \in {"COMMITTED", "REJECTED"})

==============================================================
