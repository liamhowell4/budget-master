import Foundation

/// Environment configuration for the app
enum AppEnvironment {
    case development
    case staging
    case production
    
    static var current: AppEnvironment {
        #if DEBUG
        return .development
        #else
        return .production
        #endif
    }
    
    var name: String {
        switch self {
        case .development: return "Development"
        case .staging: return "Staging"
        case .production: return "Production"
        }
    }
    
    var apiBaseURL: String {
        // Check for environment variable override first
        if let urlString = ProcessInfo.processInfo.environment["API_BASE_URL"] {
            return urlString
        }
        
        switch self {
        case .development:
            return "http://localhost:8000"
        case .staging:
            return "https://staging-api.budgetmaster.com"
        case .production:
            return "https://expense-tracker-nsz3hblwea-uc.a.run.app"
        }
    }
    
    var enableLogging: Bool {
        switch self {
        case .development, .staging:
            return true
        case .production:
            return false
        }
    }
    
    var enableAnalytics: Bool {
        switch self {
        case .production:
            return true
        case .development, .staging:
            return false
        }
    }
}

/// Configuration manager for the app
final class AppConfiguration {
    static let shared = AppConfiguration()

    let environment: AppEnvironment
    let apiBaseURL: String
    let enableLogging: Bool
    let enableAnalytics: Bool

    /// The resolved backend URL used at runtime.
    /// Starts as the production URL so early API calls succeed before the
    /// startup probe completes. Updated by `resolveBaseURL()` in BudgetMasterApp.
    nonisolated(unsafe) private(set) var resolvedBaseURL: String

    private init() {
        self.environment = AppEnvironment.current
        self.apiBaseURL = environment.apiBaseURL
        self.enableLogging = environment.enableLogging
        self.enableAnalytics = environment.enableAnalytics
        self.resolvedBaseURL = AppEnvironment.production.apiBaseURL
    }

    func updateResolvedBaseURL(_ url: String) {
        resolvedBaseURL = url
    }

    /// Resolves the backend URL to use at startup.
    ///
    /// On the simulator (DEBUG builds), probes localhost:8000 first.
    /// If the local server is reachable it returns that URL; otherwise
    /// falls back to the production Cloud Run URL.
    /// On a real device or release builds, always returns production.
    static func resolveBaseURL() async -> URL {
#if DEBUG && targetEnvironment(simulator)
        let localURL = URL(string: "http://localhost:8000")!
        var request = URLRequest(url: localURL.appendingPathComponent("health"),
                                 timeoutInterval: 1.5)
        request.httpMethod = "GET"
        if let (_, response) = try? await URLSession.shared.data(for: request),
           (response as? HTTPURLResponse)?.statusCode == 200 {
            NSLog("✅ [AppConfiguration] Local backend reachable — using http://localhost:8000")
            return localURL
        }
        NSLog("⚠️ [AppConfiguration] Local backend not reachable — falling back to production")
#endif
        return URL(string: AppEnvironment.production.apiBaseURL)!
    }

    /// Print configuration info (useful for debugging)
    func printConfiguration() {
        guard enableLogging else { return }

        print("=== App Configuration ===")
        print("Environment: \(environment.name)")
        print("API Base URL: \(apiBaseURL)")
        print("Logging Enabled: \(enableLogging)")
        print("Analytics Enabled: \(enableAnalytics)")
        print("========================")
    }
}
