import Foundation

public class VaultScanner {
    public init() {}
    
    /// Mocks scanning a folder and finding assets
    public func scan(directory: URL) async throws -> [Asset] {
        // Simulate scanning latency
        try await Task.sleep(nanoseconds: 1_500_000_000)
        
        // Mock some heavy creative dump
        let mockFiles = [
            ("FINAL_v2_BUENA_AHORA_SI.mp3", AssetType.audio, 4.2),
            ("ambient_drone_04.wav", AssetType.audio, 12.5),
            ("kick_distorted.aif", AssetType.audio, 0.4),
            ("cover_alt_glitch.png", AssetType.image, 5.1),
            ("moodboard_techno.jpeg", AssetType.image, 2.3),
            ("ideas.txt", AssetType.text, 0.01),
            ("modular_jam_oct22.als", AssetType.project, 150.0),
            ("render_test.mp4", AssetType.video, 250.0),
            ("noise_sweep_120bpm.wav", AssetType.audio, 8.2),
            ("vox_cut_weird.wav", AssetType.audio, 1.1)
        ]
        
        return mockFiles.enumerated().map { index, fileInfo in
            let (name, type, mb) = fileInfo
            return Asset(
                id: UUID(),
                filename: name,
                path: directory.appendingPathComponent(name),
                type: type,
                sizeBytes: Int64(mb * 1024 * 1024),
                creationDate: Date().addingTimeInterval(-Double.random(in: 1000...10000000))
            )
        }
    }
}
