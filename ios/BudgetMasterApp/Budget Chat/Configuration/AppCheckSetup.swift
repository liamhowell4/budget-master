import FirebaseCore
import FirebaseAppCheck

/// Configures Firebase App Check to protect backend APIs from abuse.
///
/// App Check uses Apple's DeviceCheck / App Attest to cryptographically verify
/// that requests originate from a genuine, unmodified copy of the app running
/// on a real Apple device. This mitigates the risk of extracted API keys being
/// used outside the app.
///
/// **Required console-side setup:**
/// 1. Enable App Check in the Firebase console for project `budget-master-lh`.
/// 2. Register the iOS app with the App Attest provider.
/// 3. Enforce App Check on Firestore, Storage, and Auth in the Firebase console.
/// 4. Restrict the API key in Google Cloud Console:
///    - Application restrictions → iOS apps → add bundle ID `com.budgetmaster.app`
///    - API restrictions → limit to only the APIs the app actually uses.
enum AppCheckSetup {

    static func configure() {
        #if DEBUG
        // Use the debug provider in simulators / debug builds so that
        // Xcode previews and unit tests still work without App Attest hardware.
        let providerFactory = AppCheckDebugProviderFactory()
        #else
        let providerFactory = AppAttestProviderFactory()
        #endif
        AppCheck.setAppCheckProviderFactory(providerFactory)
    }
}

/// Factory that vends the App Attest provider for production builds.
private final class AppAttestProviderFactory: NSObject, AppCheckProviderFactory {
    func createProvider(with app: FirebaseApp) -> (any AppCheckProvider)? {
        AppAttestProvider(app: app)
    }
}
