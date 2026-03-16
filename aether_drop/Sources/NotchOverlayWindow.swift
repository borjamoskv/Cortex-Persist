import Cocoa
import SwiftUI

class NotchOverlayWindow: NSWindow {
    static let shared = NotchOverlayWindow()
    
    init() {
        let screenRect = NSScreen.main?.frame ?? NSRect(x: 0, y: 0, width: 1920, height: 1080)
        let windowWidth: CGFloat = 400
        let windowHeight: CGFloat = 100
        
        let overlayRect = NSRect(
            x: screenRect.midX - windowWidth / 2,
            y: screenRect.maxY - windowHeight,
            width: windowWidth,
            height: windowHeight
        )
        
        super.init(
            contentRect: overlayRect,
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        
        self.isOpaque = false
        self.backgroundColor = .clear
        self.level = .screenSaver // High enough to cover typical windows
        self.ignoresMouseEvents = true
        self.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
        
        let hostingView = NSHostingView(rootView: NotchUI())
        self.contentView = hostingView
    }
    
    func showNotchUI() {
        self.makeKeyAndOrderFront(nil)
    }
}
