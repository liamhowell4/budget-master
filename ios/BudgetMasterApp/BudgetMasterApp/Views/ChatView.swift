import SwiftUI

// MARK: - Data Models

struct ToolCall: Identifiable {
    let id: String
    let name: String
    var resultJSON: String

    init(id: String = UUID().uuidString, name: String, resultJSON: String = "{}") {
        self.id = id
        self.name = name
        self.resultJSON = resultJSON
    }
}

struct ChatMessage: Identifiable {
    let id: UUID = UUID()
    var content: String
    let isUser: Bool
    let timestamp: Date
    var toolCalls: [ToolCall]

    init(content: String, isUser: Bool, timestamp: Date = Date(), toolCalls: [ToolCall] = []) {
        self.content = content
        self.isUser = isUser
        self.timestamp = timestamp
        self.toolCalls = toolCalls
    }

    /// Detects the save_expense + get_budget_status pattern (mirrors React ChatMessage.tsx)
    var hasBudgetPattern: Bool {
        toolCalls.contains { $0.name == "save_expense" }
            && toolCalls.contains { $0.name == "get_budget_status" }
    }

    /// Extracts the budget warning string from get_budget_status result, if present
    var budgetWarning: String? {
        guard let tc = toolCalls.first(where: { $0.name == "get_budget_status" }),
              let data = tc.resultJSON.data(using: .utf8),
              let r = try? JSONDecoder().decode(BudgetStatusResult.self, from: data),
              let w = r.budget_warning, !w.isEmpty else { return nil }
        return w
    }

    /// Tool calls to display — hides get_budget_status when budget pattern is detected
    var visibleToolCalls: [ToolCall] {
        hasBudgetPattern ? toolCalls.filter { $0.name != "get_budget_status" } : toolCalls
    }

    /// Whether to show text content — hidden when budget pattern is detected
    var shouldShowContent: Bool {
        !content.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !hasBudgetPattern
    }
}

// MARK: - Tool Display Name Helper

func toolDisplayName(_ tool: String) -> String {
    switch tool {
    case "save_expense": return "Saving expense"
    case "get_budget_status": return "Checking budget"
    case "get_recent_expenses": return "Loading expenses"
    case "search_expenses": return "Searching expenses"
    case "query_expenses": return "Querying expenses"
    case "get_spending_summary": return "Summarizing spending"
    case "get_spending_by_category": return "Analyzing categories"
    case "get_budget_remaining": return "Checking budget"
    case "get_largest_expenses": return "Finding top expenses"
    case "compare_periods": return "Comparing periods"
    case "create_recurring_expense": return "Creating recurring"
    case "list_recurring_expenses": return "Loading recurring"
    case "delete_expense": return "Deleting expense"
    case "delete_recurring_expense": return "Deleting recurring"
    case "update_expense": return "Updating expense"
    default: return tool.replacingOccurrences(of: "_", with: " ").capitalized
    }
}

// MARK: - ChatView

struct ChatView: View {
    @StateObject private var viewModel = ChatViewModel()
    @FocusState private var isInputFocused: Bool
    @State private var showHistory = false
    @State private var chatSelectedExpense: APIExpense?
    @State private var chatSelectedCategory: CategoryBreakdown?
    @State private var chatSelectedRecurring: RecurringExpenseListItem?

    private let quickSuggestions = ["Coffee $5", "Lunch $15", "Groceries $80"]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if viewModel.messages.isEmpty && !viewModel.isStreaming {
                    emptyStateView.frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    messagesScrollView
                }
                inputArea
                    .padding(.horizontal)
                    .padding(.vertical, 10)
            }
            .navigationTitle("Budget Assistant")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button { showHistory = true } label: {
                        Image(systemName: "clock.arrow.circlepath")
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Button { viewModel.newConversation() } label: {
                            Label("New Chat", systemImage: "square.and.pencil")
                        }
                        Button { Task { await viewModel.loadSuggestions() } } label: {
                            Label("Get Suggestions", systemImage: "lightbulb")
                        }
                    } label: { Image(systemName: "ellipsis.circle") }
                }
            }
            .sheet(isPresented: $showHistory) {
                ConversationHistorySheet(viewModel: viewModel, isPresented: $showHistory)
            }
            .sheet(item: $chatSelectedExpense) { expense in
                EditExpenseView(
                    expense: Expense(
                        backendId: expense.id,
                        description: expense.expense_name,
                        amount: expense.amount,
                        category: expense.category,
                        date: {
                            let cal = Calendar.current
                            let comps = DateComponents(year: expense.date.year, month: expense.date.month, day: expense.date.day)
                            return cal.date(from: comps) ?? Date()
                        }()
                    ),
                    availableCategories: viewModel.availableCategories
                ) { updated in
                    guard let backendId = updated.backendId else { return }
                    let cal = Calendar.current
                    let dateDict: [String: Int] = [
                        "day": cal.component(.day, from: updated.date),
                        "month": cal.component(.month, from: updated.date),
                        "year": cal.component(.year, from: updated.date)
                    ]
                    try? await viewModel.api.updateExpense(
                        id: backendId,
                        name: updated.description,
                        amount: updated.amount,
                        category: updated.category,
                        date: dateDict
                    )
                }
            }
            .sheet(item: $chatSelectedCategory) { category in
                CategoryDetailSheet(category: category)
            }
            .sheet(item: $chatSelectedRecurring) { recurring in
                RecurringDetailSheet(item: recurring)
            }
            .alert("Error", isPresented: .constant(viewModel.errorMessage != nil)) {
                Button("OK") { viewModel.errorMessage = nil }
            } message: {
                if let e = viewModel.errorMessage { Text(e) }
            }
            .task { await viewModel.loadInitialData() }
        }
    }

    // MARK: Empty State

    private var emptyStateView: some View {
        VStack(spacing: 24) {
            Image(systemName: "dollarsign.circle.fill")
                .font(.system(size: 64))
                .foregroundStyle(AppTheme.accent)
            VStack(spacing: 8) {
                Text("Track your expenses").font(.title2).fontWeight(.bold)
                Text("Start a conversation to log and manage your spending")
                    .font(.subheadline).foregroundStyle(.secondary)
                    .multilineTextAlignment(.center).padding(.horizontal, 32)
            }
            HStack(spacing: 8) {
                ForEach(quickSuggestions, id: \.self) { s in
                    Button {
                        viewModel.inputText = s
                        Task { await viewModel.sendMessage() }
                    } label: {
                        Text(s).font(.subheadline).fontWeight(.medium)
                            .padding(.horizontal, 14).padding(.vertical, 10)
                            .background(Color(uiColor: .secondarySystemBackground))
                            .clipShape(Capsule())
                    }.foregroundStyle(.primary)
                }
            }
        }.padding()
    }

    // MARK: Messages Scroll View

    private var messagesScrollView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    if !viewModel.pendingExpenses.isEmpty {
                        PendingBannerCard(viewModel: viewModel)
                    }

                    ForEach(viewModel.messages) { message in
                        ChatMessageView(message: message, viewModel: viewModel,
                            onSelectExpense: { chatSelectedExpense = $0 },
                            onSelectCategory: { chatSelectedCategory = $0 },
                            onSelectRecurring: { chatSelectedRecurring = $0 })
                            .id(message.id)
                    }
                    if viewModel.isStreaming {
                        if !viewModel.pendingToolNames.isEmpty {
                            StreamingToolCallView(toolNames: viewModel.pendingToolNames)
                                .id("typing")
                        } else {
                            HStack { TypingIndicator(); Spacer() }
                                .padding(.horizontal).id("typing")
                        }
                    }
                }
                .padding()
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: viewModel.messages.count) { _, _ in
                withAnimation {
                    if let last = viewModel.messages.last { proxy.scrollTo(last.id, anchor: .bottom) }
                }
            }
            .onChange(of: viewModel.isStreaming) { _, streaming in
                if streaming { withAnimation { proxy.scrollTo("typing", anchor: .bottom) } }
            }
        }
    }

    // MARK: Input Area

    private var inputArea: some View {
        HStack(spacing: 12) {
            TextField("Track an expense...", text: $viewModel.inputText, axis: .vertical)
                .textFieldStyle(.plain).lineLimit(1...4).focused($isInputFocused)
            Button { Task { await viewModel.sendMessage() } } label: {
                Circle()
                    .fill(viewModel.canSend ? Color(uiColor: .label) : Color(uiColor: .systemGray4))
                    .frame(width: 32, height: 32)
                    .overlay {
                        Image(systemName: "arrow.up").font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(viewModel.canSend
                                ? Color(uiColor: .systemBackground) : Color(uiColor: .systemGray2))
                    }
            }.disabled(!viewModel.canSend)
        }
        .padding(.horizontal, 16).padding(.vertical, 10).glassInput()
    }
}

// MARK: - Conversation History Sheet

struct ConversationHistorySheet: View {
    @ObservedObject var viewModel: ChatViewModel
    @Binding var isPresented: Bool

    var body: some View {
        NavigationStack {
            List {
                Button {
                    viewModel.newConversation()
                    isPresented = false
                } label: {
                    Label("New Conversation", systemImage: "square.and.pencil")
                        .foregroundStyle(AppTheme.accent)
                }

                if viewModel.isLoadingHistory {
                    HStack { Spacer(); ProgressView(); Spacer() }
                } else if viewModel.conversations.isEmpty {
                    Text("No conversations yet").foregroundStyle(.secondary)
                } else {
                    Section("Recent") {
                        ForEach(viewModel.conversations, id: \.conversation_id) { conv in
                            Button {
                                Task {
                                    await viewModel.loadConversation(id: conv.conversation_id)
                                    isPresented = false
                                }
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(conv.summary ?? "Conversation")
                                        .font(.subheadline).lineLimit(2).foregroundStyle(.primary)
                                    if let ts = conv.last_activity,
                                       let date = parseConvDate(ts) {
                                        Text(date, style: .relative)
                                            .font(.caption).foregroundStyle(.secondary)
                                    }
                                }
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    Task { await viewModel.deleteConversation(id: conv.conversation_id) }
                                } label: { Label("Delete", systemImage: "trash") }
                            }
                        }
                    }
                }
            }
            .navigationTitle("History")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) { Button("Done") { isPresented = false } }
            }
            .task { await viewModel.fetchConversations() }
        }
    }

    private func parseConvDate(_ s: String) -> Date? {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = f.date(from: s) { return d }
        f.formatOptions = [.withInternetDateTime]
        return f.date(from: s)
    }
}

// MARK: - Chat Message View

struct ChatMessageView: View {
    let message: ChatMessage
    @ObservedObject var viewModel: ChatViewModel
    var onSelectExpense: ((APIExpense) -> Void)? = nil
    var onSelectCategory: ((CategoryBreakdown) -> Void)? = nil
    var onSelectRecurring: ((RecurringExpenseListItem) -> Void)? = nil

    var body: some View {
        if message.isUser {
            MessageBubble(message: message)
        } else {
            VStack(alignment: .leading, spacing: 8) {
                // 1. Tool cards (filtered via visibleToolCalls)
                ForEach(message.visibleToolCalls) { tc in
                    HStack {
                        ToolCallCardView(
                            toolCall: tc,
                            budgetWarning: tc.name == "save_expense" ? message.budgetWarning : nil,
                            viewModel: viewModel,
                            onSelectExpense: onSelectExpense,
                            onSelectCategory: onSelectCategory,
                            onSelectRecurring: onSelectRecurring
                        ).frame(maxWidth: 340, alignment: .leading)
                        Spacer(minLength: 0)
                    }.padding(.horizontal)
                }
                // 2. Text content (hidden when budget pattern detected)
                if message.shouldShowContent {
                    MessageBubble(message: message)
                }
            }
        }
    }
}

// MARK: - Message Bubble

struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack {
            if message.isUser { Spacer(minLength: 60) }
            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 4) {
                Text(message.content)
                    .font(.subheadline).padding(12)
                    .background(message.isUser ? Color(uiColor: .label) : Color(uiColor: .secondarySystemBackground))
                    .foregroundStyle(message.isUser ? Color(uiColor: .systemBackground) : Color(uiColor: .label))
                    .overlay {
                        if !message.isUser {
                            RoundedRectangle(cornerRadius: 16)
                                .stroke(Color(uiColor: .quaternaryLabel), lineWidth: 0.5)
                        }
                    }
                    .cornerRadius(16)
                Text(message.timestamp, style: .time)
                    .font(.caption2).foregroundStyle(.secondary)
            }
            if !message.isUser { Spacer(minLength: 60) }
        }
        .padding(.horizontal)
    }
}

// MARK: - Typing Indicator

struct TypingIndicator: View {
    @State private var dotCount = 0

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { i in
                Circle().fill(Color.gray).frame(width: 8, height: 8).opacity(dotCount == i ? 1 : 0.3)
            }
        }
        .padding(12)
        .background(Color(uiColor: .secondarySystemBackground))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(uiColor: .quaternaryLabel), lineWidth: 0.5))
        .cornerRadius(16)
        .onAppear {
            Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
                withAnimation { dotCount = (dotCount + 1) % 3 }
            }
        }
    }
}

// MARK: - Streaming Tool Call View

struct StreamingToolCallView: View {
    let toolNames: [String]

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(Array(toolNames.enumerated()), id: \.offset) { _, name in
                    HStack(spacing: 8) {
                        ProgressView()
                            .scaleEffect(0.7)
                        Text(toolDisplayName(name) + "\u{2026}")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(AppTheme.accent.opacity(0.08))
                    .clipShape(Capsule())
                }
            }
            Spacer()
        }
        .padding(.horizontal)
    }
}

// MARK: - Tool Call Card Dispatcher

struct ToolCallCardView: View {
    let toolCall: ToolCall
    var budgetWarning: String? = nil
    @ObservedObject var viewModel: ChatViewModel
    var onSelectExpense: ((APIExpense) -> Void)? = nil
    var onSelectCategory: ((CategoryBreakdown) -> Void)? = nil
    var onSelectRecurring: ((RecurringExpenseListItem) -> Void)? = nil

    var body: some View {
        let data = toolCall.resultJSON.data(using: .utf8) ?? Data()
        VStack(alignment: .leading, spacing: 4) {
            switch toolCall.name {
            case "save_expense":
                if let r = try? JSONDecoder().decode(SaveExpenseResult.self, from: data) {
                    toolCompletionLabel
                    ExpenseCardView(result: r, budgetWarning: budgetWarning,
                                  viewModel: viewModel, onSelectExpense: onSelectExpense)
                } else { GenericToolCard(tool: toolCall.name) }

            case "get_recent_expenses", "search_expenses", "query_expenses":
                if let r = try? JSONDecoder().decode(ExpenseListResult.self, from: data) {
                    toolCompletionLabel
                    ExpenseListCard(result: r, tool: toolCall.name, onSelectExpense: onSelectExpense)
                } else { GenericToolCard(tool: toolCall.name) }

            case "get_budget_remaining":
                if let r = try? JSONDecoder().decode(BudgetRemainingResult.self, from: data) {
                    toolCompletionLabel
                    BudgetRemainingCard(result: r, onSelectCategory: onSelectCategory)
                } else { GenericToolCard(tool: toolCall.name) }

            case "get_spending_by_category":
                if let r = try? JSONDecoder().decode(SpendingByCategoryResult.self, from: data) {
                    toolCompletionLabel
                    SpendingByCategoryCard(result: r, onSelectCategory: onSelectCategory)
                } else { GenericToolCard(tool: toolCall.name) }

            case "get_spending_summary":
                if let r = try? JSONDecoder().decode(SpendingSummaryResult.self, from: data) {
                    toolCompletionLabel
                    SpendingSummaryCard(result: r)
                } else { GenericToolCard(tool: toolCall.name) }

            case "get_largest_expenses":
                if let r = try? JSONDecoder().decode(LargestExpensesResult.self, from: data) {
                    toolCompletionLabel
                    TopExpensesCard(result: r)
                } else { GenericToolCard(tool: toolCall.name) }

            case "compare_periods":
                if let r = try? JSONDecoder().decode(PeriodComparisonResult.self, from: data) {
                    toolCompletionLabel
                    PeriodComparisonCard(result: r)
                } else { GenericToolCard(tool: toolCall.name) }

            case "create_recurring_expense":
                if let r = try? JSONDecoder().decode(RecurringExpenseResult.self, from: data) {
                    toolCompletionLabel
                    RecurringExpenseCard(result: r)
                } else { GenericToolCard(tool: toolCall.name) }

            case "list_recurring_expenses":
                if let r = try? JSONDecoder().decode(RecurringExpenseListResult.self, from: data) {
                    toolCompletionLabel
                    RecurringExpenseListCard(result: r, onSelectRecurring: onSelectRecurring)
                } else { GenericToolCard(tool: toolCall.name) }

            default:
                GenericToolCard(tool: toolCall.name)
            }
        }
    }

    private var toolCompletionLabel: some View {
        HStack(spacing: 4) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(AppTheme.accent)
                .font(.caption2)
            Text(toolDisplayName(toolCall.name))
                .font(.caption2).foregroundStyle(.secondary)
        }
    }
}

// MARK: - Card: save_expense

struct ExpenseCardView: View {
    let result: SaveExpenseResult
    var budgetWarning: String? = nil
    @ObservedObject var viewModel: ChatViewModel
    var onSelectExpense: ((APIExpense) -> Void)? = nil
    @State private var showDeleteConfirm = false
    @State private var isDeleted = false
    @State private var isDeleting = false

    var body: some View {
        let color = AppTheme.categoryColor(result.category ?? "")
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: AppTheme.sfSymbol(for: result.category ?? ""))
                    .foregroundStyle(color)
                Text(result.category?.replacingOccurrences(of: "_", with: " ").capitalized ?? "Expense")
                    .font(.caption).fontWeight(.semibold).foregroundStyle(color)
                Spacer()
                Text("Today").font(.caption).foregroundStyle(.secondary)
            }

            HStack(alignment: .firstTextBaseline) {
                Text(result.expense_name).font(.subheadline).fontWeight(.semibold)
                Spacer()
                Text(result.amount, format: .currency(code: "USD"))
                    .font(.subheadline).fontWeight(.bold)
            }

            if isDeleted {
                Label("Deleted", systemImage: "trash").font(.caption).foregroundStyle(.secondary)
            } else {
                HStack(spacing: 8) {
                    Spacer()
                    if isDeleting {
                        ProgressView().scaleEffect(0.8)
                    } else {
                        if let expenseId = result.expense_id {
                            Button {
                                let apiDate = APIDate(day: Calendar.current.component(.day, from: Date()),
                                                     month: Calendar.current.component(.month, from: Date()),
                                                     year: Calendar.current.component(.year, from: Date()))
                                let expense = APIExpense(id: expenseId, expense_name: result.expense_name,
                                                       amount: result.amount, date: apiDate,
                                                       category: result.category ?? "OTHER")
                                onSelectExpense?(expense)
                            } label: {
                                Label("Edit", systemImage: "pencil").font(.caption)
                            }
                            .buttonStyle(.bordered).controlSize(.mini)
                        }

                        Button(role: .destructive) { showDeleteConfirm = true } label: {
                            Label("Delete", systemImage: "trash").font(.caption)
                        }
                        .buttonStyle(.bordered).controlSize(.mini)
                    }
                }
            }

            // Budget warnings
            if let warning = budgetWarning {
                budgetWarningView(warning)
            }
        }
        .padding(14)
        .background(color.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(color.opacity(0.2), lineWidth: 1))
        .confirmationDialog("Delete this expense?", isPresented: $showDeleteConfirm, titleVisibility: .visible) {
            Button("Delete", role: .destructive) {
                guard let expenseId = result.expense_id else { return }
                isDeleting = true
                Task {
                    await viewModel.deleteExpense(id: expenseId)
                    isDeleted = true
                    isDeleting = false
                }
            }
        }
    }

    @ViewBuilder
    private func budgetWarningView(_ warning: String) -> some View {
        let lines = warning.components(separatedBy: "\n").filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }
        ForEach(Array(lines.enumerated()), id: \.offset) { _, line in
            let level = classifyWarningLine(line)
            let cleanLine = line.replacingOccurrences(of: "^[\\p{So}\\p{Sk}\\s]+", with: "", options: .regularExpression)
            HStack(spacing: 6) {
                Image(systemName: level.icon)
                    .font(.caption2)
                Text(cleanLine)
                    .font(.caption2)
                    .lineLimit(2)
            }
            .foregroundStyle(level.foreground)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(level.background)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private enum WarningLevel {
        case over, danger, warning, info

        var icon: String {
            switch self {
            case .over, .danger: return "exclamationmark.triangle.fill"
            case .warning: return "exclamationmark.triangle"
            case .info: return "info.circle"
            }
        }

        var foreground: Color {
            switch self {
            case .over, .danger: return .red
            case .warning: return .orange
            case .info: return .blue
            }
        }

        var background: Color {
            switch self {
            case .over, .danger: return .red.opacity(0.1)
            case .warning: return .orange.opacity(0.1)
            case .info: return .blue.opacity(0.1)
            }
        }
    }

    private func classifyWarningLine(_ line: String) -> WarningLevel {
        let upper = line.uppercased()
        if upper.contains("OVER BUDGET") { return .over }
        if upper.contains("95%") || upper.contains("100%") { return .danger }
        if upper.contains("\u{26A0}\u{FE0F}") || upper.contains("90%") { return .warning }
        return .info
    }
}

// MARK: - Card: expense lists

struct ExpenseListCard: View {
    let result: ExpenseListResult
    let tool: String
    var onSelectExpense: ((APIExpense) -> Void)? = nil
    @State private var showAll = false

    var title: String {
        if tool == "search_expenses", let q = result.query { return "Results for \"\(q)\"" }
        if tool == "get_recent_expenses" { return "Recent Expenses" }
        return "Expenses"
    }

    var body: some View {
        let expenses = result.expenses ?? []
        let visible = showAll ? expenses : Array(expenses.prefix(5))

        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(title).font(.subheadline).fontWeight(.semibold)
                Spacer()
                Text("\(expenses.count)").font(.caption).foregroundStyle(.secondary)
            }

            ForEach(Array(visible.enumerated()), id: \.offset) { _, e in
                let rowContent = HStack(spacing: 8) {
                    Circle().fill(AppTheme.categoryColor(e.category ?? "")).frame(width: 8, height: 8)
                    Text(e.name).font(.caption).lineLimit(1)
                    Spacer()
                    if let d = e.date {
                        Text(formatAPIDate(d)).font(.caption2).foregroundStyle(.secondary)
                    }
                    Text(e.amount, format: .currency(code: "USD")).font(.caption).fontWeight(.semibold)
                }

                if let id = e.id, let onSelectExpense {
                    Button {
                        let apiExpense = APIExpense(id: id, expense_name: e.name, amount: e.amount,
                                                   date: e.date ?? APIDate(day: 1, month: 1, year: 2025),
                                                   category: e.category ?? "OTHER")
                        onSelectExpense(apiExpense)
                    } label: {
                        rowContent
                    }
                    .buttonStyle(.plain)
                } else {
                    rowContent
                }
            }

            if expenses.count > 5 {
                Button(showAll ? "Show less" : "Show \(expenses.count - 5) more") { showAll.toggle() }
                    .font(.caption).foregroundStyle(AppTheme.accent)
            }

            if let total = result.total {
                Divider()
                HStack {
                    Text("Total").font(.caption).fontWeight(.semibold)
                    Spacer()
                    Text(total, format: .currency(code: "USD")).font(.caption).fontWeight(.bold)
                }
            }
        }
        .padding(14).cardStyle()
    }
}

// MARK: - Card: get_budget_remaining

struct BudgetRemainingCard: View {
    let result: BudgetRemainingResult
    var onSelectCategory: ((CategoryBreakdown) -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Budget Remaining").font(.subheadline).fontWeight(.semibold)

            if let cats = result.categories, !cats.isEmpty {
                ForEach(cats, id: \.category) { cat in
                    BudgetCatRow(category: cat.category, spending: cat.spending,
                                 cap: cat.cap, percentage: cat.percentage, remaining: cat.remaining,
                                 onTap: onSelectCategory != nil ? {
                                     onSelectCategory?(CategoryBreakdown(
                                         categoryId: cat.category,
                                         name: cat.category.replacingOccurrences(of: "_", with: " ").capitalized,
                                         amount: cat.spending, cap: cat.cap, percentage: cat.percentage,
                                         color: AppTheme.categoryColor(cat.category),
                                         icon: cat.category))
                                 } : nil)
                }
                if let total = result.total {
                    Divider()
                    BudgetCatRow(category: "TOTAL", spending: total.spending,
                                 cap: total.cap, percentage: total.percentage, remaining: total.remaining)
                }
            } else if let spending = result.spending, let cap = result.cap,
                      let pct = result.percentage, let rem = result.remaining {
                let cat = result.category ?? ""
                BudgetCatRow(category: cat, spending: spending, cap: cap, percentage: pct, remaining: rem,
                             onTap: onSelectCategory != nil && !cat.isEmpty ? {
                                 onSelectCategory?(CategoryBreakdown(
                                     categoryId: cat,
                                     name: cat.replacingOccurrences(of: "_", with: " ").capitalized,
                                     amount: spending, cap: cap, percentage: pct,
                                     color: AppTheme.categoryColor(cat), icon: cat))
                             } : nil)
            }
        }
        .padding(14).cardStyle()
    }
}

struct BudgetCatRow: View {
    let category: String
    let spending: Double
    let cap: Double
    let percentage: Double
    let remaining: Double
    var onTap: (() -> Void)? = nil

    var body: some View {
        let content = VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(category == "TOTAL" ? "Total" : category.replacingOccurrences(of: "_", with: " ").capitalized)
                    .font(.caption).fontWeight(.semibold)
                    .foregroundStyle(category == "TOTAL" ? .primary : AppTheme.categoryColor(category))
                Spacer()
                Text(remaining, format: .currency(code: "USD"))
                    .font(.caption).fontWeight(.semibold)
                    .foregroundStyle(AppTheme.budgetProgressColor(percentage))
                Text("left").font(.caption2).foregroundStyle(.secondary)
            }
            ProgressView(value: min(percentage / 100, 1.0))
                .tint(AppTheme.budgetProgressColor(percentage))
                .progressViewStyle(.linear)
                .scaleEffect(x: 1, y: 0.7, anchor: .center)
            HStack {
                Text(spending, format: .currency(code: "USD")).font(.caption2).foregroundStyle(.secondary)
                Text("of").font(.caption2).foregroundStyle(.secondary)
                Text(cap, format: .currency(code: "USD")).font(.caption2).foregroundStyle(.secondary)
                Text("(\(Int(percentage))%)").font(.caption2).foregroundStyle(.secondary)
            }
        }

        if let onTap {
            Button(action: onTap) { content }.buttonStyle(.plain)
        } else {
            content
        }
    }
}

// MARK: - Card: get_spending_by_category

struct SpendingByCategoryCard: View {
    let result: SpendingByCategoryResult
    var onSelectCategory: ((CategoryBreakdown) -> Void)? = nil

    var body: some View {
        let maxTotal = result.breakdown.map(\.total).max() ?? 1
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Spending by Category").font(.subheadline).fontWeight(.semibold)
                Spacer()
                Text(formatDateRange(result.start_date, result.end_date))
                    .font(.caption2).foregroundStyle(.secondary)
            }

            ForEach(result.breakdown, id: \.category) { cat in
                let rowContent = HStack(spacing: 8) {
                    Text(cat.category.replacingOccurrences(of: "_", with: " ").capitalized)
                        .font(.caption).foregroundStyle(AppTheme.categoryColor(cat.category))
                        .frame(width: 80, alignment: .leading)
                    GeometryReader { geo in
                        RoundedRectangle(cornerRadius: 3)
                            .fill(AppTheme.categoryColor(cat.category).opacity(0.3))
                            .frame(width: geo.size.width * CGFloat(cat.total / maxTotal))
                    }
                    .frame(height: 12)
                    Spacer()
                    Text(cat.total, format: .currency(code: "USD")).font(.caption).fontWeight(.semibold)
                }

                if let onSelectCategory {
                    Button {
                        onSelectCategory(CategoryBreakdown(
                            categoryId: cat.category,
                            name: cat.category.replacingOccurrences(of: "_", with: " ").capitalized,
                            amount: cat.total, cap: 0, percentage: 0,
                            color: AppTheme.categoryColor(cat.category),
                            icon: cat.category))
                    } label: {
                        rowContent
                    }
                    .buttonStyle(.plain)
                } else {
                    rowContent
                }
            }

            Divider()
            HStack {
                Text("Total").font(.caption).fontWeight(.semibold)
                Spacer()
                Text(result.total, format: .currency(code: "USD")).font(.caption).fontWeight(.bold)
            }
        }
        .padding(14).cardStyle()
    }
}

// MARK: - Card: get_spending_summary

struct SpendingSummaryCard: View {
    let result: SpendingSummaryResult

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Spending Summary").font(.subheadline).fontWeight(.semibold)
                Spacer()
                Text(formatDateRange(result.start_date, result.end_date))
                    .font(.caption2).foregroundStyle(.secondary)
            }
            HStack(spacing: 0) {
                summaryCell("Total", text: result.total.formatted(.currency(code: "USD")))
                Divider().frame(height: 28)
                summaryCell("Transactions", text: "\(result.count)")
                Divider().frame(height: 28)
                summaryCell("Average", text: result.average_per_transaction.formatted(.currency(code: "USD")))
            }
        }
        .padding(14).cardStyle()
    }

    private func summaryCell(_ title: String, text: String) -> some View {
        VStack(spacing: 2) {
            Text(title).font(.caption2).foregroundStyle(.secondary)
            Text(text).font(.caption).fontWeight(.semibold)
        }.frame(maxWidth: .infinity)
    }
}

// MARK: - Card: get_largest_expenses

struct TopExpensesCard: View {
    let result: LargestExpensesResult

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Top Expenses").font(.subheadline).fontWeight(.semibold)
                Spacer()
                Text(formatDateRange(result.start_date, result.end_date))
                    .font(.caption2).foregroundStyle(.secondary)
            }
            ForEach(Array(result.largest_expenses.enumerated()), id: \.offset) { idx, e in
                HStack(spacing: 8) {
                    Text("\(idx + 1)")
                        .font(.caption2).fontWeight(.bold)
                        .frame(width: 18, height: 18)
                        .background(idx == 0 ? Color.orange.opacity(0.2) : Color(uiColor: .systemGray5))
                        .clipShape(Circle())
                    Circle().fill(AppTheme.categoryColor(e.category ?? "")).frame(width: 6, height: 6)
                    Text(e.name).font(.caption).lineLimit(1)
                    Spacer()
                    Text(e.amount, format: .currency(code: "USD")).font(.caption).fontWeight(.semibold)
                }
                .padding(6)
                .background(idx == 0 ? Color.orange.opacity(0.05) : Color.clear)
                .cornerRadius(8)
            }
        }
        .padding(14).cardStyle()
    }
}

// MARK: - Card: compare_periods

struct PeriodComparisonCard: View {
    let result: PeriodComparisonResult

    var body: some View {
        let diff = result.comparison.difference
        let pct = result.comparison.percentage_change

        VStack(alignment: .leading, spacing: 10) {
            Text("Period Comparison").font(.subheadline).fontWeight(.semibold)

            HStack(spacing: 0) {
                periodCell("Period 1", total: result.period1.total, count: result.period1.count)
                Divider().frame(height: 40)
                periodCell("Period 2", total: result.period2.total, count: result.period2.count)
            }

            Divider()
            HStack {
                Image(systemName: diff > 0 ? "arrow.up.right" : diff < 0 ? "arrow.down.right" : "minus")
                    .foregroundStyle(diff > 0 ? .red : diff < 0 ? AppTheme.accent : .secondary)
                    .font(.caption)
                Text(abs(diff), format: .currency(code: "USD"))
                    .font(.caption).fontWeight(.semibold)
                    .foregroundStyle(diff > 0 ? .red : diff < 0 ? AppTheme.accent : .secondary)
                if let pct {
                    Text("(\(String(format: "%.1f", abs(pct)))%)")
                        .font(.caption2).foregroundStyle(.secondary)
                }
                Spacer()
                Text(diff > 0 ? "more spent" : diff < 0 ? "less spent" : "no change")
                    .font(.caption2).foregroundStyle(.secondary)
            }
        }
        .padding(14).cardStyle()
    }

    private func periodCell(_ label: String, total: Double, count: Int) -> some View {
        VStack(spacing: 4) {
            Text(label).font(.caption2).foregroundStyle(.secondary)
            Text(total, format: .currency(code: "USD")).font(.caption).fontWeight(.semibold)
            Text("\(count) transactions").font(.caption2).foregroundStyle(.secondary)
        }.frame(maxWidth: .infinity)
    }
}

// MARK: - Card: create_recurring_expense

struct RecurringExpenseCard: View {
    let result: RecurringExpenseResult

    var body: some View {
        let color = AppTheme.categoryColor(result.category)
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: AppTheme.sfSymbol(for: result.category))
                    .foregroundStyle(color)
                Text(result.category.replacingOccurrences(of: "_", with: " ").capitalized)
                    .font(.caption).fontWeight(.semibold).foregroundStyle(color)
                Spacer()
                freqBadge(result.frequency)
            }
            HStack(alignment: .firstTextBaseline) {
                Text(result.expense_name).font(.subheadline).fontWeight(.semibold)
                Spacer()
                Text(result.amount, format: .currency(code: "USD")).font(.subheadline).fontWeight(.bold)
            }
        }
        .padding(14)
        .background(color.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(color.opacity(0.2), lineWidth: 1))
    }

    private func freqBadge(_ freq: String) -> some View {
        let color: Color = freq == "monthly" ? .purple : freq == "weekly" ? .blue : .indigo
        return Text(freq.capitalized)
            .font(.caption2).fontWeight(.medium)
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(color.opacity(0.15))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }
}

// MARK: - Card: list_recurring_expenses

struct RecurringExpenseListCard: View {
    let result: RecurringExpenseListResult
    var onSelectRecurring: ((RecurringExpenseListItem) -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Recurring Expenses").font(.subheadline).fontWeight(.semibold)
                Spacer()
                Text("\(result.count)").font(.caption).foregroundStyle(.secondary)
            }
            ForEach(result.recurring_expenses, id: \.expense_name) { e in
                let rowContent = HStack(spacing: 8) {
                    Circle().fill(AppTheme.categoryColor(e.category)).frame(width: 8, height: 8)
                    Text(e.expense_name).font(.caption).lineLimit(1)
                    Spacer()
                    Text(e.frequency.capitalized)
                        .font(.caption2)
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(Color(uiColor: .systemGray5))
                        .clipShape(Capsule())
                    Text(e.amount, format: .currency(code: "USD")).font(.caption).fontWeight(.semibold)
                }

                if let onSelectRecurring {
                    Button { onSelectRecurring(e) } label: { rowContent }
                        .buttonStyle(.plain)
                } else {
                    rowContent
                }
            }
        }
        .padding(14).cardStyle()
    }
}

// MARK: - Card: generic fallback

struct GenericToolCard: View {
    let tool: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(AppTheme.accent)
                .font(.caption)
            Text(toolDisplayName(tool))
                .font(.caption).foregroundStyle(.secondary)
        }
        .padding(10)
        .background(AppTheme.accent.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(AppTheme.accent.opacity(0.15), lineWidth: 0.5))
    }
}

// MARK: - Recurring Detail Sheet

struct RecurringDetailSheet: View {
    let item: RecurringExpenseListItem
    @Environment(\.dismiss) private var dismiss
    @State private var showDeleteConfirm = false
    @State private var isDeleting = false
    private let api = APIService()

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack {
                        Image(systemName: AppTheme.sfSymbol(for: item.category))
                            .font(.title2)
                            .foregroundStyle(AppTheme.categoryColor(item.category))
                            .frame(width: 44, height: 44)
                            .background(AppTheme.categoryColor(item.category).opacity(0.15))
                            .clipShape(RoundedRectangle(cornerRadius: 10))

                        VStack(alignment: .leading, spacing: 4) {
                            Text(item.category.replacingOccurrences(of: "_", with: " ").capitalized)
                                .font(.caption).foregroundStyle(.secondary)
                            Text(item.expense_name)
                                .font(.headline)
                        }
                        Spacer()
                        Text(item.frequency.capitalized)
                            .font(.caption2).fontWeight(.medium)
                            .padding(.horizontal, 8).padding(.vertical, 4)
                            .background(Color.purple.opacity(0.15))
                            .foregroundStyle(.purple)
                            .clipShape(Capsule())
                    }
                }

                Section {
                    HStack {
                        Text("Amount")
                        Spacer()
                        Text(item.amount, format: .currency(code: "USD"))
                            .fontWeight(.semibold)
                    }
                    if let schedule = item.schedule {
                        HStack {
                            Text("Schedule")
                            Spacer()
                            Text(schedule)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Section {
                    Button(role: .destructive) {
                        showDeleteConfirm = true
                    } label: {
                        HStack {
                            Spacer()
                            if isDeleting {
                                ProgressView()
                            } else {
                                Label("Delete Template", systemImage: "trash")
                            }
                            Spacer()
                        }
                    }
                    .disabled(isDeleting)
                }
            }
            .navigationTitle("Recurring Expense")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
            .confirmationDialog("Delete this recurring expense template?",
                              isPresented: $showDeleteConfirm, titleVisibility: .visible) {
                Button("Delete Template", role: .destructive) {
                    guard let templateId = item.template_id else { return }
                    isDeleting = true
                    Task {
                        try? await api.deleteRecurring(id: templateId)
                        dismiss()
                    }
                }
            }
        }
    }
}

// MARK: - Pending Banner & Sheet

struct PendingBannerCard: View {
    @ObservedObject var viewModel: ChatViewModel
    @State private var showSheet = false

    var body: some View {
        let count = viewModel.pendingExpenses.count
        HStack(spacing: 12) {
            Image(systemName: "clock.badge.exclamationmark")
                .font(.title3)
                .foregroundStyle(.orange)

            VStack(alignment: .leading, spacing: 2) {
                Text("\(count) recurring expense\(count == 1 ? "" : "s") need\(count == 1 ? "s" : "") confirmation")
                    .font(.subheadline).fontWeight(.medium)
                Text("Tap to review")
                    .font(.caption).foregroundStyle(.secondary)
            }

            Spacer()

            Button("Review") { showSheet = true }
                .font(.subheadline).fontWeight(.semibold)
                .foregroundStyle(.white)
                .padding(.horizontal, 14).padding(.vertical, 7)
                .background(Color.orange)
                .clipShape(Capsule())
        }
        .padding(14)
        .background(Color.orange.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.orange.opacity(0.2), lineWidth: 1))
        .padding(.horizontal)
        .sheet(isPresented: $showSheet) {
            PendingExpensesSheet(viewModel: viewModel)
        }
    }
}

struct PendingExpensesSheet: View {
    @ObservedObject var viewModel: ChatViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.pendingExpenses.isEmpty {
                    ContentUnavailableView(
                        "All Done!",
                        systemImage: "checkmark.circle.fill",
                        description: Text("No pending expenses to review.")
                    )
                } else {
                    List {
                        ForEach(viewModel.pendingExpenses) { pending in
                            PendingExpenseRow(
                                pending: pending,
                                onConfirm: { await viewModel.confirmPending(id: pending.pending_id) },
                                onSkip: { await viewModel.skipPending(id: pending.pending_id) }
                            )
                        }
                    }
                }
            }
            .navigationTitle("Pending Expenses")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

// MARK: - Card Style Extension

extension View {
    func cardStyle() -> some View {
        self
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(uiColor: .secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(uiColor: .separator), lineWidth: 0.5))
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
    @Published var conversations: [ConversationSummary] = []
    @Published var isLoadingHistory = false
    @Published var pendingToolNames: [String] = []
    @Published var pendingExpenses: [PendingExpense] = []
    @Published var availableCategories: [APICategory] = []

    let api = APIService()

    var canSend: Bool {
        !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isStreaming
    }

    // MARK: Messaging

    func sendMessage() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        messages.append(ChatMessage(content: text, isUser: true))
        inputText = ""
        isStreaming = true
        // Placeholder assistant message (mirrors React useChat.ts)
        messages.append(ChatMessage(content: "", isUser: false))
        await streamResponse(for: text)
        isStreaming = false
    }

    private func streamResponse(for query: String) async {
        do { try await api.ensureServerConnected() } catch {
            errorMessage = "Could not connect to server: \(error.localizedDescription)"
            return
        }
        do {
            try await api.streamChat(message: query, conversationId: conversationId) { [weak self] event in
                guard let self else { return }
                let lastIdx = self.messages.count - 1
                guard lastIdx >= 0 else { return }
                switch event {
                case .conversationId(let id):
                    self.conversationId = id
                case .text(let chunk):
                    self.messages[lastIdx].content += chunk
                case .toolStart(let id, let tool):
                    self.pendingToolNames.append(tool)
                    self.messages[lastIdx].toolCalls.append(ToolCall(id: id, name: tool))
                case .toolEnd(let id, let tool, let resultJSON):
                    self.pendingToolNames.removeAll { $0 == tool }
                    if let tcIdx = self.messages[lastIdx].toolCalls.firstIndex(where: { $0.id == id }) {
                        self.messages[lastIdx].toolCalls[tcIdx] = ToolCall(id: id, name: tool, resultJSON: resultJSON)
                    }
                case .done:
                    self.pendingToolNames.removeAll()
                    self.isStreaming = false
                    // Remove empty placeholder if no content or tools
                    if self.messages[lastIdx].content.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                        && self.messages[lastIdx].toolCalls.isEmpty {
                        self.messages.remove(at: lastIdx)
                    }
                case .error(let msg):
                    self.errorMessage = msg
                    self.isStreaming = false
                }
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    // MARK: Conversation History

    func loadConversationHistory() async {
        do {
            let summaries = try await api.fetchConversations(limit: 1)
            guard let latest = summaries.first else { return }
            await loadConversation(id: latest.conversation_id)
        } catch { }
    }

    func loadConversation(id: String) async {
        do {
            let detail = try await api.fetchConversation(id: id)
            guard !detail.messages.isEmpty else { return }
            let isoFull = ISO8601DateFormatter()
            isoFull.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let isoBasic = ISO8601DateFormatter()
            var loaded: [ChatMessage] = []
            for msg in detail.messages {
                let date = msg.timestamp.flatMap { isoFull.date(from: $0) ?? isoBasic.date(from: $0) } ?? Date()
                let toolCalls = msg.toolCalls.map { ToolCall(name: $0.name, resultJSON: $0.resultJSON) }
                loaded.append(ChatMessage(
                    content: msg.content, isUser: msg.role == "user",
                    timestamp: date, toolCalls: toolCalls
                ))
            }
            messages = loaded
            conversationId = id
        } catch { }
    }

    func fetchConversations() async {
        isLoadingHistory = true
        do { conversations = try await api.fetchConversations(limit: 20) } catch { }
        isLoadingHistory = false
    }

    func deleteConversation(id: String) async {
        do {
            try await api.deleteConversation(id: id)
            conversations.removeAll { $0.conversation_id == id }
            if conversationId == id { newConversation() }
        } catch { }
    }

    func newConversation() {
        messages = []
        conversationId = nil
    }

    func deleteExpense(id: String) async {
        do { try await api.deleteExpense(id: id) } catch { }
    }

    func loadSuggestions() async {
        messages.append(ChatMessage(content: "Ask me about your spending, budget, or to add an expense!", isUser: false))
    }

    // MARK: Pending Expenses

    func fetchPendingExpenses() async {
        do {
            pendingExpenses = try await api.fetchPending()
        } catch { }
    }

    func confirmPending(id: String) async {
        do {
            try await api.confirmPending(id: id)
            pendingExpenses.removeAll { $0.pending_id == id }
        } catch { }
    }

    func skipPending(id: String) async {
        do {
            try await api.skipPending(id: id)
            pendingExpenses.removeAll { $0.pending_id == id }
        } catch { }
    }

    // MARK: Initial Data

    func loadInitialData() async {
        await fetchPendingExpenses()
        do {
            availableCategories = try await api.fetchCategories()
        } catch { }
    }
}

// MARK: - Tool Result Models

struct SaveExpenseResult: Decodable {
    let expense_id: String?
    let expense_name: String
    let amount: Double
    let category: String?
}

struct BudgetStatusResult: Decodable {
    let budget_warning: String?
}

struct BudgetRemainingResult: Decodable {
    let category: String?
    let spending: Double?
    let cap: Double?
    let percentage: Double?
    let remaining: Double?
    let categories: [BudgetCatResult]?
    let total: BudgetTotalResult?
}

struct BudgetCatResult: Decodable {
    let category: String
    let spending: Double
    let cap: Double
    let percentage: Double
    let remaining: Double
}

struct BudgetTotalResult: Decodable {
    let spending: Double
    let cap: Double
    let percentage: Double
    let remaining: Double
}

struct SpendingByCategoryResult: Decodable {
    let breakdown: [CategoryBreakdownResult]
    let total: Double
    let start_date: APIDate?
    let end_date: APIDate?
}

struct CategoryBreakdownResult: Decodable {
    let category: String
    let total: Double
    let count: Int
}

struct SpendingSummaryResult: Decodable {
    let total: Double
    let count: Int
    let average_per_transaction: Double
    let start_date: APIDate?
    let end_date: APIDate?
}

struct ExpenseListResult: Decodable {
    let expenses: [ExpenseResultItem]?
    let count: Int?
    let total: Double?
    let query: String?
    let start_date: APIDate?
    let end_date: APIDate?
}

struct ExpenseResultItem: Decodable {
    let id: String?
    let name: String
    let amount: Double
    let category: String?
    let date: APIDate?
}

struct LargestExpensesResult: Decodable {
    let largest_expenses: [ExpenseResultItem]
    let start_date: APIDate?
    let end_date: APIDate?
    let category: String?
}

struct PeriodComparisonResult: Decodable {
    let period1: PeriodData
    let period2: PeriodData
    let comparison: ComparisonData
    let category: String?
}

struct PeriodData: Decodable {
    let start: APIDate?
    let end: APIDate?
    let total: Double
    let count: Int
}

struct ComparisonData: Decodable {
    let difference: Double
    let percentage_change: Double?
}

struct RecurringExpenseResult: Decodable {
    let template_id: String?
    let expense_name: String
    let amount: Double
    let category: String
    let frequency: String
}

struct RecurringExpenseListResult: Decodable {
    let count: Int
    let recurring_expenses: [RecurringExpenseListItem]
}

struct RecurringExpenseListItem: Decodable, Identifiable {
    var id: String { template_id ?? expense_name }
    let template_id: String?
    let expense_name: String
    let amount: Double
    let category: String
    let frequency: String
    let schedule: String?
}

// MARK: - Helpers

private func formatAPIDate(_ d: APIDate) -> String {
    let cal = Calendar.current
    let comps = DateComponents(year: d.year, month: d.month, day: d.day)
    guard let date = cal.date(from: comps) else { return "\(d.month)/\(d.day)" }
    if cal.isDateInToday(date) { return "Today" }
    if cal.isDateInYesterday(date) { return "Yesterday" }
    let f = DateFormatter()
    f.dateFormat = "MMM d"
    return f.string(from: date)
}

private func formatDateRange(_ start: APIDate?, _ end: APIDate?) -> String {
    guard let s = start, let e = end else { return "" }
    let f = DateFormatter()
    f.dateFormat = "MMM d"
    let cal = Calendar.current
    let sd = cal.date(from: DateComponents(year: s.year, month: s.month, day: s.day))
    let ed = cal.date(from: DateComponents(year: e.year, month: e.month, day: e.day))
    guard let sd, let ed else { return "" }
    return "\(f.string(from: sd)) \u{2013} \(f.string(from: ed))"
}
