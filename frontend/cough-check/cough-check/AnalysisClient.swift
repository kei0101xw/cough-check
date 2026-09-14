import Foundation

struct AnalysisResult: Decodable {
    let coughCount: Int
    let averagePositiveScore: Double?

    enum CodingKeys: String, CodingKey {
        case coughCount = "cough_count"
        case averagePositiveScore = "average_positive_score"
    }
}

enum CheckError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        switch self { case .message(let text): text }
    }
}

struct AnalysisClient {
    func analyze(file: URL) async throws -> AnalysisResult {
        let configured = ProcessInfo.processInfo.environment["COUGH_API_URL"]
            ?? Bundle.main.object(forInfoDictionaryKey: "CoughAPIURL") as? String
        guard let configured, let url = URL(string: configured),
              ["http", "https"].contains(url.scheme ?? ""), url.host != nil else {
            throw CheckError.message("APIの接続先が設定されていません。")
        }
        let boundary = UUID().uuidString
        var body = Data()
        body.append(Data("--\(boundary)\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"cough.wav\"\r\nContent-Type: audio/wav\r\n\r\n".utf8))
        body.append(try Data(contentsOf: file))
        body.append(Data("\r\n--\(boundary)--\r\n".utf8))
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 120
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await URLSession.shared.upload(for: request, from: body)
        guard let http = response as? HTTPURLResponse else {
            throw CheckError.message("サーバーからの応答を確認できませんでした。")
        }
        guard (200..<300).contains(http.statusCode) else {
            let message: String
            switch http.statusCode {
            case 413: message = "録音データが大きすぎます。短めに録音し直してください。"
            case 400, 415, 422: message = "音声を解析できませんでした。もう一度録音してください。"
            case 503: message = "解析サーバーの準備ができていません。時間をおいてお試しください。"
            default: message = "解析に失敗しました（\(http.statusCode)）。時間をおいてお試しください。"
            }
            throw CheckError.message(message)
        }
        let result = try JSONDecoder().decode(AnalysisResult.self, from: data)
        guard result.coughCount >= 0,
              (result.coughCount == 0 && result.averagePositiveScore == nil)
                || (result.coughCount > 0 && result.averagePositiveScore.map { $0.isFinite && (0...1).contains($0) } == true) else {
            throw CheckError.message("解析結果の形式が正しくありません。")
        }
        return result
    }
}
