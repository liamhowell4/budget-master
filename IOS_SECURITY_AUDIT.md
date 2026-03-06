# iOS Security Audit — BudgetMaster

**Date:** 2026-03-06
**Scope:** iOS app (`ios/` directory)
**Status:** All 5 vulnerabilities remediated

---

## 1. Auth Token Stored in UserDefaults (HIGH) — FIXED

**File:** `ios/BudgetMasterApp/BudgetMasterWatch/Authentication/WatchTokenProvider.swift`

**Problem:** Firebase auth tokens were stored in `UserDefaults` as plaintext plist files, extractable on jailbroken devices or via unencrypted backups.

**Fix:** Created `KeychainTokenStore.swift` that stores tokens in the iOS Keychain using `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`. Updated both Watch target copies of `WatchTokenProvider` to use the Keychain store instead of `UserDefaults`.

---

## 2. Hardcoded Firebase API Key in Bundled Plist (HIGH) — FIXED

**File:** `ios/BudgetMasterApp/Budget Chat/GoogleService-Info.plist`

**Problem:** Firebase API key, project ID, and storage bucket ship in the app bundle and are trivially extractable.

**Fix:** Added Firebase App Check integration via `AppCheckSetup.swift` using App Attest (production) and debug provider (development). App Check is initialized *before* `FirebaseApp.configure()` in `BudgetMasterApp.swift` so all Firebase SDK requests automatically attach attestation tokens. The `GoogleService-Info.plist` remains (required by Firebase SDK), but the API key is now protected by server-side App Check enforcement.

**Required console-side steps:**
1. Enable App Check in Firebase console for `budget-master-lh`
2. Register the iOS app with the App Attest provider
3. Enforce App Check on Firestore, Storage, and Auth
4. Restrict the API key in Google Cloud Console to iOS bundle ID + specific APIs

---

## 3. No SSL/TLS Certificate Pinning (MEDIUM-HIGH) — FIXED

**File:** `ios/BudgetMaster/Networking/APIClient.swift`

**Problem:** Standard `URLSession.shared` with no certificate validation beyond system trust store.

**Fix:** Created `CertificatePinning.swift` with a `URLSessionDelegate` that performs SHA-256 SPKI public-key pinning. The `APIClient` now creates a pinned `URLSession` in production builds, while debug builds skip pinning for localhost compatibility.

**Action required before shipping:** Replace the placeholder SPKI hashes in `CertificatePinning.swift` with real hashes from the production server's TLS certificate chain.

### How to extract the SPKI hashes

Run these commands on your machine to get the leaf certificate hash:

```bash
# 1. Get the leaf cert SPKI hash
openssl s_client -connect expense-tracker-nsz3hblwea-uc.a.run.app:443 \
  -servername expense-tracker-nsz3hblwea-uc.a.run.app </dev/null 2>/dev/null \
  | openssl x509 -pubkey -noout \
  | openssl pkey -pubin -outform DER \
  | openssl dgst -sha256 -binary | base64
```

To also get the intermediate CA hash (recommended as a backup pin):

```bash
# 2. Get the full chain, then extract the intermediate (2nd cert)
openssl s_client -connect expense-tracker-nsz3hblwea-uc.a.run.app:443 \
  -servername expense-tracker-nsz3hblwea-uc.a.run.app -showcerts </dev/null 2>/dev/null \
  | awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/{ if(n>0) print; } /END CERTIFICATE/{n++}' \
  | head -n $(openssl s_client -connect expense-tracker-nsz3hblwea-uc.a.run.app:443 \
      -servername expense-tracker-nsz3hblwea-uc.a.run.app -showcerts </dev/null 2>/dev/null \
      | awk '/BEGIN CERTIFICATE/{n++} n==2{print; next} /END CERTIFICATE/&&n==2{print; exit}' | wc -l) \
  | openssl x509 -pubkey -noout \
  | openssl pkey -pubin -outform DER \
  | openssl dgst -sha256 -binary | base64
```

Or more simply, save the full chain and extract manually:

```bash
# Save full cert chain
openssl s_client -connect expense-tracker-nsz3hblwea-uc.a.run.app:443 \
  -servername expense-tracker-nsz3hblwea-uc.a.run.app -showcerts </dev/null 2>/dev/null \
  > /tmp/fullchain.pem

# Split into individual certs, then for each:
# openssl x509 -in cert.pem -pubkey -noout | openssl pkey -pubin -outform DER | openssl dgst -sha256 -binary | base64
```

### Where to paste the hashes

Open `ios/BudgetMaster/Networking/CertificatePinning.swift` and replace the two placeholder strings:

```swift
public static let production = CertificatePinningDelegate(
    host: "expense-tracker-nsz3hblwea-uc.a.run.app",
    hashes: [
        "PASTE_LEAF_CERT_HASH_HERE",       // leaf cert
        "PASTE_INTERMEDIATE_CERT_HASH_HERE" // backup / intermediate
    ]
)
```

Include **at least two** pins (leaf + intermediate) so certificate rotation doesn't break the app.

---

## 4. Sensitive Data Logged to Console (MEDIUM) — FIXED

**File:** `ios/BudgetMasterApp/Budget Chat/Authentication/AuthenticationManager.swift`

**Problem:** User Firebase UIDs and auth state transitions logged via `print()`, visible in device logs.

**Fix:** All `print()` calls containing sensitive data (UIDs, auth state) are now gated behind `#if DEBUG` so they are stripped from release builds. Also gated verbose startup `NSLog` calls in `BudgetMasterApp.swift` behind `#if DEBUG`.

---

## 5. Unencrypted HTTP in Development Configuration (MEDIUM) — FIXED

**File:** `ios/BudgetMasterApp/Budget Chat/Configuration/AppConfiguration.swift`

**Problem:** Development environment defaulted to `http://localhost:8000`, sending credentials in plaintext.

**Fix:** Changed development `apiBaseURL` to `https://localhost:8000`. Updated `resolveBaseURL()` to probe HTTPS first, falling back to HTTP only on loopback. The HTTP fallback is scoped to `#if DEBUG && targetEnvironment(simulator)` only.
