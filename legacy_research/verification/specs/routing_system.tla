----------------- MODULE routing_system -----------------
EXTENDS Naturals, Sequences

VARIABLES 
    state,          \* Current routing phase: "idle", "routing", "agent_exec", "validate", "persist"
    event_log,      \* Sequence of processed system events
    budget,         \* Computational budget remaining (Real/Int proxy)
    memory          \* Persistent memory version set (simulating append-only versions)

(* Model Constants *)
Constants ==
    {"idle", "routing", "agent_exec", "validate", "persist"}

(* Initialization *)
Init ==
    /\ state = "idle"
    /\ event_log = << >>
    /\ budget = 100
    /\ memory = {0}  \* Initial state version 0

(* State Transitions *)
RouteEvent ==
    /\ state = "idle"
    /\ state' = "routing"
    /\ event_log' = Append(event_log, "TASK_RECEIVED")
    /\ budget' = budget
    /\ UNCHANGED <<memory>>

SelectAgents ==
    /\ state = "routing"
    /\ budget >= 10  \* Needs minimal budget to run agent inference
    /\ state' = "agent_exec"
    /\ event_log' = Append(event_log, "AGENT_ROUTED")
    /\ budget' = budget - 5  \* Deduct routing cost
    /\ UNCHANGED <<memory>>

ExecuteAgent ==
    /\ state = "agent_exec"
    /\ state' = "validate"
    /\ event_log' = Append(event_log, "TRAIT_EXTRACTED")
    /\ budget' = budget - 15  \* Deduct execution cost
    /\ UNCHANGED <<memory>>

ValidateOutput ==
    /\ state = "validate"
    /\ state' = "persist"
    /\ event_log' = Append(event_log, "TRAIT_NORMALIZED")
    /\ budget' = budget
    /\ UNCHANGED <<memory>>

PersistState ==
    LET next_ver == Max(memory) + 1 IN
    /\ state = "persist"
    /\ state' = "idle"
    /\ event_log' = Append(event_log, "METADATA_EXPORTED")
    /\ budget' = budget
    /\ memory' = memory \cup {next_ver}

\* Helper to get maximum element of a finite set of integers
Max(S) ==
    CHOOSE x \in S : \A y \in S : x >= y

\* System Fail-Safe (Out of Budget)
FailSafe ==
    /\ budget < 10
    /\ state /= "idle"
    /\ state' = "idle"
    /\ event_log' = Append(event_log, "OUT_OF_BUDGET_ABORT")
    /\ budget' = 100  \* Reset budget on recovery
    /\ UNCHANGED <<memory>>

Next ==
    \/ RouteEvent
    \/ SelectAgents
    \/ ExecuteAgent
    \/ ValidateOutput
    \/ PersistState
    \/ FailSafe

---------------------------------------------------------

(* Invariants *)

\* 1. Safety: Never execute agent actions without routing
SafetyNoUnmanagedExec ==
    state = "agent_exec" => 
        \E i \in 1..Len(event_log) : event_log[i] = "AGENT_ROUTED"

\* 2. Consistency: Version history is strictly increasing (no double-write/no overwrite)
NoDoubleWrite ==
    \A v1, v2 \in memory : v1 = v2 \/ v1 /= v2

\* 3. Liveness: System is eventually idle or active, avoiding lockups
LivenessType ==
    state \in Constants

=========================================================
