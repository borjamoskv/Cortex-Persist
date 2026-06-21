--------------------------- MODULE WAL_Async ---------------------------
EXTENDS Sequences, Naturals

VARIABLES 
    channel,      \* The unbounded crossbeam channel holding claims
    disk,         \* The persistent storage (ledger)
    client_ack,   \* Has the client received an OK?
    process_alive \* Is the CORTEX-Persist engine running?

vars == <<channel, disk, client_ack, process_alive>>

Init == 
    /\ channel = <<>>
    /\ disk = <<>>
    /\ client_ack = FALSE
    /\ process_alive = TRUE

IngestClaim == 
    /\ process_alive = TRUE
    /\ channel' = Append(channel, "claim1")
    /\ client_ack' = TRUE
    /\ UNCHANGED <<disk, process_alive>>

BackgroundFlush ==
    /\ process_alive = TRUE
    /\ Len(channel) > 0
    /\ disk' = Append(disk, Head(channel))
    /\ channel' = Tail(channel)
    /\ UNCHANGED <<client_ack, process_alive>>

Crash ==
    /\ process_alive = TRUE
    /\ process_alive' = FALSE
    /\ channel' = <<>>  \* RAM is wiped
    /\ UNCHANGED <<disk, client_ack>>

Next ==
    \/ IngestClaim
    \/ BackgroundFlush
    \/ Crash

-----------------------------------------------------------------------------
\* C5-REAL Absolute Consistency Property: 
\* If the client has an ACK, the data MUST be on disk, regardless of crashes.
AbsoluteConsistency == client_ack => ("claim1" \in {disk[i] : i \in 1..Len(disk)})

=============================================================================
