import SwiftUI

public struct SidebarView: View {
    @Binding public var selection: String?
    
    public var body: some View {
        List {
            Section(header: Text("STUDIO").foregroundColor(Theme.textMuted)) {
                NavigationLink(destination: VaultScanView(), tag: "scan", selection: $selection) {
                    Label("Vault Scan", systemImage: "waveform.path.ecg")
                }
                NavigationLink(destination: MonetizeView(), tag: "monetize", selection: $selection) {
                    Label("Monetize", systemImage: "bitcoinsign.circle.fill")
                }
            }
            
            Section(header: Text("VALUE EXTRACTION").foregroundColor(Theme.textMuted)) {
                NavigationLink(destination: DeadGoldView(), tag: "deadgold", selection: $selection) {
                    Label("Dead Gold", systemImage: "sparkles")
                        .foregroundColor(Theme.accent)
                }
                NavigationLink(destination: Text("Identity Map (WIP)").foregroundColor(Theme.textPrimary), tag: "identity", selection: $selection) {
                    Label("Identity Map", systemImage: "network")
                }
            }
        }
        .listStyle(SidebarListStyle())
        .background(Theme.surface)
    }
}
