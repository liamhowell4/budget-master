import Foundation

/// Parses Server-Sent Events from `/chat/stream` into typed `ChatStreamEvent` values.
enum SSEClient {

    /// Stream chat events from the backend SSE endpoint.
    static func stream(
        message: String,
        conversationId: String? = nil
    ) -> AsyncThrowingStream<ChatStreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let endpoint = APIEndpoint(
                        method: .post,
                        path: "/chat/stream"
                    )
                    let body = ChatRequest(message: message, conversationId: conversationId)
                    let (bytes, response) = try await APIClient.shared.streamRequest(endpoint, body: body)

                    // Validate HTTP status
                    if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                        continuation.finish(throwing: APIError.serverError(
                            statusCode: http.statusCode,
                            message: "SSE connection failed"
                        ))
                        return
                    }

                    var buffer = ""

                    for try await byte in bytes {
                        let char = Character(UnicodeScalar(byte))
                        buffer.append(char)

                        // SSE lines are delimited by \n
                        while let newlineIndex = buffer.firstIndex(of: "\n") {
                            let line = String(buffer[buffer.startIndex..<newlineIndex])
                            buffer = String(buffer[buffer.index(after: newlineIndex)...])

                            if let event = parseLine(line) {
                                switch event {
                                case .done:
                                    continuation.finish()
                                    return
                                case .error(let msg):
                                    continuation.finish(throwing: APIError.sseParsingError(msg))
                                    return
                                default:
                                    continuation.yield(event)
                                }
                            }
                        }
                    }

                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }

            continuation.onTermination = { _ in
                task.cancel()
            }
        }
    }

    // MARK: - Line Parsing

    private static func parseLine(_ line: String) -> ChatStreamEvent? {
        guard line.hasPrefix("data: ") else { return nil }

        let data = String(line.dropFirst(6))

        if data == "[DONE]" {
            return .done
        }

        if data.hasPrefix("[ERROR]") {
            let message = String(data.dropFirst(7)).trimmingCharacters(in: .whitespaces)
            return .error(message)
        }

        // Parse JSON event
        guard let jsonData = data.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any],
              let type = json["type"] as? String
        else {
            // Non-JSON text chunk
            if !data.trimmingCharacters(in: .whitespaces).isEmpty {
                return .text(data)
            }
            return nil
        }

        switch type {
        case "conversation_id":
            if let id = json["conversation_id"] as? String {
                return .conversationId(id)
            }
        case "tool_start":
            let id = json["id"] as? String ?? ""
            let name = json["name"] as? String ?? ""
            let args = json["args"] as? [String: Any] ?? [:]
            return .toolStart(id: id, name: name, args: args)
        case "tool_end":
            let id = json["id"] as? String ?? ""
            let name = json["name"] as? String ?? ""
            let result = json["result"] ?? ""
            return .toolEnd(id: id, name: name, result: result)
        case "text":
            let content = json["content"] as? String ?? ""
            return .text(content)
        default:
            break
        }

        return nil
    }
}
