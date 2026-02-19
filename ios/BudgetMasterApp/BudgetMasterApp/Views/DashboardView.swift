import SwiftUI
import Charts

struct DashboardView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @StateObject private var viewModel = DashboardViewModel()
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Header with user greeting
                    headerView
                    
                    // Budget Summary Card
                    if let summary = viewModel.budgetSummary {
                        budgetSummaryCard(summary)
                    }
                    
                    // Category Breakdown
                    if !viewModel.categories.isEmpty {
                        categoryBreakdownSection
                    }
                    
                    // Recent Expenses
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
                            Task {
                                await viewModel.refresh()
                            }
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
        }
    }
    
    // MARK: - Subviews
    
    private var headerView: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Hello, \(authManager.currentUser?.displayName ?? "there")!")
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("Here's your budget overview")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            
            Spacer()
        }
    }
    
    private func budgetSummaryCard(_ summary: BudgetSummary) -> some View {
        VStack(spacing: 16) {
            // Total spent
            VStack(spacing: 4) {
                Text("Total Spent")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                
                Text(summary.totalSpent, format: .currency(code: "USD"))
                    .font(.system(size: 40, weight: .bold))
                    .foregroundStyle(.primary)
            }
            
            Divider()
            
            // Stats grid
            HStack(spacing: 20) {
                statItem(
                    title: "Budget",
                    value: summary.totalBudget,
                    color: .blue
                )
                
                Divider()
                
                statItem(
                    title: "Remaining",
                    value: summary.remaining,
                    color: summary.remaining >= 0 ? .green : .red
                )
                
                Divider()
                
                statItem(
                    title: "This Month",
                    value: summary.thisMonth,
                    color: .orange
                )
            }
            .frame(maxWidth: .infinity)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 10, y: 4)
    }
    
    private func statItem(title: String, value: Double, color: Color) -> some View {
        VStack(spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            
            Text(value, format: .currency(code: "USD"))
                .font(.headline)
                .fontWeight(.semibold)
                .foregroundStyle(color)
        }
    }
    
    private var categoryBreakdownSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Category Breakdown")
                .font(.headline)
                .padding(.horizontal)
            
            VStack(spacing: 0) {
                // Chart
                if #available(iOS 16.0, *) {
                    Chart(viewModel.categories) { category in
                        BarMark(
                            x: .value("Amount", category.amount),
                            y: .value("Category", category.name)
                        )
                        .foregroundStyle(by: .value("Category", category.name))
                    }
                    .frame(height: CGFloat(viewModel.categories.count) * 40)
                    .padding()
                }
                
                // List
                ForEach(viewModel.categories) { category in
                    categoryRow(category)
                    
                    if category.id != viewModel.categories.last?.id {
                        Divider()
                            .padding(.leading)
                    }
                }
            }
            .background(Color(.systemBackground))
            .cornerRadius(16)
            .shadow(color: .black.opacity(0.05), radius: 10, y: 4)
        }
    }
    
    private func categoryRow(_ category: CategoryBreakdown) -> some View {
        HStack {
            Circle()
                .fill(category.color)
                .frame(width: 12, height: 12)
            
            Text(category.name)
                .font(.subheadline)
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 2) {
                Text(category.amount, format: .currency(code: "USD"))
                    .font(.subheadline)
                    .fontWeight(.semibold)
                
                Text("\(Int(category.percentage))%")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
    }
    
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
                        .foregroundStyle(.green)
                }
            }
            .padding(.horizontal)
            
            VStack(spacing: 0) {
                ForEach(viewModel.recentExpenses) { expense in
                    expenseRow(expense)
                    
                    if expense.id != viewModel.recentExpenses.last?.id {
                        Divider()
                            .padding(.leading)
                    }
                }
            }
            .background(Color(.systemBackground))
            .cornerRadius(16)
            .shadow(color: .black.opacity(0.05), radius: 10, y: 4)
        }
    }
    
    private func expenseRow(_ expense: RecentExpense) -> some View {
        HStack(spacing: 12) {
            Text(expense.icon)
                .font(.title3)
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

// MARK: - View Models and Models

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

            // Build a lookup map from category_id → APICategory
            let catMap = Dictionary(uniqueKeysWithValues: apiCategories.map { ($0.category_id, $0) })

            budgetSummary = BudgetSummary(
                totalSpent: budget.total_spending,
                totalBudget: budget.total_cap,
                remaining: budget.total_remaining,
                thisMonth: budget.total_spending
            )

            categories = budget.categories
                .filter { $0.spending > 0 }
                .sorted { $0.spending > $1.spending }
                .map { budgetCat in
                    let cat = catMap[budgetCat.category]
                    return CategoryBreakdown(
                        name: cat?.display_name ?? budgetCat.category,
                        amount: budgetCat.spending,
                        percentage: budgetCat.percentage,
                        color: Color(hex: cat?.color ?? "") ?? .gray
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

struct BudgetSummary {
    let totalSpent: Double
    let totalBudget: Double
    let remaining: Double
    let thisMonth: Double
}

struct CategoryBreakdown: Identifiable {
    let id = UUID()
    let name: String
    let amount: Double
    let percentage: Double
    let color: Color
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

#Preview {
    DashboardView()
        .environmentObject(AuthenticationManager())
}
