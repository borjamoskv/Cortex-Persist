namespace Cortex.Kernel

open Fable.Core
open Cortex.Kernel.Babylon

module StateMachine =

    type EpistemicPhase =
        | Observation
        | Reflection
        | Decision
        | Execution
        | Verification

    type TransitionResult =
        | Advanced of phase: EpistemicPhase * hash: uint32
        | Blocked of reason: string
        | Halted

    type MachineState = {
        Phase: EpistemicPhase
        Cycle: uint32
        ExergyAccum: uint32
        TraceHash: uint32
    }

    let phaseToTag (phase: EpistemicPhase) : uint32 =
        match phase with
        | Observation  -> 0u
        | Reflection   -> 1u
        | Decision     -> 2u
        | Execution    -> 3u
        | Verification -> 4u

    let hashTransition (state: MachineState) (nextPhase: EpistemicPhase) : uint32 =
        let FNV_PRIME = 16777619u
        let combined = state.TraceHash ^^^ (phaseToTag nextPhase) ^^^ state.Cycle
        combined * FNV_PRIME

    let transition (state: MachineState) (exergyInput: uint32) : TransitionResult =
        match state.Phase with
        | Observation ->
            if exergyInput > 0u then
                Advanced(Reflection, hashTransition state Reflection)
            else
                Blocked("Zero exergy")
        | Reflection ->
            if exergyInput >= 10u then
                Advanced(Decision, hashTransition state Decision)
            else
                Blocked("Zero exergy")
        | Decision ->
            if exergyInput >= 50u then
                Advanced(Execution, hashTransition state Execution)
            else
                Blocked("Zero exergy")
        | Execution ->
            Advanced(Verification, hashTransition state Verification)
        | Verification ->
            Advanced(Observation, hashTransition state Observation)

    let stepMachine (state: MachineState) (exergyInput: uint32) : MachineState =
        match transition state exergyInput with
        | Advanced(nextPhase, newHash) ->
            let cycleIncrement =
                match state.Phase with
                | Verification -> 1u
                | _ -> 0u
            { Phase = nextPhase
              Cycle = state.Cycle + cycleIncrement
              ExergyAccum = state.ExergyAccum + exergyInput
              TraceHash = newHash }
        | Blocked _ ->
            { state with ExergyAccum = state.ExergyAccum + exergyInput }
        | Halted ->
            state

    let runCycle (initialState: MachineState) (inputs: uint32 array) : MachineState =
        Array.fold stepMachine initialState inputs
