import Foundation
import Security

/// Securely stores the Firebase auth token in the iOS/watchOS Keychain
/// instead of UserDefaults, preventing plaintext extraction on jailbroken
/// devices or via unencrypted backups.
enum KeychainTokenStore {

    private static let service = "com.budgetmaster.watch"
    private static let tokenAccount = "firebase.token"
    private static let timestampAccount = "firebase.tokenTimestamp"

    // MARK: - Read

    static func token() -> String? {
        readString(account: tokenAccount)
    }

    static func tokenTimestamp() -> TimeInterval? {
        guard let str = readString(account: timestampAccount),
              let ts = TimeInterval(str) else { return nil }
        return ts
    }

    // MARK: - Write

    static func save(token: String, timestamp: TimeInterval) {
        save(string: token, account: tokenAccount)
        save(string: String(timestamp), account: timestampAccount)
    }

    // MARK: - Delete

    static func deleteAll() {
        delete(account: tokenAccount)
        delete(account: timestampAccount)
    }

    // MARK: - Private

    private static func save(string: String, account: String) {
        guard let data = string.data(using: .utf8) else { return }

        // Delete any existing item first
        delete(account: account)

        let query: [String: Any] = [
            kSecClass as String:       kSecClassGenericPassword,
            kSecAttrService as String:  service,
            kSecAttrAccount as String:  account,
            kSecValueData as String:    data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        SecItemAdd(query as CFDictionary, nil)
    }

    private static func readString(account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String:       kSecClassGenericPassword,
            kSecAttrService as String:  service,
            kSecAttrAccount as String:  account,
            kSecReturnData as String:   true,
            kSecMatchLimit as String:   kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let str = String(data: data, encoding: .utf8) else {
            return nil
        }
        return str
    }

    private static func delete(account: String) {
        let query: [String: Any] = [
            kSecClass as String:       kSecClassGenericPassword,
            kSecAttrService as String:  service,
            kSecAttrAccount as String:  account
        ]
        SecItemDelete(query as CFDictionary)
    }
}
