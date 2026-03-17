import Foundation
import Combine
import SwiftUI

@MainActor
public class StudioViewModel: ObservableObject {
    @Published public var rawAssets: [Asset] = []
    @Published public var clusters: [AssetCluster] = []
    @Published public var packCandidates: [PackCandidate] = []
    @Published public var deadGold: [Asset] = []
    
    @Published public var isAnalyzing: Bool = false
    @Published public var scanProgress: String = "Waiting for drop..."
    
    @Published public var totalValueExtracted: Double = 0.0
    
    private let scanner = VaultScanner()
    private let engine = MockAnalysisEngine()
    
    public init() {}
    
    public func ingestFolder(url: URL) {
        guard !isAnalyzing else { return }
        isAnalyzing = true
        scanProgress = "Indexing \(url.lastPathComponent)..."
        
        Task {
            do {
                // 1. Scan
                let scanned = try await scanner.scan(directory: url)
                self.scanProgress = "Fingerprinting \(scanned.count) assets..."
                
                // 2. Analyze
                let analyzed = try await engine.analyze(assets: scanned)
                
                // 3. Cluster & Monetize
                self.scanProgress = "Detecting Aesthetic Universes..."
                try await Task.sleep(nanoseconds: 800_000_000)
                
                let clusters = engine.extractClusters(from: analyzed)
                let packs = engine.generatePackCandidates(from: clusters, assets: analyzed)
                
                self.rawAssets = analyzed
                self.clusters = clusters
                self.packCandidates = packs
                self.deadGold = analyzed.filter { $0.isDeadGold }
                self.totalValueExtracted = analyzed.reduce(0) { $0 + $1.monetizationValue }
                
                self.scanProgress = "Extraction Complete."
            } catch {
                self.scanProgress = "Failed: \(error.localizedDescription)"
            }
            self.isAnalyzing = false
        }
    }
}
