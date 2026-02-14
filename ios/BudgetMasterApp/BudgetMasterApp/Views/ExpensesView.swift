import SwiftUI

struct ExpensesView: View {
    @StateObject private var viewModel = ExpensesViewModel()
    @State private var showingAddExpense = false
    @State private var showingFilters = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                if viewModel.filteredExpenses.isEmpty && !viewModel.isLoading {
                    emptyStateView
                } else {
                    expensesList
                }
            }
            .navigationTitle("Expenses")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showingFilters = true
                    } label: {
                        Label("Filters", systemImage: viewModel.hasActiveFilters ? "line.3.horizontal.decrease.circle.fill" : "line.3.horizontal.decrease.circle")
                    }
                }
                
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showingAddExpense = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                    }
                }
            }
            .sheet(isPresented: $showingAddExpense) {
                AddExpenseView { expense in
                    await viewModel.addExpense(expense)
                }
            }
            .sheet(isPresented: $showingFilters) {
                FiltersView(viewModel: viewModel)
            }
            .task {
                await viewModel.loadExpenses()
            }
            .refreshable {
                await viewModel.refresh()
            }
            .overlay {
                if viewModel.isLoading && viewModel.expenses.isEmpty {
                    ProgressView()
                }
            }
        }
    }
    
    private var expensesList: some View {
        List {
            ForEach(viewModel.groupedExpenses.keys.sorted(by: >), id: \.self) { date in
                Section {
                    ForEach(viewModel.groupedExpenses[date] ?? []) { expense in
                        ExpenseRowView(expense: expense)
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    Task {
                                        await viewModel.deleteExpense(expense)
                                    }
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
                } header: {
                    Text(date, style: .date)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
            }
        }
        .listStyle(.insetGrouped)
        .sheet(item: $viewModel.selectedExpense) { expense in
            EditExpenseView(expense: expense) { updated in
                await viewModel.updateExpense(updated)
            }
        }
    }
    
    private var emptyStateView: some View {
        ContentUnavailableView(
            "No Expenses",
            systemImage: "dollarsign.circle",
            description: Text("Add your first expense to get started tracking your budget.")
        )
    }
}

// MARK: - Expense Row

struct ExpenseRowView: View {
    let expense: Expense
    
    var body: some View {
        HStack(spacing: 12) {
            // Category icon
            Image(systemName: expense.categoryIcon)
                .font(.title3)
                .foregroundStyle(expense.categoryColor)
                .frame(width: 40, height: 40)
                .background(expense.categoryColor.opacity(0.1))
                .cornerRadius(8)
            
            // Details
            VStack(alignment: .leading, spacing: 4) {
                Text(expense.description)
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                HStack(spacing: 8) {
                    Text(expense.category)
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
            
            // Amount
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
    let onSave: (Expense) async -> Void
    
    @State private var description = ""
    @State private var amount = ""
    @State private var category = "Food"
    @State private var date = Date()
    @State private var notes = ""
    @State private var isSaving = false
    
    let categories = ["Food", "Transportation", "Entertainment", "Shopping", "Bills", "Health", "Other"]
    
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Description", text: $description)
                    
                    TextField("Amount", text: $amount)
                        .keyboardType(.decimalPad)
                    
                    Picker("Category", selection: $category) {
                        ForEach(categories, id: \.self) { cat in
                            Text(cat).tag(cat)
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
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await saveExpense()
                        }
                    }
                    .disabled(!isValid || isSaving)
                }
            }
            .overlay {
                if isSaving {
                    ProgressView()
                }
            }
        }
    }
    
    private var isValid: Bool {
        !description.isEmpty && Double(amount) != nil && Double(amount)! > 0
    }
    
    private func saveExpense() async {
        guard let amountValue = Double(amount) else { return }
        
        isSaving = true
        
        let expense = Expense(
            description: description,
            amount: amountValue,
            category: category,
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
    let onSave: (Expense) async -> Void
    
    @State private var description: String
    @State private var amount: String
    @State private var category: String
    @State private var date: Date
    @State private var notes: String
    @State private var isSaving = false
    
    let categories = ["Food", "Transportation", "Entertainment", "Shopping", "Bills", "Health", "Other"]
    
    init(expense: Expense, onSave: @escaping (Expense) async -> Void) {
        self.expense = expense
        self.onSave = onSave
        _description = State(initialValue: expense.description)
        _amount = State(initialValue: String(expense.amount))
        _category = State(initialValue: expense.category)
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
                    
                    Picker("Category", selection: $category) {
                        ForEach(categories, id: \.self) { cat in
                            Text(cat).tag(cat)
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
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await saveExpense()
                        }
                    }
                    .disabled(!isValid || isSaving)
                }
            }
            .overlay {
                if isSaving {
                    ProgressView()
                }
            }
        }
    }
    
    private var isValid: Bool {
        !description.isEmpty && Double(amount) != nil && Double(amount)! > 0
    }
    
    private func saveExpense() async {
        guard let amountValue = Double(amount) else { return }
        
        isSaving = true
        
        var updated = expense
        updated.description = description
        updated.amount = amountValue
        updated.category = category
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
                
                Section("Categories") {
                    ForEach(viewModel.availableCategories, id: \.self) { category in
                        Toggle(category, isOn: Binding(
                            get: { viewModel.selectedCategories.contains(category) },
                            set: { isSelected in
                                if isSelected {
                                    viewModel.selectedCategories.insert(category)
                                } else {
                                    viewModel.selectedCategories.remove(category)
                                }
                            }
                        ))
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
                    Button("Reset Filters") {
                        viewModel.resetFilters()
                    }
                    .foregroundStyle(.red)
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}

// MARK: - View Model

@MainActor
class ExpensesViewModel: ObservableObject {
    @Published var expenses: [Expense] = []
    @Published var selectedExpense: Expense?
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    // Filters
    @Published var filterStartDate = Calendar.current.date(byAdding: .month, value: -1, to: Date()) ?? Date()
    @Published var filterEndDate = Date()
    @Published var selectedCategories: Set<String> = []
    @Published var minAmount: Double?
    @Published var maxAmount: Double?
    
    let availableCategories = ["Food", "Transportation", "Entertainment", "Shopping", "Bills", "Health", "Other"]
    
    var hasActiveFilters: Bool {
        !selectedCategories.isEmpty || minAmount != nil || maxAmount != nil
    }
    
    var filteredExpenses: [Expense] {
        expenses.filter { expense in
            // Date filter
            let inDateRange = expense.date >= filterStartDate && expense.date <= filterEndDate
            
            // Category filter
            let inCategory = selectedCategories.isEmpty || selectedCategories.contains(expense.category)
            
            // Amount filter
            let inAmountRange: Bool = {
                if let min = minAmount, expense.amount < min {
                    return false
                }
                if let max = maxAmount, expense.amount > max {
                    return false
                }
                return true
            }()
            
            return inDateRange && inCategory && inAmountRange
        }
    }
    
    var groupedExpenses: [Date: [Expense]] {
        Dictionary(grouping: filteredExpenses) { expense in
            Calendar.current.startOfDay(for: expense.date)
        }
    }
    
    func loadExpenses() async {
        isLoading = true
        
        // Simulate API call
        try? await Task.sleep(for: .seconds(1))
        
        // Mock data - replace with actual API calls
        expenses = [
            Expense(description: "Grocery Store", amount: 85.50, category: "Food", date: Date(), notes: "Weekly shopping"),
            Expense(description: "Gas Station", amount: 45.00, category: "Transportation", date: Date().addingTimeInterval(-86400), notes: nil),
            Expense(description: "Movie Tickets", amount: 28.00, category: "Entertainment", date: Date().addingTimeInterval(-172800), notes: "Avatar 2"),
            Expense(description: "Amazon Order", amount: 120.00, category: "Shopping", date: Date().addingTimeInterval(-259200), notes: "Books and gadgets"),
            Expense(description: "Restaurant", amount: 65.00, category: "Food", date: Date().addingTimeInterval(-345600), notes: "Dinner with friends")
        ]
        
        isLoading = false
    }
    
    func refresh() async {
        await loadExpenses()
    }
    
    func addExpense(_ expense: Expense) async {
        // TODO: Call API to add expense
        expenses.insert(expense, at: 0)
    }
    
    func updateExpense(_ expense: Expense) async {
        // TODO: Call API to update expense
        if let index = expenses.firstIndex(where: { $0.id == expense.id }) {
            expenses[index] = expense
        }
    }
    
    func deleteExpense(_ expense: Expense) async {
        // TODO: Call API to delete expense
        expenses.removeAll { $0.id == expense.id }
    }
    
    func resetFilters() {
        filterStartDate = Calendar.current.date(byAdding: .month, value: -1, to: Date()) ?? Date()
        filterEndDate = Date()
        selectedCategories = []
        minAmount = nil
        maxAmount = nil
    }
}

// MARK: - Models

struct Expense: Identifiable, Hashable {
    let id = UUID()
    var description: String
    var amount: Double
    var category: String
    var date: Date
    var notes: String?
    
    var categoryIcon: String {
        switch category {
        case "Food": return "cart.fill"
        case "Transportation": return "car.fill"
        case "Entertainment": return "film.fill"
        case "Shopping": return "bag.fill"
        case "Bills": return "doc.text.fill"
        case "Health": return "cross.case.fill"
        default: return "tag.fill"
        }
    }
    
    var categoryColor: Color {
        switch category {
        case "Food": return .orange
        case "Transportation": return .blue
        case "Entertainment": return .purple
        case "Shopping": return .pink
        case "Bills": return .red
        case "Health": return .green
        default: return .gray
        }
    }
}

#Preview("Expenses List") {
    ExpensesView()
}

#Preview("Add Expense") {
    AddExpenseView { _ in }
}
