import Foundation

public struct AssetCluster: Identifiable, Hashable {
    public let id: UUID
    public let name: String // e.g. "Industrial Noir", "Melancolía Sintética"
    public let description: String
    public let assets: [Asset]
    
    public var totalValue: Double {
        assets.reduce(0) { $0 + $1.monetizationValue }
    }
    
    public init(id: UUID = UUID(), name: String, description: String, assets: [Asset]) {
        self.id = id
        self.name = name
        self.description = description
        self.assets = assets
    }
}
