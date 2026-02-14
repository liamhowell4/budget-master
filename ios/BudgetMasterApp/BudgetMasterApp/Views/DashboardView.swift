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
            Image(systemName: expense.icon)
                .font(.title3)
                .foregroundStyle(expense.categoryColor)
                .frame(width: 40, height: 40)
                .background(expense.categoryColor.opacity(0.1))
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
    
    // TODO: Replace with actual API service from BudgetMaster package
    func loadData() async {
        isLoading = true
        
        // Simulate API call
        try? await Task.sleep(for: .seconds(1))
        
        // Mock data - replace with actual API calls
        budgetSummary = BudgetSummary(
            totalSpent: 2450.00,
            totalBudget: 3000.00,
            remaining: 550.00,
            thisMonth: 2450.00
        )
        
        categories = [
            CategoryBreakdown(name: "Food", amount: 850.00, percentage: 34.7, color: .orange),
            CategoryBreakdown(name: "Transportation", amount: 650.00, percentage: 26.5, color: .blue),
            CategoryBreakdown(name: "Entertainment", amount: 450.00, percentage: 18.4, color: .purple),
            CategoryBreakdown(name: "Shopping", amount: 300.00, percentage: 12.2, color: .pink),
            CategoryBreakdown(name: "Other", amount: 200.00, percentage: 8.2, color: .gray)
        ]
        
        recentExpenses = [
            RecentExpense(description: "Grocery Store", category: "Food", amount: 85.50, date: Date(), icon: "cart.fill", categoryColor: .orange),
            RecentExpense(description: "Gas Station", category: "Transportation", amount: 45.00, date: Date().addingTimeInterval(-86400), icon: "fuelpump.fill", categoryColor: .blue),
            RecentExpense(description: "Movie Tickets", category: "Entertainment", amount: 28.00, date: Date().addingTimeInterval(-172800), icon: "film.fill", categoryColor: .purple)
        ]
        
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
