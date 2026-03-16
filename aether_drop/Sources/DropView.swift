import Cocoa

class DropView: NSView {
    var onDrop: (([URL]) -> Void)?
    
    override init(frame: NSRect) {
        super.init(frame: frame)
        // Register for file URLs
        registerForDraggedTypes([.fileURL])
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    // Pass mouse events to the parent NSStatusBarButton
    override func mouseDown(with event: NSEvent) {
        if let parent = superview {
            parent.mouseDown(with: event)
        }
    }
    
    override func mouseUp(with event: NSEvent) {
        if let parent = superview {
            parent.mouseUp(with: event)
        }
    }
    
    override func rightMouseDown(with event: NSEvent) {
        if let parent = superview {
            parent.rightMouseDown(with: event)
        }
    }

    override func draggingEntered(_ sender: NSDraggingInfo) -> NSDragOperation {
        let pasteboard = sender.draggingPasteboard
        if pasteboard.canReadItem(withDataConformingToTypes: ["public.file-url"]) {
            // Optional: visually highlight the drop area here if we want
            return .copy
        }
        return []
    }
    
    override func performDragOperation(_ sender: NSDraggingInfo) -> Bool {
        guard let items = sender.draggingPasteboard.pasteboardItems else { return false }
        var urls: [URL] = []
        for item in items {
            if let stringURL = item.string(forType: .fileURL), let url = URL(string: stringURL) {
                urls.append(url)
            }
        }
        
        if urls.isEmpty { return false }
        
        onDrop?(urls)
        return true
    }
}
