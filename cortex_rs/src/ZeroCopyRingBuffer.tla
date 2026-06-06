---- MODULE ZeroCopyRingBuffer ----
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS Capacity, Consumers

VARIABLES buffer, tasks

vars == <<buffer, tasks>>

Init == 
    /\ buffer = [i \in 1..Capacity |-> 0]
    /\ tasks = [c \in Consumers |-> {}]

Enqueue == 
    \E i \in 1..Capacity :
        /\ buffer[i] = 0
        /\ buffer' = [buffer EXCEPT ![i] = 1]
        /\ UNCHANGED tasks

Fetch(c) == 
    /\ tasks[c] = {}
    /\ \E i \in 1..Capacity : buffer[i] = 1
    /\ buffer' = [i \in 1..Capacity |-> IF buffer[i] = 1 THEN 2 ELSE buffer[i]]
    /\ tasks' = [tasks EXCEPT ![c] = {i \in 1..Capacity : buffer[i] = 1}]

ProcessComplete(c) == 
    /\ tasks[c] /= {}
    /\ buffer' = [i \in 1..Capacity |-> IF i \in tasks[c] THEN 0 ELSE buffer[i]]
    /\ tasks' = [tasks EXCEPT ![c] = {}]

Next == Enqueue \/ (\E c \in Consumers : Fetch(c)) \/ (\E c \in Consumers : ProcessComplete(c))

Spec == Init /\ [][Next]_vars /\ (\A c \in Consumers : WF_vars(Fetch(c)) /\ WF_vars(ProcessComplete(c)))

TypeOK == 
    /\ \A i \in 1..Capacity : buffer[i] \in {0, 1, 2}
    /\ \A c \in Consumers : tasks[c] \subseteq 1..Capacity

Safety == \A i \in 1..Capacity : 
    (buffer[i] = 2) <=> (\E c \in Consumers : i \in tasks[c])

MutualExclusion == \A c1, c2 \in Consumers : 
    (c1 /= c2) => (tasks[c1] \cap tasks[c2] = {})

Liveness == \A i \in 1..Capacity : (buffer[i] = 1) ~> (buffer[i] = 0)

====
