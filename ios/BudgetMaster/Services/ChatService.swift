import Foundation

public enum ChatService {

    /// POST /chat/stream (SSE)
    /// Returns an `AsyncThrowingStream` of `ChatStreamEvent` values.
    public static func streamChat(
        message: String,
        conversationId: String? = nil
    ) -> AsyncThrowingStream<ChatStreamEvent, Error> {
        SSEClient.stream(message: message, conversationId: conversationId)
    }

    /// POST /mcp/process_expense (multipart form-data)
    public static func processExpense(
        text: String? = nil,
        imageData: Data? = nil,
        imageMimeType: String? = nil,
        audioData: Data? = nil,
        audioFileName: String? = nil,
        conversationId: String? = nil
    ) async throws -> ExpenseProcessResponse {
        var form = MultipartFormData()

        if let text {
            form.addTextField(name: "text", value: text)
        }

        if let imageData, let mimeType = imageMimeType {
            let ext = mimeType == "image/png" ? "png" : "jpg"
            form.addFileField(
                name: "image",
                fileName: "receipt.\(ext)",
                mimeType: mimeType,
                data: imageData
            )
        }

        if let audioData {
            let fileName = audioFileName ?? "recording.webm"
            form.addFileField(
                name: "audio",
                fileName: fileName,
                mimeType: "audio/webm",
                data: audioData
            )
        }

        if let conversationId {
            form.addTextField(name: "conversation_id", value: conversationId)
        }

        let endpoint = APIEndpoint(method: .post, path: "/mcp/process_expense")
        return try await APIClient.shared.upload(endpoint, multipart: form)
    }
}
