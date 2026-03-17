import Cocoa
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var popover: NSPopover!
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Initialize Popover
        popover = NSPopover()
        popover.contentSize = NSSize(width: 300, height: 400)
        popover.behavior = .transient
        
        // This view will be replaced with our custom Notch overlay
        let hostingController = NSHostingController(rootView: Text("Aether Drop UI"))
        popover.contentViewController = hostingController
        
        // Initialize Status Item
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "bag.circle.fill", accessibilityDescription: "Aether Drop")
            button.action = #selector(togglePopover(_:))
            
            // Add Drag and Drop overlay
            let dropView = DropView(frame: button.bounds)
            dropView.autoresizingMask = [.width, .height]
            dropView.onDrop = { [weak self] urls in
                self?.handleFileDrop(urls)
            }
            button.addSubview(dropView)
        }
        
        print("Aether Drop started.")
    }
    
    func handleFileDrop(_ urls: [URL]) {
        print("Dropped files: \(urls)")
        // Bring app to front and optionally show popover with state "Uploading..."
        NSApp.activate(ignoringOtherApps: true)
        if !popover.isShown {
            showPopover(statusItem.button)
        }
    }
    
    @objc func togglePopover(_ sender: Any?) {
        if popover.isShown {
            closePopover(sender)
        } else {
            showPopover(sender)
        }
    }
    
    func showPopover(_ sender: Any?) {
        if let button = statusItem.button {
            // Bring app to front
            NSApp.activate(ignoringOtherApps: true)
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: NSRectEdge.minY)
        }
    }
    
    func closePopover(_ sender: Any?) {
        popover.performClose(sender)
    }
}
