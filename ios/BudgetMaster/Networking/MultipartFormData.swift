import Foundation

struct MultipartFormData: Sendable {
    private let boundary: String
    private var parts: [(Data, String)] = [] // (partData, name) for bookkeeping
    private var bodyData = Data()

    var contentType: String { "multipart/form-data; boundary=\(boundary)" }

    init(boundary: String = UUID().uuidString) {
        self.boundary = boundary
    }

    /// Append a text field.
    mutating func addTextField(name: String, value: String) {
        bodyData.append("--\(boundary)\r\n")
        bodyData.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n")
        bodyData.append("\(value)\r\n")
    }

    /// Append a file field.
    mutating func addFileField(name: String, fileName: String, mimeType: String, data: Data) {
        bodyData.append("--\(boundary)\r\n")
        bodyData.append("Content-Disposition: form-data; name=\"\(name)\"; filename=\"\(fileName)\"\r\n")
        bodyData.append("Content-Type: \(mimeType)\r\n\r\n")
        bodyData.append(data)
        bodyData.append("\r\n")
    }

    /// Finalize and return the complete body data.
    func finalize() -> Data {
        var result = bodyData
        result.append("--\(boundary)--\r\n")
        return result
    }
}

// MARK: - Data + String Append

private extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}
