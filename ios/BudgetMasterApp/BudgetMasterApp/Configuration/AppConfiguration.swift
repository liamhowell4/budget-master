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
            // Replace with your actual Cloud Run URL
            return "https://your-cloud-run-service.run.app"
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
    
    private init() {
        self.environment = AppEnvironment.current
        self.apiBaseURL = environment.apiBaseURL
        self.enableLogging = environment.enableLogging
        self.enableAnalytics = environment.enableAnalytics
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
