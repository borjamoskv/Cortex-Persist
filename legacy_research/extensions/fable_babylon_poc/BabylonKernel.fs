// [C5-REAL] Exergy-Maximized
// BABYLON-60 Fable 5.0 Deterministic Kernel Proof of Concept
// Enforces pure int32/uint32 semantics, Type Erasure, and Bitwise Constraints.

module BabylonKernel

open Fable.Core

/// 1. BORDER TRUNCATION PRIMITIVE (INVARIANTE I & IV)
/// Secuestra el motor JS forzando truncamiento u32 a nivel de AST.
/// El operador >>> 0 asegura que cualquier desbordamiento interno
/// se trate como un uint32 estricto en el motor anfitrión.
[<Emit("$0 >>> 0")>]
let forceU32 (value: int) : uint32 = jsNative

/// Alias para operaciones puras en u32
let inline toU32 (v: int) = forceU32 v

/// Estructura de Estado Estricto (INVARIANTE II: Álgebra Plana)
/// No genéricos. No uniones complejas expuestas en runtime.
type CausalState = {
    Cycle: uint32
    PositionX: int
    PositionY: int
    Exergy: uint32
    Hash: uint32
}

/// 2. CAUSAL DISTANCE (INVARIANTE III)
/// Distancia de Manhattan pura, Cero Floats. Computable en un ciclo bajo.
let computeCausalDistance (a: CausalState) (b: CausalState) : uint32 =
    let dx = abs (a.PositionX - b.PositionX)
    let dy = abs (a.PositionY - b.PositionY)
    toU32 (dx + dy)

/// 3. MAXWELL DEMON (FILTRO TERMODINÁMICO)
/// Válvula de un solo sentido para trayectorias de estado.
/// Descarta mutaciones que reduzcan la exergía total o superen la 
/// distancia causal máxima permitida en un solo ciclo de CPU.
let maxwellDemonFilter (maxDistance: uint32) (origin: CausalState) (target: CausalState) : bool =
    let distance = computeCausalDistance origin target
    let exergyYield = target.Exergy >= origin.Exergy
    let withinCausalCone = distance <= maxDistance
    
    // El demonio sólo abre la puerta si hay ganancia termodinámica 
    // y la mutación respeta el cono de luz causal del agente.
    exergyYield && withinCausalCone

/// 4. MERKLE ROLLUP (CONDENSACIÓN CRIPTOGRÁFICA DE BAJA FRICCIÓN)
/// Función de hash bit a bit (Avalanche simulado) pura matemática entera.
/// Diseñada para ser compilada a instrucciones Shift nativas por JIT.
let inline bitwiseMix (hash: uint32) (data: uint32) : uint32 =
    let step1 = (hash ^^^ data) * 0x9E3779B9u // Constante dorada
    let step2 = (step1 <<< 5) ^^^ (step1 >>> 27) // Rotación bit a bit
    forceU32 (int step2)

let merkleRollup (initialHash: uint32) (mutations: CausalState array) : uint32 =
    // Reducción secuencial y determinista del árbol
    mutations
    |> Array.fold (fun acc state ->
        let h1 = bitwiseMix acc state.Cycle
        let h2 = bitwiseMix h1 (toU32 state.PositionX)
        let h3 = bitwiseMix h2 (toU32 state.PositionY)
        let h4 = bitwiseMix h3 state.Exergy
        bitwiseMix h4 state.Hash
    ) initialHash

/// 5. BUCLE DE EJECUCIÓN OMEGA (Validación Causal)
/// Punto de entrada determinista del Proof of Concept.
let executeCausalTick (origin: CausalState) (candidates: CausalState array) : CausalState =
    
    // Filtrar candidatos usando al Maxwell Demon
    let validTrajectories = 
        candidates 
        |> Array.filter (maxwellDemonFilter 100u origin)

    // Si no hay rutas viables, retornamos el estado congelado (Apoptosis parcial)
    if validTrajectories.Length = 0 then 
        origin
    else
        // Elegimos la trayectoria de máxima exergía (Primitiva Ouroboros)
        let optimalState = 
            validTrajectories 
            |> Array.maxBy (fun s -> s.Exergy)
        
        // Calculamos el Rollup de todas las trayectorias evaluadas 
        // para anclar criptográficamente el esfuerzo computacional de la decisión.
        let effortHash = merkleRollup origin.Hash candidates
        
        // Mutación final determinista
        { optimalState with Hash = effortHash; Cycle = origin.Cycle + 1u }
