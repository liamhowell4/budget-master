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
        
        // Add user message
        let userMessage = ChatMessage(content: text, isUser: true)
        messages.append(userMessage)
        
        // Clear input
        inputText = ""
        
        // Start streaming
        isStreaming = true
        
        // Simulate streaming response with SSE
        await streamResponse(for: text)
        
        isStreaming = false
    }
    
    private func streamResponse(for query: String) async {
        // TODO: Replace with actual SSE streaming from your API
        // This simulates the streaming behavior
        
        let responses = [
            "Based on your recent expenses, ",
            "I can see that you've spent $2,450 this month. ",
            "Your top categories are Food ($850), ",
            "Transportation ($650), and Entertainment ($450). ",
            "You have $550 remaining in your budget. ",
            "Consider reducing dining out expenses to save more!"
        ]
        
        var accumulatedText = ""
        
        for chunk in responses {
            try? await Task.sleep(for: .milliseconds(300))
            accumulatedText += chunk
            
            // Update or add assistant message
            if let lastIndex = messages.indices.last, !messages[lastIndex].isUser {
                messages[lastIndex].content = accumulatedText
            } else {
                let assistantMessage = ChatMessage(content: accumulatedText, isUser: false)
                messages.append(assistantMessage)
            }
        }
    }
    
    func loadConversationHistory() async {
        // TODO: Load conversation history from API or local storage
        // For now, start with empty messages
    }
    
    func clearHistory() {
        messages.removeAll()
    }
    
    func loadSuggestions() async {
        // TODO: Load personalized suggestions from API
        let suggestion = "Based on your spending patterns, I recommend setting aside $100 more per month for savings."
        let message = ChatMessage(content: suggestion, isUser: false)
        messages.append(message)
    }
}

// MARK: - Models

struct ChatMessage: Identifiable {
    let id = UUID()
    var content: String
    let isUser: Bool
    let timestamp = Date()
}

// MARK: - SSE Client (for real implementation)

actor SSEClient {
    private var task: Task<Void, Never>?
    
    func connect(url: URL, onMessage: @escaping (String) -> Void) {
        task = Task {
            do {
                let (bytes, _) = try await URLSession.shared.bytes(from: url)
                
                for try await line in bytes.lines {
                    if line.hasPrefix("data: ") {
                        let data = String(line.dropFirst(6))
                        await MainActor.run {
                            onMessage(data)
                        }
                    }
                }
            } catch {
                print("SSE connection error: \(error)")
            }
        }
    }
    
    func disconnect() {
        task?.cancel()
        task = nil
    }
}

#Preview {
    ChatView()
}
