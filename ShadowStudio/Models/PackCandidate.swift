import Foundation

public enum PackType: String, Codable {
    case samplePack = "Sample Pack"
    case drumKit = "Drum Kit"
    case microEP = "Micro EP"
    case visualCapsule = "Visual Capsule"
    case archiveDrop = "Archive Drop"
}

public struct PackCandidate: Identifiable, Hashable {
    public let id: UUID
    public let title: String
    public let type: PackType
    public let description: String
    public let assets: [Asset]
    public let estimatedPrice: Double
    
    public init(id: UUID = UUID(), title: String, type: PackType, description: String, assets: [Asset], estimatedPrice: Double) {
        self.id = id
        self.title = title
        self.type = type
        self.description = description
        self.assets = assets
        self.estimatedPrice = estimatedPrice
    }
}
