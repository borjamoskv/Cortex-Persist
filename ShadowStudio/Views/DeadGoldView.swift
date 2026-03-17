import SwiftUI

public struct DeadGoldView: View {
    @EnvironmentObject var viewModel: StudioViewModel
    
    public var body: some View {
        ZStack {
            Theme.background.edgesIgnoringSafeArea(.all)
            
            VStack(alignment: .leading, spacing: 20) {
                HStack {
                    Text("DEAD GOLD")
                        .font(.system(size: 32, weight: .heavy, design: .monospaced))
                        .foregroundColor(Theme.accent)
                    Spacer()
                    Text("\(viewModel.deadGold.count) ITEMS")
                        .font(.headline)
                        .foregroundColor(Theme.textMuted)
                }
                
                Text("Tus joyas olvidadas. El motor ha detectado anomalías de alto rendimiento en estos archivos.")
                    .foregroundColor(Theme.textSecondary)
                
                if viewModel.deadGold.isEmpty {
                    Spacer()
                    Text("NO DEAD GOLD DETECTED YET.")
                        .font(.system(.body, design: .monospaced))
                        .foregroundColor(Theme.textMuted)
                        .frame(maxWidth: .infinity, alignment: .center)
                    Spacer()
                } else {
                    List {
                        ForEach(viewModel.deadGold) { asset in
                            HStack {
                                Image(systemName: icon(for: asset.type))
                                    .foregroundColor(Theme.accent)
                                    .frame(width: 30)
                                VStack(alignment: .leading) {
                                    Text(asset.filename).font(.headline).foregroundColor(Theme.textPrimary)
                                    Text("Created: \(asset.creationDate, style: .date)")
                                        .font(.caption)
                                        .foregroundColor(Theme.textMuted)
                                }
                                Spacer()
                                VStack(alignment: .trailing) {
                                    Text(String(format: "$%.2f", asset.monetizationValue))
                                        .font(.system(.body, design: .monospaced).weight(.bold))
                                        .foregroundColor(Theme.accent)
                                    if let enumTags = asset.tags.first {
                                        Text(enumTags).font(.caption).foregroundColor(Theme.textSecondary)
                                    }
                                }
                            }
                            .listRowBackground(Theme.surface)
                        }
                    }
                    .listStyle(PlainListStyle())
                }
            }
            .padding()
        }
    }
    
    private func icon(for type: AssetType) -> String {
        switch type {
        case .audio: return "waveform"
        case .image: return "photo.fill"
        case .video: return "video.fill"
        case .text: return "doc.text.fill"
        case .project: return "cube.box.fill"
        case .unknown: return "questionmark.folder"
        }
    }
}
