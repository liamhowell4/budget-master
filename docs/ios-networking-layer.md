# iOS Networking Layer

Architecture and usage guide for the BudgetMaster iOS app's networking + models layer.

## Overview

The `ios/BudgetMaster/` directory contains a pure Swift networking layer that connects to the existing FastAPI backend at `https://budget-master-backend-857587891388.us-central1.run.app`. It covers all 25+ endpoints, handles Firebase Bearer token auth, SSE streaming for chat, and multipart uploads for expense processing.

No views or view models -- just the data/networking foundation for building the SwiftUI frontend on top of.

## File Structure

```
ios/BudgetMaster/
├── Models/              # Codable structs mirroring backend responses
│   ├── Common.swift     # AnyCodable, SuccessResponse, HealthResponse
│   ├── Expense.swift    # Expense, ExpenseDate, request/response types
│   ├── Budget.swift     # BudgetCategory, BudgetStatus, bulk update types
│   ├── Category.swift   # Category CRUD types, defaults, onboarding
│   ├── Chat.swift       # ChatStreamEvent enum, ChatRequest, ToolCallStored
│   ├── Conversation.swift # Conversation, ConversationListItem
│   ├── Recurring.swift  # RecurringExpense, PendingExpense, Frequency
│   └── Server.swift     # MCPServer, ServerStatus, ServerTool
│
├── Networking/          # Core HTTP/SSE infrastructure
│   ├── APIClient.swift  # Actor-based HTTP client (singleton)
│   ├── APIError.swift   # Error enum (9 cases)
│   ├── APIEndpoint.swift # Endpoint descriptor (method, path, query, auth)
│   ├── SSEClient.swift  # SSE stream parser → AsyncThrowingStream
│   ├── MultipartFormData.swift # Multipart body builder
│   └── TokenProvider.swift     # Firebase auth token protocol + stub
│
├── Services/            # Stateless endpoint wrappers (enum + static methods)
│   ├── ExpenseService.swift
│   ├── BudgetService.swift
│   ├── CategoryService.swift
│   ├── ChatService.swift
│   ├── ConversationService.swift
│   ├── RecurringService.swift
│   ├── PendingService.swift
│   └── ServerService.swift
│
└── Package.swift        # SPM manifest (for standalone compilation checks)
```

## Architecture

### APIClient (actor)

`APIClient.shared` is a thread-safe singleton wrapping `URLSession`. It handles:

- **Token injection** via a `TokenProvider` protocol (set after sign-in)
- **JSON coding** with `convertFromSnakeCase` / `convertToSnakeCase` (no manual `CodingKeys` needed on most models)
- **Error mapping** from HTTP status codes to typed `APIError` values

Key methods:

```swift
// GET/DELETE (no body)
func request<T: Decodable>(_ endpoint: APIEndpoint, as: T.Type) async throws -> T

// POST/PUT with JSON body
func request<Body: Encodable, T: Decodable>(_ endpoint: APIEndpoint, body: Body, as: T.Type) async throws -> T

// Multipart upload (images, audio)
func upload<T: Decodable>(_ endpoint: APIEndpoint, multipart: MultipartFormData, as: T.Type) async throws -> T

// SSE streaming (returns raw bytes for SSEClient to parse)
func streamRequest(_ endpoint: APIEndpoint, body: some Encodable) async throws -> (URLSession.AsyncBytes, URLResponse)
```

### Services (stateless enums)

Each service is an `enum` with static methods. No instances, no state. They compose an `APIEndpoint` and delegate to `APIClient.shared`.

```swift
// Usage from a ViewModel
let expenses = try await ExpenseService.getExpenses(year: 2025, month: 6)
let budget = try await BudgetService.getBudgetStatus()
try await ExpenseService.deleteExpense(id: "abc123")
```

### SSE Streaming (chat)

The `/chat/stream` endpoint returns Server-Sent Events. `SSEClient` parses the byte stream line-by-line and yields typed `ChatStreamEvent` values.

```swift
for try await event in ChatService.streamChat(message: "Coffee $5") {
    switch event {
    case .conversationId(let id):
        // Track conversation for context continuity
    case .toolStart(let id, let name, let args):
        // Show tool execution indicator
    case .toolEnd(let id, let name, let result):
        // Show tool result
    case .text(let content):
        // Append to response text
    case .done:
        break // Stream complete
    case .error(let message):
        // Handle error
    }
}
```

SSE format from the backend:
- `data: {"type": "conversation_id", "conversation_id": "..."}\n\n`
- `data: {"type": "tool_start", "id": "...", "name": "...", "args": {...}}\n\n`
- `data: {"type": "tool_end", "id": "...", "name": "...", "result": {...}}\n\n`
- `data: {"type": "text", "content": "..."}\n\n`
- `data: [DONE]\n\n`
- `data: [ERROR] message\n\n`

### Multipart Upload (expense processing)

`/mcp/process_expense` accepts text, images, and audio via multipart form-data:

```swift
let response = try await ChatService.processExpense(
    text: "Lunch at Chipotle",
    imageData: receiptJPEG,
    imageMimeType: "image/jpeg"
)
```

### TokenProvider

The `TokenProvider` protocol decouples `APIClient` from FirebaseAuth. After the user signs in, set the real provider:

```swift
// After FirebaseAuth sign-in
await APIClient.shared.setTokenProvider(FirebaseTokenProvider())
```

For testing, use `StubTokenProvider(token: "test-token")`.

## Endpoints Covered

| Service | Method | Path | Auth |
|---------|--------|------|------|
| **Expense** | GET | `/expenses` | Yes |
| | PUT | `/expenses/{id}` | Yes |
| | DELETE | `/expenses/{id}` | Yes |
| **Budget** | GET | `/budget` | Yes |
| | PUT | `/budget-caps/bulk-update` | Yes |
| | GET | `/budget/total` | Yes |
| | PUT | `/budget/total` | Yes |
| **Category** | GET | `/categories` | Yes |
| | POST | `/categories` | Yes |
| | PUT | `/categories/{id}` | Yes |
| | DELETE | `/categories/{id}` | Yes |
| | PUT | `/categories/reorder` | Yes |
| | GET | `/categories/defaults` | No |
| | POST | `/onboarding/complete` | Yes |
| **Chat** | POST | `/chat/stream` (SSE) | Yes |
| | POST | `/mcp/process_expense` | Yes |
| **Conversation** | GET | `/conversations` | Yes |
| | GET | `/conversations/{id}` | Yes |
| | POST | `/conversations` | Yes |
| | DELETE | `/conversations/{id}` | Yes |
| **Recurring** | GET | `/recurring` | Yes |
| | DELETE | `/recurring/{id}` | Yes |
| **Pending** | GET | `/pending` | Yes |
| | POST | `/pending/{id}/confirm` | Yes |
| | DELETE | `/pending/{id}` | Yes |
| **Server** | GET | `/servers` | No |
| | POST | `/connect/{id}` | No |
| | GET | `/status` | No |
| | POST | `/disconnect` | No |
| | GET | `/health` | No |

## Xcode Project Setup

### 1. Create the iOS app

In Xcode: `File > New > Project > iOS > App`. Use SwiftUI lifecycle, set bundle ID (e.g. `com.budgetmaster.app`), minimum deployment target iOS 16.0.

### 2. Add source files

Drag the `Models/`, `Networking/`, and `Services/` folders into the Xcode project. Make sure "Copy items if needed" is unchecked (they're already in the repo) and add to the app target.

Alternatively, reference the `Package.swift` as a local Swift package dependency.

### 3. Add Firebase SDK

In Xcode: `File > Add Package Dependencies` → enter `https://github.com/firebase/firebase-ios-sdk`. Select `FirebaseAuth` (minimum required for token auth).

### 4. Register iOS app in Firebase Console

Go to the [Firebase Console](https://console.firebase.google.com/) → project `budget-master-lh` → `Project Settings > General > Add app > iOS`. Enter your bundle ID. Download `GoogleService-Info.plist` and add it to the Xcode project root.

### 5. Initialize Firebase

In your `App` struct:

```swift
import SwiftUI
import FirebaseCore

@main
struct BudgetMasterApp: App {
    init() {
        FirebaseApp.configure()
    }
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
```

### 6. Implement FirebaseTokenProvider

In `TokenProvider.swift`, uncomment the `FirebaseTokenProvider` class or create it:

```swift
import FirebaseAuth

final class FirebaseTokenProvider: TokenProvider {
    func getToken() async throws -> String {
        guard let user = Auth.auth().currentUser else {
            throw APIError.noToken
        }
        return try await user.getIDToken()
    }
}
```

Then after sign-in:

```swift
await APIClient.shared.setTokenProvider(FirebaseTokenProvider())
```

## Key Design Notes

- **Snake case handled automatically.** `JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase` means `total_monthly_budget` maps to `totalMonthlyBudget` without explicit `CodingKeys`. The few exceptions (like `expense_id` → `id`) use manual `CodingKeys`.

- **All models are `Sendable`.** Safe to pass across actor/task boundaries. `AnyCodable` and `ChatStreamEvent` use `@unchecked Sendable` because they contain `Any` values from JSON parsing.

- **Services are stateless enums.** No retained state, no singletons (besides `APIClient`). Call them from any actor context.

- **Errors are typed.** `APIError` covers network failures, HTTP status codes, decoding errors, and SSE parsing. FastAPI's `detail` field is extracted automatically from error responses.
