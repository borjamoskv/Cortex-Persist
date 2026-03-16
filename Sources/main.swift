import SwiftUI
import AppKit

extension Color {
    static let cyberLime = Color(red: 0xCC / 255.0, green: 0xFF / 255.0, blue: 0x00 / 255.0)
    static let darkBase = Color(white: 0.05)
    static let panelBg = Color(white: 0.1).opacity(0.8)
}

struct VisualEffectView: NSViewRepresentable {
    var material: NSVisualEffectView.Material
    var blendingMode: NSVisualEffectView.BlendingMode

    func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.material = material
        view.blendingMode = blendingMode
        view.state = .active
        return view
    }

    func updateNSView(_ nsView: NSVisualEffectView, context: Context) {
        nsView.material = material
        nsView.blendingMode = blendingMode
    }
}

@main
struct CortexDashApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 1000, minHeight: 700)
                .background(VisualEffectView(material: .hudWindow, blendingMode: .behindWindow))
        }
        .windowStyle(HiddenTitleBarWindowStyle())
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        if let window = NSApplication.shared.windows.first {
            window.titlebarAppearsTransparent = true
            window.isOpaque = false
            window.backgroundColor = .clear
            window.isMovableByWindowBackground = true
        }
    }
}

// MARK: - Views

struct ContentView: View {
    @State private var timeOffset = 0.0
    
    let timer = Timer.publish(every: 0.05, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            // Animated background layer
            ScannerBackground(tick: timeOffset)
            
            VStack(spacing: 24) {
                // Header
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("CORTEX-PERSIST OS")
                            .font(.system(size: 24, weight: .black, design: .monospaced))
                            .foregroundColor(.white)
                        Text("MOSKV-1 V5 SOVEREIGN DASHBOARD")
                            .font(.system(size: 12, weight: .bold, design: .monospaced))
                            .foregroundColor(.cyberLime)
                    }
                    Spacer()
                    
                    HStack(spacing: 16) {
                        StatusIndicator(label: "UPlink", isGood: true)
                        StatusIndicator(label: "Encrypt", isGood: true)
                        StatusIndicator(label: "Mem Shard", isGood: false)
                    }
                }
                .padding()
                
                // Main Grid
                HStack(spacing: 24) {
                    // Left Column
                    VStack(spacing: 24) {
                        MetricPanel(title: "GLOBAL ENTROPY", value: "24.5%", sparkline: true)
                        ListPanel(title: "ACTIVE AGENTS", items: ["Azkartu - Opt Loop", "Josu - Ghost Sniper", "Nyx - PPenTest", "Ariadne - Topology"])
                    }
                    
                    // Center Column (Large Map / Diagram)
                    VStack {
                        ArchMapPanel(tick: timeOffset)
                    }
                    .frame(maxWidth: .infinity)
                    
                    // Right Column
                    VStack(spacing: 24) {
                        MetricPanel(title: "AXIOM Ω₁₃ YIELD", value: "124,050h", sparkline: false)
                        TerminalPanel(tick: timeOffset)
                    }
                }
            }
            .padding(32)
        }
        .onReceive(timer) { _ in
            timeOffset += 0.05
        }
        .preferredColorScheme(.dark)
    }
}

struct ScannerBackground: View {
    var tick: Double
    var body: some View {
        GeometryReader { geom in
            let y = CGFloat(sin(tick * 0.5) * 0.5 + 0.5) * geom.size.height
            Rectangle()
                .fill(LinearGradient(
                    gradient: Gradient(colors: [.clear, Color.cyberLime.opacity(0.15), .clear]),
                    startPoint: .top,
                    endPoint: .bottom
                ))
                .frame(height: 100)
                .position(x: geom.size.width / 2, y: y)
                .blendMode(.screen)
        }
        .allowsHitTesting(false)
    }
}

struct StatusIndicator: View {
    var label: String
    var isGood: Bool
    @State private var blink = false
    
    var body: some View {
        HStack {
            Circle()
                .fill(isGood ? Color.cyberLime : Color.red)
                .frame(width: 8, height: 8)
                .opacity(blink && !isGood ? 0.3 : 1.0)
                .shadow(color: isGood ? .cyberLime : .red, radius: 4)
                .onAppear {
                    if !isGood {
                        withAnimation(Animation.easeInOut(duration: 0.5).repeatForever()) {
                            blink.toggle()
                        }
                    }
                }
            Text(label.uppercased())
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(.gray)
        }
    }
}

struct MetricPanel: View {
    var title: String
    var value: String
    var sparkline: Bool
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(.gray)
            
            Text(value)
                .font(.system(size: 48, weight: .regular, design: .monospaced))
                .foregroundColor(.white)
                .glow(color: .white.opacity(0.2), radius: 10)
            
            if sparkline {
                // Fake sparkline
                HStack(alignment: .bottom, spacing: 4) {
                    ForEach(0..<15) { i in
                        RoundedRectangle(cornerRadius: 2)
                            .fill(Color.cyberLime.opacity(Double.random(in: 0.3...1.0)))
                            .frame(width: 8, height: CGFloat.random(in: 10...40))
                    }
                }
                .frame(height: 40)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.panelBg)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.white.opacity(0.1), lineWidth: 1)
        )
    }
}

struct ListPanel: View {
    var title: String
    var items: [String]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(title)
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(.gray)
            
            VStack(alignment: .leading, spacing: 12) {
                ForEach(items, id: \.self) { item in
                    HStack {
                        Rectangle()
                            .fill(Color.cyberLime)
                            .frame(width: 4, height: 16)
                        Text(item)
                            .font(.system(size: 13, design: .monospaced))
                            .foregroundColor(.white)
                    }
                }
            }
            Spacer()
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.panelBg)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.white.opacity(0.1), lineWidth: 1)
        )
    }
}

struct ArchMapPanel: View {
    var tick: Double
    
    var body: some View {
        VStack {
            Text("MEMORY TOPOLOGY DIAGNOSTICS")
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(.gray)
                .padding(.top)
            
            ZStack {
                // Central Node
                Circle()
                    .strokeBorder(Color.cyberLime, lineWidth: 2)
                    .frame(width: 100, height: 100)
                    .background(Circle().fill(Color.cyberLime.opacity(0.1)))
                    .shadow(color: .cyberLime, radius: CGFloat(abs(sin(tick)) * 10))
                Text("GHOST\nCORE")
                    .multilineTextAlignment(.center)
                    .font(.system(size: 12, weight: .black, design: .monospaced))
                    .foregroundColor(.white)
                
                // Orbiting Nodes
                ForEach(0..<6) { i in
                    let angle = Double(i) * (.pi * 2 / 6) + tick * 0.5
                    let x = cos(angle) * 120
                    let y = sin(angle) * 120
                    
                    Circle()
                        .fill(Color.white)
                        .frame(width: 12, height: 12)
                        .offset(x: CGFloat(x), y: CGFloat(y))
                        .shadow(color: .white, radius: 5)
                    
                    // Connecting lines (approximation)
                    Path { path in
                        path.move(to: CGPoint(x: 150, y: 150))
                        path.addLine(to: CGPoint(x: 150 + x, y: 150 + y))
                    }
                    .stroke(Color.cyberLime.opacity(0.3), style: StrokeStyle(lineWidth: 1, dash: [5, 5]))
                    .frame(width: 300, height: 300)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .background(Color.panelBg)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.white.opacity(0.1), lineWidth: 1)
        )
    }
}

struct TerminalPanel: View {
    var tick: Double
    let logs = [
        "> init cortex_persist --verify",
        "  [OK] Hash continuity checked",
        "> immune-chaos invoke",
        "  [WARN] Drift detected in module auth",
        "> autodidact-omega compile",
        "  [OK] Axioms crystallized",
        "> nyx-redteam payload inject",
        "  [OK] Surface breached",
        "> standby..."
    ]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("RUNTIME LEDGER")
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(.gray)
                .padding(.bottom, 8)
            
            ForEach(0..<min(Int(tick * 2) % (logs.count + 5), logs.count), id: \.self) { i in
                Text(logs[i])
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundColor(logs[i].contains("[WARN]") ? .red : (logs[i].contains("[OK]") ? .cyberLime : .white))
            }
            Spacer()
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.darkBase)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.white.opacity(0.1), lineWidth: 1)
        )
    }
}

extension View {
    func glow(color: Color = .red, radius: CGFloat = 20) -> some View {
        self.shadow(color: color, radius: radius / 3)
            .shadow(color: color, radius: radius / 3)
            .shadow(color: color, radius: radius / 3)
    }
}
