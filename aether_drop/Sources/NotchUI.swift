import SwiftUI

class NotchState: ObservableObject {
    static let shared = NotchState()
    @Published var isVisible = false
    @Published var message = ""
    
    func triggerPulse(message: String) {
        self.message = message
        withAnimation(.spring(response: 0.4, dampingFraction: 0.6, blendDuration: 0.1)) {
            self.isVisible = true
        }
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
            withAnimation(.easeInOut(duration: 0.3)) {
                self.isVisible = false
            }
        }
    }
}

struct NotchUI: View {
    @ObservedObject var state = NotchState.shared
    
    var body: some View {
        VStack {
            if state.isVisible {
                ZStack {
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(Color(red: 0.04, green: 0.04, blue: 0.04)) // #0A0A0A (Industrial Noir)
                        .overlay(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .stroke(Color(red: 0.8, green: 1.0, blue: 0.0).opacity(0.5), lineWidth: 1) // #CCFF00 (Cyber Lime)
                        )
                        .shadow(color: Color(red: 0.8, green: 1.0, blue: 0.0).opacity(0.3), radius: 15, x: 0, y: 5)
                    
                    HStack(spacing: 12) {
                        Image(systemName: "link")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(Color(red: 0.8, green: 1.0, blue: 0.0))
                        
                        Text(state.message)
                            .font(.system(size: 13, weight: .bold, design: .monospaced))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 12)
                }
                .frame(height: 44)
                .fixedSize()
                .transition(.move(edge: .top).combined(with: .opacity))
            }
            Spacer()
        }
        .padding(.top, -10) // Pulls slightly up to look like it drops from menu bar
    }
}
