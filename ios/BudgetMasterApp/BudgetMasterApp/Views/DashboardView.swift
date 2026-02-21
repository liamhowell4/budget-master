import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @StateObject private var viewModel = DashboardViewModel()
    @State private var selectedCategory: CategoryBreakdown?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    if let summary = viewModel.budgetSummary {
                        budgetSummaryCard(summary)
                    }

                    if !viewModel.categories.isEmpty {
                        categoryBreakdownSection
                    }

                    if !viewModel.recentExpenses.isEmpty {
                        recentExpensesSection
                    }
                }
                .padding()
            }
            .navigationTitle("Dashboard")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            Task { await viewModel.refresh() }
                        } label: {
                            Label("Refresh", systemImage: "arrow.clockwise")
                        }

                        Divider()

                        Button(role: .destructive) {
                            authManager.signOut()
                        } label: {
                            Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .refreshable {
                await viewModel.refresh()
            }
            .task {
                await viewModel.loadData()
            }
            .overlay {
                if viewModel.isLoading && viewModel.budgetSummary == nil {
                    ProgressView()
                }
            }
            .sheet(item: $selectedCategory) { category in
                CategoryDetailSheet(category: category)
            }
        }
    }

    // MARK: - Budget Summary Card

    private func budgetSummaryCard(_ summary: BudgetSummary) -> some View {
        VStack(spacing: 16) {
            // Primary stat: Total Remaining
            VStack(spacing: 4) {
                Text("Total Remaining")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                Text(summary.remaining, format: .currency(code: "USD"))
                    .font(.system(size: 40, weight: .bold))
                    .foregroundStyle(
                        summary.remaining < 0
                            ? Color.red
                            : AppTheme.budgetProgressColor(summary.percentage)
                    )
            }

            // Progress bar
            VStack(spacing: 4) {
                ProgressView(value: min(summary.percentage / 100, 1.0))
                    .tint(AppTheme.budgetProgressColor(summary.percentage))
                    .progressViewStyle(.linear)

                HStack {
                    Text("\(Int(summary.percentage))% used")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Spacer()
                }
            }

            Divider()

            // Secondary stats row
            HStack(spacing: 0) {
                budgetStatItem(title: "Spent", value: summary.totalSpent)
                Divider().frame(height: 36)
                budgetStatItem(title: "Budget", value: summary.totalBudget)
                Divider().frame(height: 36)
                budgetStatText(title: "% Used", text: "\(Int(summary.percentage))%")
            }
            .frame(maxWidth: .infinity)
        }
        .padding()
        .glassCard()
    }

    private func budgetStatItem(title: String, value: Double) -> some View {
        VStack(spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value, format: .currency(code: "USD"))
                .font(.subheadline)
                .fontWeight(.semibold)
        }
        .frame(maxWidth: .infinity)
    }

    private func budgetStatText(title: String, text: String) -> some View {
        VStack(spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(text)
                .font(.subheadline)
                .fontWeight(.semibold)
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Category Breakdown Grid

    private var categoryBreakdownSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Category Breakdown")
                .font(.headline)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                ForEach(viewModel.categories) { category in
                    Button { selectedCategory = category } label: {
                        categoryCard(category)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func categoryCard(_ category: CategoryBreakdown) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: AppTheme.sfSymbol(for: category.icon))
                    .font(.title3)
                    .foregroundStyle(category.color)
                Spacer()
                Text(category.amount, format: .currency(code: "USD"))
                    .font(.caption)
                    .fontWeight(.semibold)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
            }

            Text(category.name)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)

            ProgressView(value: min(category.percentage / 100, 1.0))
                .tint(AppTheme.budgetProgressColor(category.percentage))
                .progressViewStyle(.linear)
                .scaleEffect(x: 1, y: 0.7, anchor: .center)
        }
        .padding(12)
        .glassCard(cornerRadius: 16)
    }

    // MARK: - Recent Expenses

    private var recentExpensesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Recent Expenses")
                    .font(.headline)

                Spacer()

                NavigationLink {
                    ExpensesView()
                } label: {
                    Text("See All")
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.accent)
                }
            }

            VStack(spacing: 0) {
                ForEach(viewModel.recentExpenses) { expense in
                    expenseRow(expense)

                    if expense.id != viewModel.recentExpenses.last?.id {
                        Divider()
                            .padding(.leading, 60)
                    }
                }
            }
            .glassCard()
        }
    }

    private func expenseRow(_ expense: RecentExpense) -> some View {
        HStack(spacing: 12) {
            Image(systemName: AppTheme.sfSymbol(for: expense.icon))
                .font(.title3)
                .foregroundStyle(expense.categoryColor)
                .frame(width: 40, height: 40)
                .background(expense.categoryColor.opacity(0.15))
                .cornerRadius(8)

            VStack(alignment: .leading, spacing: 4) {
                Text(expense.description)
                    .font(.subheadline)
                    .fontWeight(.medium)

                Text(expense.category)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(expense.amount, format: .currency(code: "USD"))
                    .font(.subheadline)
                    .fontWeight(.semibold)

                Text(expense.date, style: .date)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
    }
}

// MARK: - View Model

@MainActor
class DashboardViewModel: ObservableObject {
    @Published var budgetSummary: BudgetSummary?
    @Published var categories: [CategoryBreakdown] = []
    @Published var recentExpenses: [RecentExpense] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService()

    func loadData() async {
        isLoading = true
        errorMessage = nil

        let now = Date()
        let cal = Calendar.current
        let year = cal.component(.year, from: now)
        let month = cal.component(.month, from: now)

        do {
            async let budgetFetch = api.fetchBudget()
            async let categoriesFetch = api.fetchCategories()
            async let expensesFetch = api.fetchExpenses(year: year, month: month)

            let (budget, apiCategories, expenses) = try await (budgetFetch, categoriesFetch, expensesFetch)

            let catMap = Dictionary(uniqueKeysWithValues: apiCategories.map { ($0.category_id, $0) })

            budgetSummary = BudgetSummary(
                totalSpent: budget.total_spending,
                totalBudget: budget.total_cap,
                remaining: budget.total_remaining,
                thisMonth: budget.total_spending,
                percentage: budget.total_percentage
            )

            categories = budget.categories
                .filter { $0.spending > 0 }
                .sorted { $0.spending > $1.spending }
                .map { budgetCat in
                    let cat = catMap[budgetCat.category]
                    return CategoryBreakdown(
                        categoryId: budgetCat.category,
                        name: cat?.display_name ?? budgetCat.category,
                        amount: budgetCat.spending,
                        cap: budgetCat.cap,
                        percentage: budgetCat.percentage,
                        color: Color(hex: cat?.color ?? "") ?? .gray,
                        icon: cat?.icon ?? budgetCat.emoji
                    )
                }

            recentExpenses = expenses.prefix(3).compactMap { expense in
                let components = DateComponents(
                    year: expense.date.year,
                    month: expense.date.month,
                    day: expense.date.day
                )
                let date = cal.date(from: components) ?? now
                let cat = catMap[expense.category]
                return RecentExpense(
                    description: expense.expense_name,
                    category: cat?.display_name ?? expense.category,
                    amount: expense.amount,
                    date: date,
                    icon: cat?.icon ?? "📦",
                    categoryColor: Color(hex: cat?.color ?? "") ?? .gray
                )
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func refresh() async {
        await loadData()
    }
}

// MARK: - Models

struct BudgetSummary {
    let totalSpent: Double
    let totalBudget: Double
    let remaining: Double
    let thisMonth: Double
    let percentage: Double
}

struct CategoryBreakdown: Identifiable {
    let id = UUID()
    let categoryId: String
    let name: String
    let amount: Double
    let cap: Double
    let percentage: Double
    let color: Color
    let icon: String
}

struct RecentExpense: Identifiable {
    let id = UUID()
    let description: String
    let category: String
    let amount: Double
    let date: Date
    let icon: String
    let categoryColor: Color
}

// MARK: - Category Detail Sheet

struct CategoryDetailSheet: View {
    let category: CategoryBreakdown
    @StateObject private var vm: CategoryDetailViewModel

    init(category: CategoryBreakdown) {
        self.category = category
        _vm = StateObject(wrappedValue: CategoryDetailViewModel(categoryId: category.categoryId))
    }

    var body: some View {
        NavigationStack {
            List {
                // Stats header
                Section {
                    VStack(spacing: 16) {
                        HStack(spacing: 16) {
                            statCell(title: "Spent",   text: category.amount.formatted(.currency(code: "USD")))
                            Divider().frame(height: 36)
                            statCell(title: "Budget",  text: category.cap.formatted(.currency(code: "USD")))
                            Divider().frame(height: 36)
                            statCell(title: "% Used",  text: "\(Int(category.percentage))%",
                                     color: AppTheme.budgetProgressColor(category.percentage))
                        }

                        ProgressView(value: min(category.percentage / 100, 1.0))
                            .tint(AppTheme.budgetProgressColor(category.percentage))
                            .progressViewStyle(.linear)
                    }
                    .padding(.vertical, 8)
                }

                // Expense rows
                Section("This Month") {
                    if vm.isLoading {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                        .listRowBackground(Color.clear)
                    } else if vm.expenses.isEmpty {
                        Text("No expenses this month")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(vm.expenses) { expense in
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(expense.name)
                                        .font(.subheadline)
                                    Text(expense.date, style: .date)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Text(expense.amount, format: .currency(code: "USD"))
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                            }
                        }
                    }
                }
            }
            .navigationTitle(category.name)
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Image(systemName: AppTheme.sfSymbol(for: category.icon))
                        .foregroundStyle(category.color)
                        .font(.title3)
                }
            }
        }
        .task { await vm.load() }
    }

    private func statCell(title: String, text: String, color: Color = .primary) -> some View {
        VStack(spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(text)
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(color)
        }
        .frame(maxWidth: .infinity)
    }
}

@MainActor
class CategoryDetailViewModel: ObservableObject {
    let categoryId: String
    @Published var expenses: [CategoryExpenseRow] = []
    @Published var isLoading = false

    private let api = APIService()

    init(categoryId: String) {
        self.categoryId = categoryId
    }

    func load() async {
        isLoading = true
        let cal = Calendar.current
        let now = Date()
        let year = cal.component(.year, from: now)
        let month = cal.component(.month, from: now)

        do {
            let raw = try await api.fetchExpenses(year: year, month: month, category: categoryId)
            expenses = raw.compactMap { e in
                let comps = DateComponents(year: e.date.year, month: e.date.month, day: e.date.day)
                let date = cal.date(from: comps) ?? now
                return CategoryExpenseRow(id: e.id, name: e.expense_name, amount: e.amount, date: date)
            }
            .sorted { $0.date > $1.date }
        } catch {
            // Non-fatal; list stays empty
        }

        isLoading = false
    }
}

struct CategoryExpenseRow: Identifiable {
    let id: String
    let name: String
    let amount: Double
    let date: Date
}

#Preview {
    DashboardView()
        .environmentObject(AuthenticationManager())
}
