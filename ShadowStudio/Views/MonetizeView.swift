import SwiftUI

public struct MonetizeView: View {
    @EnvironmentObject var viewModel: StudioViewModel
    
    public var body: some View {
        ZStack {
            Theme.background.edgesIgnoringSafeArea(.all)
            
            VStack(alignment: .leading, spacing: 20) {
                Text("MONETIZE")
                    .font(.system(size: 32, weight: .heavy, design: .monospaced))
                    .foregroundColor(Theme.textPrimary)
                
                Text("Genera productos y pipelines directos a e-commerce a partir de tu archivo.")
                    .foregroundColor(Theme.textSecondary)
                
                if viewModel.packCandidates.isEmpty {
                    Spacer()
                    Text("NO PACK CANDIDATES DETECTED.")
                        .font(.system(.body, design: .monospaced))
                        .foregroundColor(Theme.textMuted)
                        .frame(maxWidth: .infinity, alignment: .center)
                    Spacer()
                } else {
                    ScrollView {
                        VStack(spacing: 20) {
                            ForEach(viewModel.packCandidates) { pack in
                                packRow(pack)
                            }
                        }
                    }
                }
            }
            .padding()
        }
    }
    
    private func packRow(_ pack: PackCandidate) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(pack.title)
                    .font(.title3.weight(.bold))
                    .foregroundColor(Theme.textPrimary)
                Spacer()
                Text(String(format: "$%.2f", pack.estimatedPrice))
                    .font(.system(.headline, design: .monospaced))
                    .foregroundColor(Theme.accent)
            }
            
            Text(pack.type.rawValue.uppercased())
                .font(.caption.weight(.bold))
                .padding(.horizontal, 8).padding(.vertical, 4)
                .background(Theme.surfaceHighlight)
                .foregroundColor(Theme.textMuted)
                .cornerRadius(4)
            
            Text(pack.description)
                .font(.subheadline)
                .foregroundColor(Theme.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
            
            HStack {
                HStack(spacing: 4) {
                    Image(systemName: "square.fill.on.square.fill")
                    Text("\(pack.assets.count) assets")
                }
                .font(.caption)
                .foregroundColor(Theme.textMuted)
                
                Spacer()
                
                Button("Export ZIP") {
                    // Export logic here
                }
                .neoButton()
            }
            .padding(.top, 8)
        }
        .padding()
        .background(Theme.surface)
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8).stroke(Theme.surfaceHighlight, lineWidth: 1)
        )
    }
}
