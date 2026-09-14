import AVFoundation
import SwiftUI

struct ContentView: View {
    @StateObject private var session = CheckSession()
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ZStack {
            Color.blue.ignoresSafeArea()
            switch session.screen {
            case .home: home
            case .recording: recording
            case .result: result
            }
        }
        .preferredColorScheme(.light)
        .onChange(of: scenePhase) { _, phase in
            if phase == .background { session.interruptRecording() }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { _ in
            session.interruptRecording()
        }
    }

    private var home: some View {
        VStack(spacing: 0) {
            Spacer()
            VStack(spacing: 15) {
                Text("-咳の音から感染症リスクを判定するアプリ-")
                    .font(.system(size: 13))
                    .multilineTextAlignment(.center)
                    .bold()
                ViewThatFits {
                    HStack(spacing: 7) {
                        Image(systemName: "waveform").font(.system(size: 48))
                        Text("Cough Check").font(.system(size: 32, weight: .bold))
                    }
                    VStack(spacing: 16) {
                        Image(systemName: "waveform").font(.system(size: 48))
                        Text("Cough Check").font(.largeTitle.bold())
                    }
                }
            }
            .foregroundStyle(.white)
            .padding(24)
            Spacer()
            panel {
                VStack(spacing: 16) {
                    action(session.isRequestingPermission ? "マイクを確認中…" : "感染症リスクをチェックする", icon: "mic.fill") {
                        Task { await session.goToRecording() }
                    }
                    .disabled(session.isRequestingPermission)
                    if let error = session.error {
                        Text(error)
                            .foregroundStyle(.red)
                            .multilineTextAlignment(.center)
                    }
                }
                .padding(.vertical, 60)
            }
        }
    }

    private var recording: some View {
        VStack(spacing: 0) {
            header("咳の録音", onBack: session.goHome, isBackDisabled: session.isRecording)
            ScrollView {
                VStack(spacing: 24) {
                    // 両方の案内文の高さを確保し、録音開始時の位置ずれを防ぐ。
                    ZStack(alignment: .top) {
                        ForEach([false, true], id: \.self) { isRecording in
                            VStack(spacing: 24) {
                                Text(isRecording ? "録音中" : "録音を開始してください")
                                    .font(.title2)
                                Text(isRecording ? "咳の録音が終わったら、停止してください。" : "静かな場所で、スマートフォンに向かって\n咳を録音してください。")
                                    .font(.body)
                                    .foregroundStyle(.secondary)
                                    .multilineTextAlignment(.center)
                            }
                            .opacity(session.isRecording == isRecording ? 1 : 0)
                            .accessibilityHidden(session.isRecording != isRecording)
                        }
                    }
                    CircularAudioVisualizer(
                        level: session.audioLevel,
                        isRecording: session.isRecording
                    )
                    if let start = session.startedAt, session.isRecording {
                        Text(start, style: .timer)
                            .font(.system(size: 32, weight: .medium, design: .monospaced))
                            .foregroundStyle(.blue)
                            .accessibilityLabel("録音時間")
                    } else {
                        Text("00:00").font(.system(size: 32, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    if let error = session.error {
                        Text(error).foregroundStyle(.red).multilineTextAlignment(.center)
                    }
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 36)
                .frame(maxWidth: .infinity)
            }
            .background(.white)
            VStack(spacing: 16) {
                action(
                    session.isRequestingPermission ? "マイクを確認中…" : session.isRecording ? "停止して判定する" : "録音開始",
                    icon: session.isRecording ? "stop.fill" : "mic.fill",
                    color: session.isRecording ? .red : .blue
                ) {
                    if session.isRecording { session.stopAndAnalyze() }
                    else { Task { await session.start() } }
                }
                .disabled(session.isRequestingPermission)
            }
            .padding(24)
            .background(.white)
        }
        .background(.white)
    }

    private var result: some View {
        VStack(spacing: 0) {
            header("判定結果")
            ScrollView {
                VStack(spacing: 28) {
                    if session.isAnalyzing {
                        ProgressView().controlSize(.large).tint(.blue)
                        Text("咳の音を解析しています").font(.title2)
                        Text("そのまましばらくお待ちください。").foregroundStyle(.secondary)
                    } else if let result = session.result, let score = result.averagePositiveScore {
                        Text("感染症リスクスコア").font(.title2)
                        ScoreGauge(score: score)
                        Text("解析した咳：\(result.coughCount)回").foregroundStyle(.secondary)
                        Text("この数値はAIモデルの推定スコアです。\n実際の感染確率や診断を示すものではありません。")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    } else {
                        Image(systemName: session.error == nil ? "waveform.slash" : "exclamationmark.circle")
                            .font(.system(size: 56)).foregroundStyle(.blue)
                        Text(session.error == nil ? "咳が検出されませんでした" : "判定できませんでした")
                            .font(.title2)
                        Text(session.error ?? "もう一度、咳の音を録音してください。")
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.horizontal, 24)
                .padding(.vertical, 48)
            }
            .background(.white)
            VStack(spacing: 14) {
                action("もう一度判定する", icon: "arrow.clockwise") {
                    Task { await session.goToRecording() }
                }
                .disabled(session.isRequestingPermission)
                Button(action: session.goHome) {
                    Text("ホームに戻る")
                        .font(.headline)
                        .frame(maxWidth: .infinity, minHeight: 56)
                        .background(Color.gray.opacity(0.15), in: RoundedRectangle(cornerRadius: 15))
                }
                .buttonStyle(.plain)
            }
            .padding(24)
            .background(.white)
        }
        .background(.white)
    }

    private func header(_ title: String, onBack: (() -> Void)? = nil, isBackDisabled: Bool = false) -> some View {
        Text(title)
            .font(.title2.weight(.semibold))
            .foregroundStyle(.white)
            .padding(.horizontal, 64)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 24)
            .overlay(alignment: .leading) {
                if let onBack {
                    Button(action: onBack) {
                        Image(systemName: "chevron.left")
                            .font(.title2.weight(.semibold))
                            .foregroundStyle(.white)
                            .frame(width: 44, height: 44)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("ホームに戻る")
                    .disabled(isBackDisabled)
                    .opacity(isBackDisabled ? 0.35 : 1)
                    .padding(.leading, 12)
                }
            }
            .background(Color.blue)
    }

    private func panel<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        content()
            .padding(.horizontal, 28)
            .frame(maxWidth: .infinity)
            .background {
                UnevenRoundedRectangle(topLeadingRadius: 20, topTrailingRadius: 20)
                    .fill(.white)
                    .ignoresSafeArea(edges: .bottom)
            }
    }

    private func action(_ title: String, icon: String, color: Color = .blue, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Text(title).font(.headline)
                Image(systemName: icon)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 16)
            .frame(maxWidth: .infinity, minHeight: 56)
            .foregroundStyle(.white)
            .background(color, in: RoundedRectangle(cornerRadius: 15))
        }
        .buttonStyle(.plain)
    }
}

struct ScoreGauge: View {
    let score: Double

    var body: some View {
        ZStack {
            Circle().stroke(Color.blue.opacity(0.1), lineWidth: 18)
            Circle()
                .trim(from: 0, to: score)
                .stroke(Color.blue, style: StrokeStyle(lineWidth: 18, lineCap: .round))
                .rotationEffect(.degrees(-90))
            Text(score, format: .percent.precision(.fractionLength(1)))
                .font(.system(size: 44, weight: .semibold, design: .rounded))
                .minimumScaleFactor(0.6)
                .padding(24)
        }
        .frame(width: 220, height: 220)
        .padding(10)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("感染症リスクスコア")
        .accessibilityValue(score.formatted(.percent.precision(.fractionLength(1))))
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View { ContentView() }
}

struct ScoreGauge_Previews: PreviewProvider {
    static var previews: some View { ScoreGauge(score: 0.725) }
}
