import SwiftUI

public struct VaultScanView: View {
    @EnvironmentObject var viewModel: StudioViewModel
    @State private var isTargeted = false
    
    public var body: some View {
        ZStack {
            Theme.background.edgesIgnoringSafeArea(.all)
            
            VStack(spacing: 40) {
                Text("SHADOW STUDIO")
                    .font(.system(size: 42, weight: .heavy, design: .monospaced))
                    .foregroundColor(Theme.textPrimary)
                    .tracking(2.0)
                
                if viewModel.rawAssets.isEmpty {
                    dropZone
                } else {
                    scanResults
                }
            }
            .padding()
        }
    }
    
    private var dropZone: some View {
        VStack(spacing: 20) {
            Image(systemName: "folder.badge.gearshape")
                .font(.system(size: 80))
                .foregroundColor(isTargeted ? Theme.accent : Theme.textMuted)
            
            Text(viewModel.scanProgress)
                .font(.system(.body, design: .monospaced))
                .foregroundColor(Theme.textSecondary)
            
            Button("Select Folder / Drop Here") {
                // Mocking folder selection
                let mockURL = URL(fileURLWithPath: "/Users/creative/Desktop/Old_Projects")
                viewModel.ingestFolder(url: mockURL)
            }
            .neoButton()
            .disabled(viewModel.isAnalyzing)
        }
        .frame(width: 400, height: 300)
        .background(Theme.surface)
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(isTargeted ? Theme.accent : Theme.surfaceHighlight, style: StrokeStyle(lineWidth: 2, dash: [10]))
        )
        // Note: macOS Drag and Drop implementations would attach via .onDrop() here
    }
    
    private var scanResults: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("SCAN COMPLETE")
                .font(.headline)
                .foregroundColor(Theme.accent)
            
            HStack(spacing: 40) {
                metricView(title: "TOTAL ASSETS", value: "\(viewModel.rawAssets.count)")
                metricView(title: "ESTIMATED VALUE", value: String(format: "$%.2f", viewModel.totalValueExtracted))
                metricView(title: "UNIVERSES DETECTED", value: "\(viewModel.clusters.count)")
            }
            
            Divider().background(Theme.textMuted)
            
            Text("Asset Clusters")
                .font(.subheadline)
                .foregroundColor(Theme.textSecondary)
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 20) {
                    ForEach(viewModel.clusters) { cluster in
                        VStack(alignment: .leading) {
                            Text(cluster.name).font(.headline).foregroundColor(Theme.textPrimary)
                            Text("\(cluster.assets.count) items").font(.caption).foregroundColor(Theme.textMuted)
                            Text(cluster.description).font(.caption).foregroundColor(Theme.textSecondary).padding(.top, 4)
                        }
                        .padding()
                        .frame(width: 250, height: 120, alignment: .topLeading)
                        .background(Theme.surfaceHighlight)
                        .cornerRadius(6)
                        .overlay(Rectangle().frame(width: 4).foregroundColor(Theme.accent), alignment: .leading)
                    }
                }
            }
            
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
    }
    
    private func metricView(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.system(.caption, design: .monospaced)).foregroundColor(Theme.textMuted)
            Text(value).font(.system(.title2, design: .monospaced).weight(.bold)).foregroundColor(Theme.textPrimary)
        }
    }
}
