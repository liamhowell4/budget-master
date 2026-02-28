import Foundation
import BudgetMaster

/// Thin service layer used by Watch views.
/// All network calls go through `APIClient.shared` (from the BudgetMaster package).
enum WatchExpenseService {

    // MARK: - Upload Audio

    /// POST /mcp/process_expense with m4a audio data.
    static func uploadAudio(_ audioData: Data) async throws -> ExpenseProcessResponse {
        var multipart = MultipartFormData()
        multipart.addFileField(
            name: "audio",
            fileName: "voice.m4a",
            mimeType: "audio/mp4",
            data: audioData
        )
        let endpoint = APIEndpoint(method: .post, path: "/mcp/process_expense")
        return try await APIClient.shared.upload(endpoint, multipart: multipart)
    }

    // MARK: - Budget

    /// GET /budget for the current month.
    static func fetchBudget() async throws -> BudgetStatus {
        let status = try await BudgetService.getBudgetStatus()
        // Cache percentage for the complication
        let pct = status.totalPercentage / 100.0
        UserDefaults.standard.set(pct, forKey: "watch.budget.percentage")
        return status
    }

    // MARK: - Recent Expenses

    /// GET /expenses for the current month, returning up to the 5 most-recent.
    static func fetchRecentExpenses() async throws -> [Expense] {
        let calendar = Calendar.current
        let now = Date()
        let year  = calendar.component(.year,  from: now)
        let month = calendar.component(.month, from: now)
        let response = try await ExpenseService.getExpenses(year: year, month: month)
        return Array(response.expenses.prefix(5))
    }
}
