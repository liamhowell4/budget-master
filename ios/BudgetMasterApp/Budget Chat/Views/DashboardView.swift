import SwiftUI

private struct SettingsSheet: Identifiable {
    let tab: Int
    var id: Int { tab }
}

struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()
    @Environment(\.appAccent) private var appAccent
    @State private var selectedCategory: CategoryBreakdown?
    @State private var settingsSheet: SettingsSheet? = nil
    @State private var selectedYear: Int = Calendar.current.component(.year, from: Date())
    @State private var selectedMonth: Int = Calendar.current.component(.month, from: Date())
    @State private var showAllCategories = false

    private var isCurrentMonth: Bool {
        let cal = Calendar.current
        let now = Date()
        return selectedYear == cal.component(.year, from: now)
            && selectedMonth == cal.component(.month, from: now)
    }

    private var monthYearLabel: String {
        let comps = DateComponents(year: selectedYear, month: selectedMonth)
        let date = Calendar.current.date(from: comps) ?? Date()
        let formatter = DateFormatter()
        formatter.dateFormat = "MMMM yyyy"
        return formatter.string(from: date)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    monthNavigationHeader

                    if let summary = viewModel.budgetSummary {
                        budgetSummaryCard(summary)

                        if isCurrentMonth {
                            paceCard(summary)
                        }

                        if let excluded = viewModel.excludedCategories, !excluded.isEmpty {
                            excludedCategoriesNote(excluded)
                        }
                    }

                    if !viewModel.categories.isEmpty {
                        categoryBreakdownSection
                    }

                    if !viewModel.recentExpenses.isEmpty {
                        recentExpensesSection
                    }

                    TipsWidgetView()
                }
                .padding()
            }
            .navigationTitle("Dashboard")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { settingsSheet = SettingsSheet(tab: 0) } label: {
                        Image(systemName: "gearshape")
                    }
                }
            }
            .sheet(item: $settingsSheet) { sheet in
                SettingsView(initialTab: sheet.tab)
            }
            .refreshable {
                await viewModel.loadData(year: selectedYear, month: selectedMonth)
            }
            .task {
                await viewModel.loadData(year: selectedYear, month: selectedMonth)
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

    // MARK: - Month Navigation Header

    private var monthNavigationHeader: some View {
        VStack(spacing: 8) {
            HStack {
                Button {
                    navigateMonth(by: -1)
                } label: {
                    Image(systemName: "chevron.left")
                        .font(.title3)
                        .fontWeight(.semibold)
                        .foregroundStyle(appAccent)
                }

                Spacer()

                Text(monthYearLabel)
                    .font(.title3)
                    .fontWeight(.semibold)

                Spacer()

                Button {
                    navigateMonth(by: 1)
                } label: {
                    Image(systemName: "chevron.right")
                        .font(.title3)
                        .fontWeight(.semibold)
                        .foregroundStyle(isCurrentMonth ? .secondary.opacity(0.3) : appAccent)
                }
                .disabled(isCurrentMonth)
            }
            .padding(.horizontal, 4)

            if !isCurrentMonth {
                Button {
                    goToCurrentMonth()
                } label: {
                    Text("Go to Current Month")
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundStyle(appAccent)
                }
            }
        }
    }

    private func navigateMonth(by offset: Int) {
        var comps = DateComponents(year: selectedYear, month: selectedMonth)
        comps.month = (comps.month ?? 1) + offset
        if let newDate = Calendar.current.date(from: comps) {
            let cal = Calendar.current
            let newYear = cal.component(.year, from: newDate)
            let newMonth = cal.component(.month, from: newDate)

            // Don't go past current month
            let now = Date()
            let currentYear = cal.component(.year, from: now)
            let currentMonth = cal.component(.month, from: now)
            if newYear > currentYear || (newYear == currentYear && newMonth > currentMonth) {
                return
            }

            selectedYear = newYear
            selectedMonth = newMonth
            Task { await viewModel.loadData(year: selectedYear, month: selectedMonth) }
        }
    }

    private func goToCurrentMonth() {
        let cal = Calendar.current
        let now = Date()
        selectedYear = cal.component(.year, from: now)
        selectedMonth = cal.component(.month, from: now)
        Task { await viewModel.loadData(year: selectedYear, month: selectedMonth) }
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

    // MARK: - Pace Card

    private func paceCard(_ summary: BudgetSummary) -> some View {
        let cal = Calendar.current
        let now = Date()
        let currentDay = Double(cal.component(.day, from: now))
        let daysInMonth = Double(cal.range(of: .day, in: .month, for: now)?.count ?? 30)
        let monthProgress = currentDay / daysInMonth
        let percentage = summary.percentage

        let pace = monthProgress > 0 ? (percentage / 100.0) / monthProgress : 0
        let expectedSpending = summary.totalBudget * monthProgress
        let paceDifference = summary.totalSpent - expectedSpending

        let paceColor: Color = {
            if pace > 1.1 { return .red }
            if pace > 0.9 { return .orange }
            return appAccent
        }()

        return VStack(spacing: 10) {
            HStack {
                Image(systemName: "gauge.with.dots.needle.50percent")
                    .foregroundStyle(paceColor)
                Text("Spending Pace")
                    .font(.subheadline)
                    .fontWeight(.medium)
                Spacer()
            }

            HStack(spacing: 6) {
                Text(String(format: "%.1fx", pace))
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundStyle(paceColor)

                Text("pace")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                Spacer()

                Text(paceDifference >= 0
                     ? "\(formatCurrency(abs(paceDifference))) over"
                     : "\(formatCurrency(abs(paceDifference))) under")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundStyle(paceDifference >= 0 ? .red : appAccent)
            }

            // Day progress indicator
            VStack(spacing: 4) {
                ProgressView(value: monthProgress)
                    .tint(.secondary.opacity(0.5))
                    .progressViewStyle(.linear)

                Text("Day \(Int(currentDay)) of \(Int(daysInMonth)) (\(Int(monthProgress * 100))% through month)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .glassCard()
    }

    private func formatCurrency(_ value: Double) -> String {
        value.formatted(.currency(code: "USD"))
    }

    // MARK: - Excluded Categories Note

    private func excludedCategoriesNote(_ excluded: [String]) -> some View {
        // Map raw category IDs to user-facing display names via the loaded categories
        let displayNames = excluded.map { rawId -> String in
            viewModel.categories.first(where: {
                $0.categoryId.caseInsensitiveCompare(rawId) == .orderedSame
            })?.name ?? rawId
        }

        return HStack(spacing: 6) {
            Image(systemName: "eye.slash")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text("Total excludes: \(displayNames.joined(separator: ", "))")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 4)
    }

    // MARK: - Category Breakdown Grid

    private var categoryBreakdownSection: some View {
        let displayed = showAllCategories
            ? viewModel.categories
            : viewModel.categories.filter { $0.amount > 0 }

        return VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Category Breakdown")
                    .font(.headline)

                Spacer()

                if viewModel.categories.contains(where: { $0.amount == 0 }) || showAllCategories {
                    Button {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            showAllCategories.toggle()
                        }
                    } label: {
                        Text(showAllCategories ? "Hide Unused" : "Show All")
                            .font(.subheadline)
                            .foregroundStyle(appAccent)
                    }
                }
            }

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                ForEach(displayed) { category in
                    Button { selectedCategory = category } label: {
                        categoryCard(category)
                    }
                    .buttonStyle(.plain)
                }
            }

            // Full-width Edit Categories button
            Button {
                settingsSheet = SettingsSheet(tab: 2)
            } label: {
                HStack {
                    Image(systemName: "tag")
                        .font(.subheadline)
                    Text("Edit Categories")
                        .font(.subheadline)
                        .fontWeight(.medium)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(Color.primary.opacity(0.06))
                .foregroundStyle(Color.primary)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .buttonStyle(.plain)
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
                    .foregroundStyle(category.amount == 0 ? AnyShapeStyle(.secondary) : AnyShapeStyle(.primary))
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
                        .foregroundStyle(appAccent)
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
    @Published var excludedCategories: [String]?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService()

    func loadData(year: Int? = nil, month: Int? = nil) async {
        isLoading = true
        errorMessage = nil

        let now = Date()
        let cal = Calendar.current
        let targetYear = year ?? cal.component(.year, from: now)
        let targetMonth = month ?? cal.component(.month, from: now)

        do {
            async let budgetFetch = api.fetchBudget(year: targetYear, month: targetMonth)
            async let categoriesFetch = api.fetchCategories()
            async let expensesFetch = api.fetchExpenses(year: targetYear, month: targetMonth)

            let (budget, apiCategories, expenses) = try await (budgetFetch, categoriesFetch, expensesFetch)

            let catMap = Dictionary(uniqueKeysWithValues: apiCategories.map { ($0.category_id, $0) })

            budgetSummary = BudgetSummary(
                totalSpent: budget.total_spending,
                totalBudget: budget.total_cap,
                remaining: budget.total_remaining,
                thisMonth: budget.total_spending,
                percentage: budget.total_percentage
            )

            excludedCategories = budget.excluded_categories

            categories = budget.categories
                .filter { $0.spending > 0 || $0.cap > 0 }
                .sorted { lhs, rhs in
                    if lhs.spending != rhs.spending { return lhs.spending > rhs.spending }
                    return lhs.cap > rhs.cap
                }
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

    func refresh(year: Int? = nil, month: Int? = nil) async {
        await loadData(year: year, month: month)
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
