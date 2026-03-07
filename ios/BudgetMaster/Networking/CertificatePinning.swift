import Foundation
import CryptoKit
import Security

/// Provides a `URLSession` that validates the server's TLS certificate
/// against a set of known SHA-256 public-key hashes (SPKI pinning).
///
/// If the server's leaf-certificate public key does not match any pin,
/// the connection is rejected — protecting against MITM attacks even when
/// a rogue CA issues a fraudulent certificate for the domain.
///
/// **Updating pins:**
/// Run the following to extract the SPKI pin from the production server:
/// ```
/// openssl s_client -connect expense-tracker-nsz3hblwea-uc.a.run.app:443 \
///   -servername expense-tracker-nsz3hblwea-uc.a.run.app </dev/null 2>/dev/null \
///   | openssl x509 -pubkey -noout \
///   | openssl pkey -pubin -outform DER \
///   | openssl dgst -sha256 -binary | base64
/// ```
/// Add the resulting base-64 hash to `pinnedHashes` below.
public final class CertificatePinningDelegate: NSObject, URLSessionDelegate, Sendable {

    /// SHA-256 hashes of the Subject Public Key Info (SPKI) DER encoding
    /// for the production backend's TLS certificate chain.
    ///
    /// Include at least **two** pins: the current leaf and a backup
    /// (e.g. the intermediate CA) so that certificate rotation doesn't
    /// cause an outage.
    private let pinnedHashes: Set<String>
    private let pinnedHost: String

    /// - Parameters:
    ///   - host: The hostname to pin (e.g. `"expense-tracker-nsz3hblwea-uc.a.run.app"`).
    ///   - hashes: Base-64 encoded SHA-256 SPKI hashes to trust.
    public init(host: String, hashes: Set<String>) {
        self.pinnedHost = host
        self.pinnedHashes = hashes
    }

    public func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge
    ) async -> (URLSession.AuthChallengeDisposition, URLCredential?) {

        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              challenge.protectionSpace.host == pinnedHost,
              let serverTrust = challenge.protectionSpace.serverTrust else {
            return (.performDefaultHandling, nil)
        }

        // Evaluate the trust chain using the system root CAs first.
        var error: CFError?
        guard SecTrustEvaluateWithError(serverTrust, &error) else {
            return (.cancelAuthenticationChallenge, nil)
        }

        // Walk the certificate chain and check each public key hash.
        let chainLength = SecTrustGetCertificateCount(serverTrust)
        for index in 0..<chainLength {
            guard let certificate = SecTrustCopyCertificateChain(serverTrust)?[index] as? SecCertificate,
                  let publicKey = SecCertificateCopyKey(certificate),
                  let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, nil) as? Data else {
                continue
            }

            let hash = SHA256.hash(data: publicKeyData)
            let base64Hash = Data(hash).base64EncodedString()

            if pinnedHashes.contains(base64Hash) {
                return (.useCredential, URLCredential(trust: serverTrust))
            }
        }

        // No pin matched — reject the connection.
        return (.cancelAuthenticationChallenge, nil)
    }
}

// MARK: - Convenience

extension CertificatePinningDelegate {
    /// Pre-configured delegate for the BudgetMaster production backend.
    ///
    /// **IMPORTANT:** Replace these placeholder hashes with real SPKI hashes
    /// extracted from the production server certificate using the openssl
    /// command documented above. Until real hashes are added, pinning will
    /// reject all connections in production — this is intentional to force
    /// configuration before shipping.
    public static let production = CertificatePinningDelegate(
        host: "expense-tracker-nsz3hblwea-uc.a.run.app",
        hashes: [
            // TODO: Replace with real SPKI hashes before shipping.
            // Run the openssl command in the doc-comment above to obtain them.
            // Include the leaf cert hash AND at least one intermediate/backup hash.
            "REPLACE_WITH_LEAF_CERT_SPKI_SHA256_BASE64",
            "REPLACE_WITH_BACKUP_CERT_SPKI_SHA256_BASE64",
        ]
    )
}
