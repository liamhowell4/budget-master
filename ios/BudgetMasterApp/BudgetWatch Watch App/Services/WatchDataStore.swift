import Combine
import Foundation
import BudgetMaster

/// Shared data store for the watch app's three tab pages.
///
/// Lives as a `@StateObject` on `MainTabView` so its lifetime — and its fetched data —
/// survive page swipes. The key guarantee: `APIClient.tokenProvider` is set *before*
/// any network request fires, eliminating the race condition that existed when each
/// page view set up auth independently in its own `.task` modifier.
@MainActor
final class WatchDataStore: ObservableObject {

    @Published var budgetStatus: BudgetStatus?
    @Published var expenses: [Expense] = []
    @Published var budgetError: String?
    @Published var expensesError: String?
    @Published var budgetLoading = true
    @Published var expensesLoading = true

    // MARK: - Initial Load

    /// Entry point called once from `MainTabView.task`.
    ///
    /// Sets the real token provider on `APIClient.shared` first, then fans out
    /// to fetch both datasets concurrently with `async let`.
    func load() async {
        // Guarantee auth is wired before either network call starts.
        // Both `WatchDataStore` and `WatchTokenProvider` are @MainActor, so this
        // call is safe and synchronous from the actor's perspective.
        await APIClient.shared.setTokenProvider(WatchTokenProvider.shared)

        // Parallel fetch — both tasks start before either is awaited.
        async let budgetFetch: Void = loadBudget()
        async let expensesFetch: Void = loadExpenses()
        _ = await (budgetFetch, expensesFetch)
    }

    // MARK: - Budget

    func loadBudget() async {
        budgetLoading = true
        budgetError = nil
        do {
            budgetStatus = try await WatchExpenseService.fetchBudget()
        } catch {
            budgetError = error.localizedDescription
        }
        budgetLoading = false
    }

    // MARK: - Expenses

    func loadExpenses() async {
        expensesLoading = true
        expensesError = nil
        do {
            expenses = try await WatchExpenseService.fetchRecentExpenses()
        } catch {
            expensesError = error.localizedDescription
        }
        expensesLoading = false
    }

    // MARK: - Refresh

    /// Refreshes both datasets in parallel — call this after saving a new expense
    /// so all three pages reflect up-to-date data without a full reload.
    func refresh() async {
        async let budgetFetch: Void = loadBudget()
        async let expensesFetch: Void = loadExpenses()
        _ = await (budgetFetch, expensesFetch)
    }
}
