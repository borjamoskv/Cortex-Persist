namespace Babylon60.Kernel

open System

// BABYLON-60 Invariant 1: Unidades de Medida Nativas (Tipado de la realidad causal)
[<Measure>] type causal_distance
[<Measure>] type exergy_joule

module Types =
    // BABYLON-60 Invariant 2: Integer puro, sin floats silenciosos. Fable BigInt / uint64 map.
    type Hash256 = uint64 * uint64 * uint64 * uint64
    
    type Node = {
        Id: uint64
        Distance: int<causal_distance>
        PayloadHash: Hash256
    }

module Crypto =
    // Determinismo bit a bit en WASM, Node, Bun, Native (x86/ARM).
    let inline popCount (x: uint64) : uint64 =
        let mutable count = 0UL
        let mutable temp = x
        while temp > 0UL do
            count <- count + (temp &&& 1UL)
            temp <- temp >>> 1
        count

    let mix (a: uint64) (b: uint64) : uint64 =
        let x = a ^^^ b
        // Rotación a la izquierda estricta
        (x <<< 13) ||| (x >>> (64 - 13))

    let hashNode (node: Types.Node) : Types.Hash256 =
        let d = uint64 node.Distance
        let (h1, h2, h3, h4) = node.PayloadHash
        (mix h1 node.Id, mix h2 d, mix h3 h1, mix h4 h2)

module MaxwellDemon =
    // Invariant 3: Filtros de entropía estrictos sin cálculos estocásticos
    let evaluateEntropy (hash: Types.Hash256) : uint64 =
        let (h1, h2, h3, h4) = hash
        Crypto.popCount h1 + Crypto.popCount h2 + Crypto.popCount h3 + Crypto.popCount h4

    let filter (nodes: Types.Node list) (threshold: uint64) : Types.Node list =
        nodes 
        |> List.filter (fun n -> evaluateEntropy n.PayloadHash >= threshold)

module MerkleRollup =
    // Invariant 4: Merkle Rollup por lotes estructural, álgebra eliminada en compile time.
    let rec buildTree (hashes: Types.Hash256 list) : Types.Hash256 =
        match hashes with
        | [] -> (0UL, 0UL, 0UL, 0UL)
        | [h] -> h
        | _ ->
            let pairs = hashes |> List.chunkBySize 2
            let nextLevel = 
                pairs |> List.map (function
                    | [a; b] -> 
                        let (a1, a2, a3, a4) = a
                        let (b1, b2, b3, b4) = b
                        (Crypto.mix a1 b1, Crypto.mix a2 b2, Crypto.mix a3 b3, Crypto.mix a4 b4)
                    | [a] -> a // Nodo impar sube
                    | _ -> failwith "Invalid chunk")
            buildTree nextLevel

module Kernel =
    let executeC5 () =
        let nodes = [
            { Types.Id = 1UL; Distance = 10<causal_distance>; PayloadHash = (100UL, 200UL, 300UL, 400UL) }
            { Types.Id = 2UL; Distance = 15<causal_distance>; PayloadHash = (0xFFFFFFFFFFFFFFFFUL, 0UL, 0UL, 0UL) }
            { Types.Id = 3UL; Distance = 20<causal_distance>; PayloadHash = (10UL, 20UL, 30UL, 40UL) }
            { Types.Id = 4UL; Distance = 25<causal_distance>; PayloadHash = (0xAAAAAAAAAAAAAAAAUL, 0x5555555555555555UL, 0UL, 0UL) }
        ]
        
        let filteredNodes = MaxwellDemon.filter nodes 30UL
        let hashes = filteredNodes |> List.map Crypto.hashNode
        let rootHash = MerkleRollup.buildTree hashes
        
        rootHash

module EntryPoint =
    [<EntryPoint>]
    let main argv =
        let rootHash = Kernel.executeC5 ()
        printfn "[MOSKV-1] BABYLON-60 C5-REAL Kernel Initialized"
        printfn "[MOSKV-1] Merkle Root Hash: %A" rootHash
        0
