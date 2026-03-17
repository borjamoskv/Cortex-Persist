import SwiftUI

public struct ContentView: View {
    @StateObject private var viewModel = StudioViewModel()
    @State private var selection: String? = "scan"
    
    public var body: some View {
        NavigationView {
            SidebarView(selection: $selection)
            
            // Default view if nothing selected
            VaultScanView()
        }
        .environmentObject(viewModel)
        .preferredColorScheme(.dark) // Force dark mode strictly
    }
}
