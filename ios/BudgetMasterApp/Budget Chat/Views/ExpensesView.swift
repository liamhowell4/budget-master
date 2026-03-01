import SwiftUI

// MARK: - Sort Options

enum ExpenseSort: String, CaseIterable {
    case newest = "Newest"
    case oldest = "Oldest"
    case highestAmount = "Highest Amount"
    case lowestAmount = "Lowest Amount"
}

struct ExpensesView: View {
    @StateObject private var viewModel = ExpensesViewModel()
    @Environment(\.appAccent) private var appAccent
    @State private var showingAddExpense = false
    @State private var showingFilters = false
    @State private var selectedTab = 0
    @State private var sortOrder: ExpenseSort = .newest
    @State private var recurringToDelete: RecurringExpenseAPI?
    @State private var showSettings = false
    @State private var showErrorAlert = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Picker("View", selection: $selectedTab) {
                    Text("History").tag(0)
                    Text("Recurring").tag(1)
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.vertical, 8)

                ZStack {
                    if selectedTab == 0 {
                        if sortedFilteredExpenses.isEmpty && !viewModel.isLoading {
                            emptyStateView
                        } else {
                            expensesList
                        }
                    } else {
                        if activeRecurringExpenses.isEmpty && !viewModel.isLoadingRecurring {
                            recurringEmptyStateView
                        } else {
                            recurringList
                        }
                    }
                }
            }
            .navigationTitle("Expenses")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if selectedTab == 0 {
                        Button {
                            showingFilters = true
                        } label: {
                            ZStack(alignment: .topTrailing) {
                                Image(systemName: viewModel.hasActiveFilters
                                      ? "line.3.horizontal.decrease.circle.fill"
                                      : "line.3.horizontal.decrease.circle")
                                if viewModel.hasActiveFilters {
                                    Circle()
                                        .fill(appAccent)
                                        .frame(width: 8, height: 8)
                                        .offset(x: 4, y: -4)
                                }
                            }
                        }
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 12) {
                        if selectedTab == 0 {
                            Menu {
                                ForEach(ExpenseSort.allCases, id: \.self) { sort in
                                    Button {
                                        sortOrder = sort
                                    } label: {
                                        if sort == sortOrder {
                                            Label(sort.rawValue, systemImage: "checkmark")
                                        } else {
                                            Text(sort.rawValue)
                                        }
                                    }
                                }
                            } label: {
                                Image(systemName: "arrow.up.arrow.down.circle")
                            }

                            Button {
                                showingAddExpense = true
                            } label: {
                                Image(systemName: "plus.circle.fill")
                            }
                        }

                        Button { showSettings = true } label: {
                            Image(systemName: "gearshape")
                        }
                    }
                }
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
            }
            .sheet(isPresented: $showingAddExpense) {
                AddExpenseView(availableCategories: viewModel.availableCategories) { expense in
                    await viewModel.addExpense(expense)
                }
            }
            .sheet(isPresented: $showingFilters) {
                FiltersView(viewModel: viewModel)
            }
            .task {
                await viewModel.loadExpenses()
            }
            .task(id: selectedTab) {
                if selectedTab == 1 {
                    await viewModel.loadRecurring()
                }
            }
            .refreshable {
                if selectedTab == 0 {
                    await viewModel.refresh()
                } else {
                    await viewModel.loadRecurring()
                }
            }
            .overlay {
                if selectedTab == 0 && viewModel.isLoading && viewModel.expenses.isEmpty {
                    ProgressView()
                }
                if selectedTab == 1 && viewModel.isLoadingRecurring && activeRecurringExpenses.isEmpty {
                    ProgressView()
                }
            }
            .onChange(of: viewModel.errorMessage) { _, newValue in
                showErrorAlert = newValue != nil
            }
            .alert("Error", isPresented: $showErrorAlert) {
                Button("OK") { viewModel.errorMessage = nil }
            } message: {
                Text(viewModel.errorMessage ?? "")
            }
            .alert("Delete Recurring Expense", isPresented: .constant(recurringToDelete != nil)) {
                Button("Cancel", role: .cancel) { recurringToDelete = nil }
                Button("Delete", role: .destructive) {
                    if let item = recurringToDelete {
                        Task { await viewModel.deleteRecurring(id: item.template_id) }
                        recurringToDelete = nil
                    }
                }
            } message: {
                if let item = recurringToDelete {
                    Text("Are you sure you want to delete \"\(item.expense_name)\"? This cannot be undone.")
                }
            }
        }
    }

    private var activeRecurringExpenses: [RecurringExpenseAPI] {
        viewModel.recurringExpenses.filter { $0.active }
    }

    private var sortedFilteredExpenses: [Expense] {
        let filtered = viewModel.filteredExpenses
        switch sortOrder {
        case .newest:
            return filtered.sorted { $0.date > $1.date }
        case .oldest:
            return filtered.sorted { $0.date < $1.date }
        case .highestAmount:
            return filtered.sorted { $0.amount > $1.amount }
        case .lowestAmount:
            return filtered.sorted { $0.amount < $1.amount }
        }
    }

    private var sortedGroupedExpenses: [Date: [Expense]] {
        Dictionary(grouping: sortedFilteredExpenses) { expense in
            Calendar.current.startOfDay(for: expense.date)
        }
    }

    private var expensesList: some View {
        List {
            if !viewModel.pendingExpenses.isEmpty {
                Section {
                    ForEach(viewModel.pendingExpenses) { pending in
                        PendingExpenseRow(
                            pending: pending,
                            onConfirm: { await viewModel.confirmPending(id: pending.pending_id) },
                            onSkip: { await viewModel.skipPending(id: pending.pending_id) }
                        )
                    }
                } header: {
                    HStack {
                        Image(systemName: "clock.badge.exclamationmark")
                            .foregroundStyle(.orange)
                        Text("Pending")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                    }
                }
            }

            if sortOrder == .newest || sortOrder == .oldest {
                let sortedKeys = sortedGroupedExpenses.keys.sorted(by: sortOrder == .newest ? (>) : (<))
                ForEach(sortedKeys, id: \.self) { date in
                    Section {
                        ForEach(sortedGroupedExpenses[date] ?? []) { expense in
                            expenseRow(expense)
                        }
                    } header: {
                        Text(date, style: .date)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                    }
                }
            } else {
                ForEach(sortedFilteredExpenses) { expense in
                    expenseRow(expense)
                }
            }
        }
        .listStyle(.insetGrouped)
        .sheet(item: $viewModel.selectedExpense) { expense in
            EditExpenseView(
                expense: expense,
                availableCategories: viewModel.availableCategories
            ) { updated in
                await viewModel.updateExpense(updated)
            }
        }
    }

    private func expenseRow(_ expense: Expense) -> some View {
        ExpenseRowView(expense: expense)
            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                Button(role: .destructive) {
                    Task { await viewModel.deleteExpense(expense) }
                } label: {
                    Label("Delete", systemImage: "trash")
                }
            }
            .swipeActions(edge: .leading) {
                Button {
                    viewModel.selectedExpense = expense
                } label: {
                    Label("Edit", systemImage: "pencil")
                }
                .tint(.blue)
            }
    }

    private var recurringList: some View {
        List {
            ForEach(activeRecurringExpenses) { recurring in
                RecurringExpenseRow(recurring: recurring)
                    .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                        Button(role: .destructive) {
                            recurringToDelete = recurring
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    }
            }
        }
        .listStyle(.insetGrouped)
    }

    private var emptyStateView: some View {
        ContentUnavailableView(
            "No Expenses",
            systemImage: "dollarsign.circle",
            description: Text("Add your first expense to get started tracking your budget.")
        )
    }

    private var recurringEmptyStateView: some View {
        ContentUnavailableView(
            "No Recurring Expenses",
            systemImage: "arrow.clockwise.circle",
            description: Text("Set up recurring expenses in the chat to have them tracked automatically.")
        )
    }
}

// MARK: - Expense Row

struct ExpenseRowView: View {
    let expense: Expense

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: AppTheme.sfSymbol(for: expense.categoryEmoji))
                .font(.title3)
                .foregroundStyle(expense.categoryColor)
                .frame(width: 40, height: 40)
                .background(expense.categoryColor.opacity(0.15))
                .cornerRadius(8)

            VStack(alignment: .leading, spacing: 4) {
                Text(expense.description)
                    .font(.subheadline)
                    .fontWeight(.medium)

                HStack(spacing: 8) {
                    Text(expense.categoryDisplayName)
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if let notes = expense.notes, !notes.isEmpty {
                        Text("•")
                            .foregroundStyle(.secondary)
                        Text(notes)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }
            }

            Spacer()

            Text(expense.amount, format: .currency(code: "USD"))
                .font(.subheadline)
                .fontWeight(.semibold)
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Add Expense View

struct AddExpenseView: View {
    @Environment(\.dismiss) private var dismiss
    let availableCategories: [APICategory]
    let onSave: (Expense) async -> Void

    @State private var description = ""
    @State private var amount = ""
    @State private var selectedCategoryId = ""
    @State private var date = Date()
    @State private var notes = ""
    @State private var isSaving = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Description", text: $description)

                    TextField("Amount", text: $amount)
                        .keyboardType(.decimalPad)

                    if availableCategories.isEmpty {
                        Text("Loading categories…")
                            .foregroundStyle(.secondary)
                    } else {
                        Picker("Category", selection: $selectedCategoryId) {
                            ForEach(availableCategories, id: \.category_id) { cat in
                                Label(cat.display_name, systemImage: AppTheme.sfSymbol(for: cat.icon))
                                    .tag(cat.category_id)
                            }
                        }
                    }

                    DatePicker("Date", selection: $date, displayedComponents: .date)
                }

                Section {
                    TextField("Notes (optional)", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .navigationTitle("Add Expense")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await saveExpense() }
                    }
                    .disabled(!isValid || isSaving)
                }
            }
            .overlay {
                if isSaving { ProgressView() }
            }
            .onAppear {
                if selectedCategoryId.isEmpty, let first = availableCategories.first {
                    selectedCategoryId = first.category_id
                }
            }
        }
    }

    private var isValid: Bool {
        !description.isEmpty && !selectedCategoryId.isEmpty
            && Double(amount) != nil && Double(amount)! > 0
    }

    private func saveExpense() async {
        guard let amountValue = Double(amount) else { return }
        let cat = availableCategories.first { $0.category_id == selectedCategoryId }
        isSaving = true
        let expense = Expense(
            backendId: nil,
            description: description,
            amount: amountValue,
            category: selectedCategoryId,
            categoryDisplayName: cat?.display_name ?? selectedCategoryId,
            categoryEmoji: cat?.icon ?? "📦",
            categoryHexColor: cat?.color ?? "#6B7280",
            date: date,
            notes: notes.isEmpty ? nil : notes
        )
        await onSave(expense)
        isSaving = false
        dismiss()
    }
}

// MARK: - Edit Expense View

struct EditExpenseView: View {
    @Environment(\.dismiss) private var dismiss
    let expense: Expense
    let availableCategories: [APICategory]
    let onSave: (Expense) async -> Void

    @State private var description: String
    @State private var amount: String
    @State private var selectedCategoryId: String
    @State private var date: Date
    @State private var notes: String
    @State private var isSaving = false

    init(expense: Expense, availableCategories: [APICategory], onSave: @escaping (Expense) async -> Void) {
        self.expense = expense
        self.availableCategories = availableCategories
        self.onSave = onSave
        _description = State(initialValue: expense.description)
        _amount = State(initialValue: String(format: "%.2f", expense.amount))
        _selectedCategoryId = State(initialValue: expense.category)
        _date = State(initialValue: expense.date)
        _notes = State(initialValue: expense.notes ?? "")
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Description", text: $description)

                    TextField("Amount", text: $amount)
                        .keyboardType(.decimalPad)

                    if !availableCategories.isEmpty {
                        Picker("Category", selection: $selectedCategoryId) {
                            ForEach(availableCategories, id: \.category_id) { cat in
                                Label(cat.display_name, systemImage: AppTheme.sfSymbol(for: cat.icon))
                                    .tag(cat.category_id)
                            }
                        }
                    }

                    DatePicker("Date", selection: $date, displayedComponents: .date)
                }

                Section {
                    TextField("Notes (optional)", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .navigationTitle("Edit Expense")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await saveExpense() }
                    }
                    .disabled(!isValid || isSaving)
                }
            }
            .overlay {
                if isSaving { ProgressView() }
            }
        }
    }

    private var isValid: Bool {
        !description.isEmpty && Double(amount) != nil && Double(amount)! > 0
    }

    private func saveExpense() async {
        guard let amountValue = Double(amount) else { return }
        let cat = availableCategories.first { $0.category_id == selectedCategoryId }
        isSaving = true
        var updated = expense
        updated.description = description
        updated.amount = amountValue
        updated.category = selectedCategoryId
        updated.categoryDisplayName = cat?.display_name ?? selectedCategoryId
        updated.categoryEmoji = cat?.icon ?? expense.categoryEmoji
        updated.categoryHexColor = cat?.color ?? expense.categoryHexColor
        updated.date = date
        updated.notes = notes.isEmpty ? nil : notes
        await onSave(updated)
        isSaving = false
        dismiss()
    }
}

// MARK: - Filters View

struct FiltersView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject var viewModel: ExpensesViewModel

    var body: some View {
        NavigationStack {
            Form {
                Section("Date Range") {
                    DatePicker("From", selection: $viewModel.filterStartDate, displayedComponents: .date)
                    DatePicker("To", selection: $viewModel.filterEndDate, displayedComponents: .date)
                }

                if !viewModel.availableCategories.isEmpty {
                    Section("Categories") {
                        ForEach(viewModel.availableCategories, id: \.category_id) { cat in
                            Toggle(isOn: Binding(
                                get: { viewModel.selectedCategories.contains(cat.category_id) },
                                set: { isOn in
                                    if isOn {
                                        viewModel.selectedCategories.insert(cat.category_id)
                                    } else {
                                        viewModel.selectedCategories.remove(cat.category_id)
                                    }
                                }
                            )) {
                                Label(cat.display_name, systemImage: AppTheme.sfSymbol(for: cat.icon))
                            }
                        }
                    }
                }

                Section("Amount Range") {
                    HStack {
                        Text("Min:")
                        TextField("0", value: $viewModel.minAmount, format: .currency(code: "USD"))
                            .keyboardType(.decimalPad)
                    }
                    HStack {
                        Text("Max:")
                        TextField("No limit", value: $viewModel.maxAmount, format: .currency(code: "USD"))
                            .keyboardType(.decimalPad)
                    }
                }

                Section {
                    Button("Reset Filters") { viewModel.resetFilters() }
                        .foregroundStyle(.red)
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

// MARK: - View Model

@MainActor
class ExpensesViewModel: ObservableObject {
    @Published var expenses: [Expense] = []
    @Published var pendingExpenses: [PendingExpense] = []
    @Published var recurringExpenses: [RecurringExpenseAPI] = []
    @Published var availableCategories: [APICategory] = []
    @Published var selectedExpense: Expense?
    @Published var isLoading = false
    @Published var isLoadingRecurring = false
    @Published var errorMessage: String?

    // Filters
    @Published var filterStartDate = Calendar.current.date(byAdding: .month, value: -1, to: Date()) ?? Date()
    @Published var filterEndDate = Calendar.current.date(bySettingHour: 23, minute: 59, second: 59, of: Date()) ?? Date()
    @Published var selectedCategories: Set<String> = []
    @Published var minAmount: Double?
    @Published var maxAmount: Double?

    private let api = APIService()

    var hasActiveFilters: Bool {
        !selectedCategories.isEmpty || minAmount != nil || maxAmount != nil
    }

    var filteredExpenses: [Expense] {
        expenses.filter { expense in
            let inDateRange = expense.date >= filterStartDate && expense.date <= filterEndDate
            let inCategory = selectedCategories.isEmpty || selectedCategories.contains(expense.category)
            let inAmountRange: Bool = {
                if let min = minAmount, expense.amount < min { return false }
                if let max = maxAmount, expense.amount > max { return false }
                return true
            }()
            return inDateRange && inCategory && inAmountRange
        }
    }

    func loadExpenses() async {
        isLoading = true
        errorMessage = nil

        let now = Date()
        let cal = Calendar.current
        let year = cal.component(.year, from: now)
        let month = cal.component(.month, from: now)

        do {
            async let categoriesFetch = api.fetchCategories()
            async let expensesFetch = api.fetchExpenses(year: year, month: month)
            let (cats, apiExpenses) = try await (categoriesFetch, expensesFetch)

            availableCategories = cats
            let catMap = Dictionary(uniqueKeysWithValues: cats.map { ($0.category_id, $0) })

            expenses = apiExpenses.map { apiExpense in
                let cat = catMap[apiExpense.category]
                let components = DateComponents(
                    year: apiExpense.date.year,
                    month: apiExpense.date.month,
                    day: apiExpense.date.day
                )
                let date = cal.date(from: components) ?? now
                return Expense(
                    backendId: apiExpense.id,
                    description: apiExpense.expense_name,
                    amount: apiExpense.amount,
                    category: apiExpense.category,
                    categoryDisplayName: cat?.display_name ?? apiExpense.category,
                    categoryEmoji: cat?.icon ?? "📦",
                    categoryHexColor: cat?.color ?? "#6B7280",
                    date: date
                )
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
        await fetchPendingExpenses()
    }

    func fetchPendingExpenses() async {
        do {
            pendingExpenses = try await api.fetchPending()
        } catch { }
    }

    func confirmPending(id: String) async {
        do {
            try await api.confirmPending(id: id)
            pendingExpenses.removeAll { $0.pending_id == id }
            await loadExpenses()  // refresh expenses list after confirming
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func skipPending(id: String) async {
        do {
            try await api.skipPending(id: id)
            pendingExpenses.removeAll { $0.pending_id == id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refresh() async {
        await loadExpenses()
    }

    func addExpense(_ expense: Expense) async {
        let text = "\(expense.description) $\(String(format: "%.2f", expense.amount))"
        do {
            _ = try await api.addExpenseViaMCP(text: text)
            await loadExpenses()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func updateExpense(_ expense: Expense) async {
        guard let backendId = expense.backendId else {
            if let index = expenses.firstIndex(where: { $0.id == expense.id }) {
                expenses[index] = expense
            }
            return
        }
        let cal = Calendar.current
        let dateDict: [String: Int] = [
            "day": cal.component(.day, from: expense.date),
            "month": cal.component(.month, from: expense.date),
            "year": cal.component(.year, from: expense.date)
        ]
        do {
            try await api.updateExpense(
                id: backendId,
                name: expense.description,
                amount: expense.amount,
                category: expense.category,
                date: dateDict
            )
            if let index = expenses.firstIndex(where: { $0.id == expense.id }) {
                expenses[index] = expense
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteExpense(_ expense: Expense) async {
        guard let backendId = expense.backendId else {
            expenses.removeAll { $0.id == expense.id }
            return
        }
        do {
            try await api.deleteExpense(id: backendId)
            expenses.removeAll { $0.id == expense.id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadRecurring() async {
        isLoadingRecurring = true
        do {
            recurringExpenses = try await api.fetchRecurring()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoadingRecurring = false
    }

    func deleteRecurring(id: String) async {
        do {
            try await api.deleteRecurring(id: id)
            recurringExpenses.removeAll { $0.template_id == id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func resetFilters() {
        filterStartDate = Calendar.current.date(byAdding: .month, value: -1, to: Date()) ?? Date()
        filterEndDate = Calendar.current.date(bySettingHour: 23, minute: 59, second: 59, of: Date()) ?? Date()
        selectedCategories = []
        minAmount = nil
        maxAmount = nil
    }
}

// MARK: - Recurring Expense Row

struct RecurringExpenseRow: View {
    let recurring: RecurringExpenseAPI

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: AppTheme.sfSymbol(for: recurring.category))
                .font(.title3)
                .foregroundStyle(AppTheme.categoryColor(recurring.category))
                .frame(width: 40, height: 40)
                .background(AppTheme.categoryColor(recurring.category).opacity(0.15))
                .cornerRadius(8)

            VStack(alignment: .leading, spacing: 4) {
                Text(recurring.expense_name)
                    .font(.subheadline)
                    .fontWeight(.medium)

                Text(scheduleDescription)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Text(recurring.amount, format: .currency(code: "USD"))
                .font(.subheadline)
                .fontWeight(.semibold)
        }
        .padding(.vertical, 4)
    }

    private var scheduleDescription: String {
        switch recurring.frequency.lowercased() {
        case "monthly":
            if recurring.last_of_month == true {
                return "Last day of month"
            } else if let day = recurring.day_of_month {
                return "\(ordinal(day)) of each month"
            }
            return "Monthly"
        case "weekly":
            if let dow = recurring.day_of_week {
                return "Every \(dayName(dow))"
            }
            return "Weekly"
        case "biweekly":
            if let dow = recurring.day_of_week {
                return "Every other \(dayName(dow))"
            }
            return "Every other week"
        case "yearly":
            return "Yearly"
        default:
            return recurring.frequency.capitalized
        }
    }

    private func dayName(_ index: Int) -> String {
        // 0=Mon, 1=Tue, ..., 6=Sun
        let names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        guard index >= 0 && index < names.count else { return "Day \(index)" }
        return names[index]
    }

    private func ordinal(_ n: Int) -> String {
        let suffix: String
        let ones = n % 10
        let tens = (n / 10) % 10
        if tens == 1 {
            suffix = "th"
        } else {
            switch ones {
            case 1: suffix = "st"
            case 2: suffix = "nd"
            case 3: suffix = "rd"
            default: suffix = "th"
            }
        }
        return "\(n)\(suffix)"
    }
}

// MARK: - Pending Expense Row

struct PendingExpenseRow: View {
    let pending: PendingExpense
    let onConfirm: () async -> Void
    let onSkip: () async -> Void
    @Environment(\.appAccent) private var appAccent
    @State private var isConfirming = false
    @State private var isSkipping = false

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: AppTheme.sfSymbol(for: pending.category))
                .font(.title3)
                .foregroundStyle(AppTheme.categoryColor(pending.category))
                .frame(width: 40, height: 40)
                .background(Color.orange.opacity(0.15))
                .clipShape(RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading, spacing: 4) {
                Text(pending.expense_name)
                    .font(.subheadline)
                    .fontWeight(.medium)

                Text("Awaiting confirmation")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }

            Spacer()

            Text(pending.amount, format: .currency(code: "USD"))
                .font(.subheadline)
                .fontWeight(.semibold)

            HStack(spacing: 8) {
                Button {
                    isConfirming = true
                    Task {
                        await onConfirm()
                        isConfirming = false
                    }
                } label: {
                    if isConfirming {
                        ProgressView().scaleEffect(0.7)
                    } else {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(appAccent)
                            .font(.title3)
                    }
                }
                .disabled(isConfirming || isSkipping)

                Button {
                    isSkipping = true
                    Task {
                        await onSkip()
                        isSkipping = false
                    }
                } label: {
                    if isSkipping {
                        ProgressView().scaleEffect(0.7)
                    } else {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.red)
                            .font(.title3)
                    }
                }
                .disabled(isConfirming || isSkipping)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Expense Model

struct Expense: Identifiable, Hashable {
    let id: UUID
    var backendId: String?
    var description: String
    var amount: Double
    var category: String
    var categoryDisplayName: String
    var categoryEmoji: String
    var categoryHexColor: String
    var date: Date
    var notes: String?

    init(
        backendId: String? = nil,
        description: String,
        amount: Double,
        category: String,
        categoryDisplayName: String = "",
        categoryEmoji: String = "📦",
        categoryHexColor: String = "#6B7280",
        date: Date,
        notes: String? = nil
    ) {
        self.id = UUID()
        self.backendId = backendId
        self.description = description
        self.amount = amount
        self.category = category
        self.categoryDisplayName = categoryDisplayName.isEmpty ? category : categoryDisplayName
        self.categoryEmoji = categoryEmoji
        self.categoryHexColor = categoryHexColor
        self.date = date
        self.notes = notes
    }

    var categoryColor: Color {
        Color(hex: categoryHexColor) ?? .gray
    }
}

#Preview("Expenses List") {
    ExpensesView()
}

#Preview("Add Expense") {
    AddExpenseView(availableCategories: []) { _ in }
}
