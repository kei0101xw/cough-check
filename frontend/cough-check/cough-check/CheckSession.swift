import AVFoundation
import Combine
import Foundation

@MainActor
final class CheckSession: NSObject, ObservableObject, AVAudioRecorderDelegate {
    enum Screen { case home, recording, result }
    @Published var screen: Screen = .home
    @Published var isRecording = false
    @Published var isRequestingPermission = false
    @Published var isAnalyzing = false
    @Published var result: AnalysisResult?
    @Published var error: String?
    @Published var startedAt: Date?
    @Published private(set) var audioLevel: Double = 0

    private var meteringTask: Task<Void, Never>?
    private var recorder: AVAudioRecorder?
    private var recordingURL: URL?
    private var analysisTask: Task<Void, Never>?
    private var generation = UUID()

    func goToRecording() async {
        guard !isRequestingPermission else { return }
        reset()
        guard await ensureMicrophonePermission() else { return }
        screen = .recording
    }

    func goHome() {
        reset()
        screen = .home
    }

    private func ensureMicrophonePermission() async -> Bool {
        error = nil
        isRequestingPermission = true
        let current = generation
        let granted = await AVAudioApplication.requestRecordPermission()
        guard generation == current else { return false }
        isRequestingPermission = false
        guard granted else {
            error = "マイクが許可されていません。iPhoneの設定で、このアプリのマイクを許可してください。"
            return false
        }
        return true
    }

    func start() async {
        guard !isRecording, !isRequestingPermission else { return }
        guard await ensureMicrophonePermission() else { return }
        do {
            let audio = AVAudioSession.sharedInstance()
            try audio.setCategory(.record, mode: .measurement)
            try audio.setActive(true)
            let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".wav")
            recordingURL = url
            let recorder = try AVAudioRecorder(url: url, settings: [
                AVFormatIDKey: kAudioFormatLinearPCM,
                AVSampleRateKey: 44100,
                AVNumberOfChannelsKey: 1,
                AVLinearPCMBitDepthKey: 16,
                AVLinearPCMIsFloatKey: false,
                AVLinearPCMIsBigEndianKey: false
            ])
            recorder.isMeteringEnabled = true
            recorder.delegate = self
            self.recorder = recorder
            guard recorder.record() else { throw CheckError.message("録音を開始できませんでした。") }
            startedAt = .now
            isRecording = true
            startMetering()
        } catch {
            discardRecording()
            self.error = "録音を開始できませんでした。マイクの接続を確認してお試しください。"
        }
    }

    func stopAndAnalyze() {
        guard isRecording, let url = recordingURL else { return }
        isRecording = false
        stopMetering()
        recorder?.stop()
        recorder = nil
        deactivateAudio()
        screen = .result
        isAnalyzing = true
        let current = generation
        analysisTask = Task {
            defer {
                if generation == current { isAnalyzing = false }
            }
            do {
                let response = try await AnalysisClient().analyze(file: url)
                try Task.checkCancellation()
                guard generation == current else { return }
                result = response
            } catch {
                guard !Task.isCancelled, generation == current else { return }
                self.error = (error as? CheckError)?.errorDescription
                    ?? "サーバーに接続できませんでした。通信環境を確認して、もう一度お試しください。"
            }
            if generation == current { discardRecording() }
        }
    }

    func interruptRecording() {
        guard isRecording || isRequestingPermission else { return }
        generation = UUID()
        isRequestingPermission = false
        discardRecording()
        error = "録音が中断されました。もう一度、録音を開始してください。"
    }

    nonisolated func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        handleRecorderInterruption(ObjectIdentifier(recorder))
    }

    nonisolated func audioRecorderEncodeErrorDidOccur(_ recorder: AVAudioRecorder, error: Error?) {
        handleRecorderInterruption(ObjectIdentifier(recorder))
    }

    private nonisolated func handleRecorderInterruption(_ identifier: ObjectIdentifier) {
        Task { @MainActor [weak self] in
            guard let self, let recorder = self.recorder,
                  ObjectIdentifier(recorder) == identifier else { return }
            self.interruptRecording()
        }
    }

    private func reset() {
        generation = UUID()
        analysisTask?.cancel()
        analysisTask = nil
        discardRecording()
        isRequestingPermission = false
        isAnalyzing = false
        result = nil
        error = nil
    }

    private func discardRecording() {
        isRecording = false
        stopMetering()
        recorder?.stop()
        recorder = nil
        startedAt = nil
        deactivateAudio()
        if let recordingURL { try? FileManager.default.removeItem(at: recordingURL) }
        recordingURL = nil
    }

    private func startMetering() {
        stopMetering()
        meteringTask = Task { @MainActor [weak self] in
            while !Task.isCancelled {
                self?.updateAudioLevel()
                do {
                    try await Task.sleep(for: .milliseconds(33))
                } catch {
                    break
                }
                guard self != nil else { break }
            }
        }
    }

    private func updateAudioLevel() {
        guard isRecording, let recorder else { return }
        recorder.updateMeters()
        let decibels = Double(recorder.averagePower(forChannel: 0))
        // Ignore the noise floor; preserve a larger response for louder input.
        let normalized = min(1, max(0, (decibels + 55) / 50))
        let target = pow(normalized, 1.7)
        // Fast attack follows a cough; slower release avoids abrupt collapse.
        let smoothing = target > audioLevel ? 0.4 : 0.12
        audioLevel += (target - audioLevel) * smoothing
    }

    private func stopMetering() {
        meteringTask?.cancel()
        meteringTask = nil
        audioLevel = 0
    }

    private func deactivateAudio() {
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }
}
