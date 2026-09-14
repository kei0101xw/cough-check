import SwiftUI

/// The rings represent microphone volume, not frequency bands.
struct CircularAudioVisualizer: View {
    let level: Double
    let isRecording: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var intensity: Double {
        isRecording ? min(1, max(0, level)) : 0
    }

    var body: some View {
        ZStack {
            // Fixed layout bounds keep the timer and controls still as the rings expand.
            ForEach(0..<3) { index in
                let layer = Double(index)
                Circle()
                    .fill(Color.blue.opacity(0.045 + intensity * 0.035))
                    .overlay {
                        Circle()
                            .stroke(Color.blue.opacity(0.12 + intensity * 0.16), lineWidth: 1.5)
                    }
                    .frame(width: 164, height: 164)
                    .scaleEffect(reduceMotion ? 1 + layer * 0.055
                                 : 1 + layer * 0.055 + intensity * (0.15 + layer * 0.16))
            }

            Circle()
                .fill(Color.blue.opacity(0.09))
                .frame(width: 164, height: 164)
                .overlay {
                    Circle().stroke(Color.blue.opacity(0.25), lineWidth: 2)
                }

            Image(systemName: "mic.fill")
                .font(.system(size: 56, weight: .regular))
                .foregroundStyle(.blue)
        }
        .frame(width: 272, height: 272)
        .animation(.linear(duration: 0.1), value: intensity)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(isRecording ? "マイク入力中" : "マイク待機中")
    }
}

struct CircularAudioVisualizer_Previews: PreviewProvider {
    static var previews: some View {
        VStack {
            CircularAudioVisualizer(level: 0.1, isRecording: true)
            CircularAudioVisualizer(level: 0.9, isRecording: true)
        }
    }
}
