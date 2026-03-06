# iOS Security Audit — BudgetMaster

**Date:** 2026-03-06
**Scope:** iOS app (`ios/` directory)

---

## 1. Auth Token Stored in UserDefaults (HIGH)

**File:** `ios/BudgetMasterApp/BudgetMasterWatch/Authentication/WatchTokenProvider.swift` (lines 37-46)

Firebase authentication tokens are persisted in `UserDefaults`, which stores data as plaintext plist files on disk. On jailbroken devices or via unencrypted iTunes/Finder backups, these tokens can be read by anyone with file access, granting full impersonation of the user.

**Vulnerable code:**
```swift
UserDefaults.standard.set(token, forKey: tokenKey)
UserDefaults.standard.set(timestamp, forKey: timestampKey)
```

**Recommendation:** Store tokens in the iOS Keychain using `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` to ensure hardware-backed encryption and prevent backup extraction.

---

## 2. Hardcoded Firebase API Key in Bundled Plist (HIGH)

**File:** `ios/BudgetMasterApp/Budget Chat/GoogleService-Info.plist` (lines 9-10)

The Firebase API key, GCM sender ID, project ID, and storage bucket are hardcoded in `GoogleService-Info.plist`, which ships inside the app bundle. These values are trivially extractable from a compiled IPA using tools like `class-dump`, `otool`, or simply unzipping the archive.

**Exposed values:**
- `API_KEY`: `AIzaSyDhjFcg_6JNGEFuD0eHfd8mY3FVR8FoyGk`
- `PROJECT_ID`: `budget-master-lh`
- `STORAGE_BUCKET`: `budget-master-lh.firebasestorage.app`

**Recommendation:**
- Restrict the API key in the Google Cloud Console to specific iOS bundle IDs and APIs.
- Apply Firestore Security Rules and Firebase App Check to prevent unauthorized access even if the key is extracted.

---

## 3. No SSL/TLS Certificate Pinning (MEDIUM-HIGH)

**File:** `ios/BudgetMaster/Networking/APIClient.swift` (line 14)

The app uses a standard `URLSession.shared` without implementing certificate pinning. This makes all HTTPS communication vulnerable to man-in-the-middle attacks via fraudulent or compromised CA certificates. Additionally, the production API endpoint is hardcoded in source, making the backend easily discoverable.

```swift
public init(
    baseURL: URL = URL(string: "https://expense-tracker-nsz3hblwea-uc.a.run.app")!,
    session: URLSession = .shared,
    ...
)
```

**Recommendation:**
- Implement certificate pinning using `TrustKit`, or via a custom `URLSessionDelegate` that validates the server certificate's public key hash.
- Move the production URL to a runtime-resolved configuration rather than hardcoding it.

---

## 4. Sensitive Data Logged to Console (MEDIUM)

**File:** `ios/BudgetMasterApp/Budget Chat/Authentication/AuthenticationManager.swift` (lines 23, 30, 43, 45, 58)

User Firebase UIDs and authentication state transitions are logged using `print()`. These logs persist in the iOS unified logging system and are accessible via Xcode, Console.app, `idevicesyslog`, or directly on jailbroken devices.

```swift
print("🔐 AuthenticationManager: auth state changed — user: \(user?.uid ?? \"nil\")")
```

**Recommendation:**
- Remove or gate all `print()` statements behind `#if DEBUG`.
- Use `os_log` with `.private` sensitivity for any data that must be logged in production.

---

## 5. Unencrypted HTTP in Development Configuration (MEDIUM)

**File:** `ios/BudgetMasterApp/Budget Chat/Configuration/AppConfiguration.swift` (lines 33, 88-104)

The development environment is configured to connect over plaintext HTTP to `http://localhost:8000`. The `resolveBaseURL()` method also sends unauthenticated health-check requests over HTTP. While gated behind `#if DEBUG && targetEnvironment(simulator)`, developers on shared or untrusted networks risk leaking auth tokens and financial data.

```swift
case .development:
    return "http://localhost:8000"
```

**Recommendation:**
- Use HTTPS even in development (via a self-signed cert + local trust).
- Ensure App Transport Security (ATS) exceptions are not present in `Info.plist` for production builds.
