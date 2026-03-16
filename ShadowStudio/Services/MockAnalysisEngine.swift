import Foundation

public class MockAnalysisEngine {
    public init() {}
    
    public func analyze(assets: [Asset]) async throws -> [Asset] {
        // Simulate ML / Audio Analysis latency
        try await Task.sleep(nanoseconds: 2_000_000_000)
        
        var analyzed = assets
        for i in 0..<analyzed.count {
            switch analyzed[i].type {
            case .audio:
                analyzed[i].bpm = Double.random(in: 90...140).rounded()
                analyzed[i].key = ["Am", "F#m", "C", "Gm", "D#"].randomElement()
                analyzed[i].energy = Double.random(in: 0.1...1.0)
                analyzed[i].monetizationValue = Double.random(in: 0.5...5.0)
                let isDeadGold = Double.random(in: 0...1) > 0.8
                analyzed[i].isDeadGold = isDeadGold
                if isDeadGold {
                    analyzed[i].monetizationValue += 15.0 // High value loop
                }
            case .image:
                analyzed[i].tags = ["Dark", "Glitch", "Industrial", "Minimal"].shuffled().dropLast(2)
                analyzed[i].monetizationValue = Double.random(in: 1.0...10.0)
                analyzed[i].isDeadGold = Double.random(in: 0...1) > 0.85
            default:
                analyzed[i].monetizationValue = 0.0
            }
        }
        return analyzed
    }
    
    public func extractClusters(from assets: [Asset]) -> [AssetCluster] {
        let noir = AssetCluster(
            name: "Industrial Noir",
            description: "Texturas rotas, distorsión pesada y paletas monocromáticas.",
            assets: assets.filter { $0.energy ?? 0 > 0.7 || $0.tags.contains("Industrial") }
        )
        
        let ambient = AssetCluster(
            name: "Melancolía Sintética",
            description: "Pads largos, reverbs cavernosos y bpm bajo.",
            assets: assets.filter { ($0.bpm ?? 120 < 100) || $0.tags.contains("Minimal") }
        )
        
        return [noir, ambient]
    }
    
    public func generatePackCandidates(from clusters: [AssetCluster], assets: [Asset]) -> [PackCandidate] {
        let loops = assets.filter { $0.type == .audio && $0.isDeadGold }
        let samplePack = PackCandidate(
            title: "Vault Breaks Vol 1",
            type: .samplePack,
            description: "Una deconstrucción de loops de batería descartados durante 2021-2023. Listos para club.",
            assets: loops,
            estimatedPrice: 19.99
        )
        
        let visuals = assets.filter { $0.type == .image && $0.isDeadGold }
        let visualCapsule = PackCandidate(
            title: "Glitch Archives",
            type: .visualCapsule,
            description: "3 texturas generativas listas para portadas de Spotify o visualizers en directo.",
            assets: visuals,
            estimatedPrice: 49.00
        )
        
        return [samplePack, visualCapsule].filter { !$0.assets.isEmpty }
    }
}
