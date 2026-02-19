import SwiftUI

struct ChatView: View {
    @StateObject private var viewModel = ChatViewModel()
    @FocusState private var isInputFocused: Bool
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Messages list
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(viewModel.messages) { message in
                                MessageBubble(message: message)
                                    .id(message.id)
                            }
                            
                            // Typing indicator
                            if viewModel.isStreaming {
                                HStack {
                                    TypingIndicator()
                                    Spacer()
                                }
                                .padding(.horizontal)
                                .id("typing")
                            }
                        }
                        .padding()
                    }
                    .onChange(of: viewModel.messages.count) { _, _ in
                        withAnimation {
                            if let lastMessage = viewModel.messages.last {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                    .onChange(of: viewModel.isStreaming) { _, isStreaming in
                        if isStreaming {
                            withAnimation {
                                proxy.scrollTo("typing", anchor: .bottom)
                            }
                        }
                    }
                }
                
                // Input area
                Divider()
                
                HStack(spacing: 12) {
                    TextField("Ask about your budget...", text: $viewModel.inputText, axis: .vertical)
                        .textFieldStyle(.plain)
                        .padding(12)
                        .background(Color(.systemGray6))
                        .cornerRadius(20)
                        .lineLimit(1...4)
                        .focused($isInputFocused)
                    
                    Button {
                        Task {
                            await viewModel.sendMessage()
                        }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundStyle(viewModel.canSend ? .green : .gray)
                    }
                    .disabled(!viewModel.canSend)
                }
                .padding()
            }
            .navigationTitle("Budget Assistant")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            viewModel.clearHistory()
                        } label: {
                            Label("Clear History", systemImage: "trash")
                        }
                        
                        Button {
                            Task {
                                await viewModel.loadSuggestions()
                            }
                        } label: {
                            Label("Get Suggestions", systemImage: "lightbulb")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .task {
                await viewModel.loadConversationHistory()
            }
            .alert("Error", isPresented: .constant(viewModel.errorMessage != nil)) {
                Button("OK") {
                    viewModel.errorMessage = nil
                }
            } message: {
                if let error = viewModel.errorMessage {
                    Text(error)
                }
            }
        }
        .overlay {
            if viewModel.messages.isEmpty && !viewModel.isStreaming {
                emptyStateView
            }
        }
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Image(systemName: "message.fill")
                .font(.system(size: 60))
                .foregroundStyle(.green.gradient)
            
            Text("Budget Assistant")
                .font(.title2)
                .fontWeight(.bold)
            
            Text("Ask me anything about your budget, expenses, or financial goals!")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
            
            VStack(alignment: .leading, spacing: 12) {
                Text("Try asking:")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                
                ForEach(viewModel.suggestedQuestions, id: \.self) { question in
                    Button {
                        viewModel.inputText = question
                        Task {
                            await viewModel.sendMessage()
                        }
                    } label: {
                        HStack {
                            Text(question)
                                .font(.subheadline)
                            Spacer()
                            Image(systemName: "arrow.right")
                                .font(.caption)
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }
                    .foregroundStyle(.primary)
                }
            }
            .padding()
        }
        .padding()
    }
}

// MARK: - Message Bubble

struct MessageBubble: View {
    let message: ChatMessage
    
    var body: some View {
        HStack {
            if message.isUser {
                Spacer(minLength: 60)
            }
            
            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 4) {
                Text(message.content)
                    .font(.subheadline)
                    .padding(12)
                    .background(message.isUser ? Color.green : Color(.systemGray5))
                    .foregroundStyle(message.isUser ? .white : .primary)
                    .cornerRadius(16)
                
                Text(message.timestamp, style: .time)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            
            if !message.isUser {
                Spacer(minLength: 60)
            }
        }
        .padding(.horizontal)
    }
}

// MARK: - Typing Indicator

struct TypingIndicator: View {
    @State private var dotCount = 0
    
    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { index in
                Circle()
                    .fill(Color.gray)
                    .frame(width: 8, height: 8)
                    .opacity(dotCount == index ? 1.0 : 0.3)
            }
        }
        .padding(12)
        .background(Color(.systemGray5))
        .cornerRadius(16)
        .onAppear {
            startAnimation()
        }
    }
    
    private func startAnimation() {
        Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
            withAnimation {
                dotCount = (dotCount + 1) % 3
            }
        }
    }
}

// MARK: - View Model

@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var inputText = ""
    @Published var isStreaming = false
    @Published var errorMessage: String?
    @Published var conversationId: String?

    private let api = APIService()

    let suggestedQuestions = [
        "What's my spending this month?",
        "Show me my top expense categories",
        "How much can I save this month?",
        "Give me budgeting tips"
    ]

    var canSend: Bool {
        !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isStreaming
    }

    func sendMessage() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        let userMessage = ChatMessage(content: text, isUser: true)
        messages.append(userMessage)
        inputText = ""
        isStreaming = true

        await streamResponse(for: text)

        isStreaming = false
    }

    private func streamResponse(for query: String) async {
        do {
            try await api.ensureServerConnected()
        } catch {
            errorMessage = "Could not connect to server: \(error.localizedDescription)"
            return
        }

        do {
            try await api.streamChat(message: query, conversationId: conversationId) { [weak self] (event: SSEEvent) in
                guard let self else { return }
                switch event {
                case .conversationId(let id):
                    self.conversationId = id
                case .text(let chunk):
                    if let lastIndex = self.messages.indices.last, !self.messages[lastIndex].isUser {
                        self.messages[lastIndex].content += chunk
                    } else {
                        self.messages.append(ChatMessage(content: chunk, isUser: false))
                    }
                case .done:
                    self.isStreaming = false
                case .error(let msg):
                    self.errorMessage = msg
                    self.isStreaming = false
                case .toolStart, .toolEnd:
                    break
                }
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadConversationHistory() async {}

    func clearHistory() {
        messages.removeAll()
        conversationId = nil
    }

    func loadSuggestions() async {
        let suggestion = "Ask me about your spending, budget status, or to add an expense!"
        messages.append(ChatMessage(content: suggestion, isUser: false))
    }
}

// MARK: - Models

struct ChatMessage: Identifiable {
    let id = UUID()
    var content: String
    let isUser: Bool
    let timestamp = Date()
}


#Preview {
    ChatView()
}
