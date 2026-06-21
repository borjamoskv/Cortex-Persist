module Program

open Cortex.Kernel
open Cortex.Kernel.Babylon
open Cortex.Kernel.StateMachine

[<EntryPoint>]
let main argv =
    printfn "CORTEX-PERSIST C5-REAL: F# FABLE KERNEL INITIALIZED"
    
    let demon = MaxwellDemon(85us<distance>)
    demon.SetState("CONSTRUCT")
    
    let chunks = [|
        (1001u, "El sistema es determinista.")
        (1001u, "El sistema es determinista.")
        (2005u, "La entropía de la red ha aumentado.")
        (2005u, "La entropía de la red ha aumentado.")
        (3010u, "Iniciando secuencia de auto-reparación.")
    |]

    let (retained, purged) = demon.PurgeRedundant(chunks)
    
    printfn "\n[MaxwellDemon Test]"
    printfn "Total chunks evaluados: %d" chunks.Length
    printfn "Chunks retenidos: %d" retained.Length
    printfn "Chunks purgados: %d" purged
    
    for c in retained do
        printfn " - %s" c

    // Test merkle
    let merkleRoot = hashDistanceRollup 123456u [| 50us<distance>; 10us<distance>; 0us<distance> |]
    printfn "\nMerkle Rollup Root (uint32): %u" merkleRoot

    // StateMachine Demo
    printfn "\n[StateMachine Test]"
    let initial = { Phase = Observation; Cycle = 0u; ExergyAccum = 0u; TraceHash = 0u }
    let inputs = [| 5u; 15u; 60u; 1u; 1u; 10u; 20u; 100u; 1u; 1u |]
    let finalState = StateMachine.runCycle initial inputs
    printfn "Final Phase: %A" finalState.Phase
    printfn "Cycles completed: %u" finalState.Cycle
    printfn "Exergy accumulated: %u" finalState.ExergyAccum
    printfn "Trace Hash: %u" finalState.TraceHash

    0 // return an integer exit code
