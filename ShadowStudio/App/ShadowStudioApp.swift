import SwiftUI

@main
struct ShadowStudioApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 900, minHeight: 600)
                .background(Theme.background)
        }
        .windowStyle(HiddenTitleBarWindowStyle()) // Noir aesthetic: hide standard title bar
        .commands {
            SidebarCommands()
        }
    }
}
