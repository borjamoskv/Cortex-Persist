import Foundation

public enum AssetType: String, Codable {
    case audio = "Audio"
    case image = "Image"
    case video = "Video"
    case text = "Text"
    case project = "Project"
    case unknown = "Unknown"
}

public struct Asset: Identifiable, Codable, Hashable {
    public let id: UUID
    public let filename: String
    public let path: URL
    public let type: AssetType
    public let sizeBytes: Int64
    public let creationDate: Date
    
    // Extracted Metadata (Mocked)
    public var bpm: Double?
    public var key: String?
    public var energy: Double? // 0.0 to 1.0
    public var tags: [String]
    
    // Extracted Value Metric
    public var monetizationValue: Double // estimated $ value
    public var isDeadGold: Bool
    
    public init(id: UUID = UUID(), filename: String, path: URL, type: AssetType, sizeBytes: Int64, creationDate: Date, bpm: Double? = nil, key: String? = nil, energy: Double? = nil, tags: [String] = [], monetizationValue: Double = 0.0, isDeadGold: Bool = false) {
        self.id = id
        self.filename = filename
        self.path = path
        self.type = type
        self.sizeBytes = sizeBytes
        self.creationDate = creationDate
        self.bpm = bpm
        self.key = key
        self.energy = energy
        self.tags = tags
        self.monetizationValue = monetizationValue
        self.isDeadGold = isDeadGold
    }
}
