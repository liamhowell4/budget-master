import Foundation
import CryptoKit
import Security

/// Provides a `URLSession` that validates the server's TLS certificate
/// against a set of known SHA-256 SubjectPublicKeyInfo (SPKI) hashes.
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

    /// SHA-256 hashes of the Subject Public Key Info (SPKI) DER encoding.
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
        guard let chain = SecTrustCopyCertificateChain(serverTrust) as? [SecCertificate] else {
            return (.cancelAuthenticationChallenge, nil)
        }
        for certificate in chain {
            guard let publicKey = SecCertificateCopyKey(certificate),
                  let spkiData = SubjectPublicKeyInfoBuilder.spkiData(for: publicKey) else {
                continue
            }

            let hash = SHA256.hash(data: spkiData)
            let base64Hash = Data(hash).base64EncodedString()

            if pinnedHashes.contains(base64Hash) {
                return (.useCredential, URLCredential(trust: serverTrust))
            }
        }

        // No pin matched — reject the connection.
        return (.cancelAuthenticationChallenge, nil)
    }
}

private enum SubjectPublicKeyInfoBuilder {
    private static let rsaAlgorithmIdentifier = Data([
        0x30, 0x0D,
        0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01, 0x01,
        0x05, 0x00,
    ])

    private static let ecPublicKeyOID = Data([
        0x06, 0x07, 0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x02, 0x01,
    ])

    private static let ecCurveOIDs: [Int: Data] = [
        256: Data([0x06, 0x08, 0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x03, 0x01, 0x07]), // prime256v1
        384: Data([0x06, 0x05, 0x2B, 0x81, 0x04, 0x00, 0x22]), // secp384r1
        521: Data([0x06, 0x05, 0x2B, 0x81, 0x04, 0x00, 0x23]), // secp521r1
    ]

    static func spkiData(for publicKey: SecKey) -> Data? {
        guard let keyData = SecKeyCopyExternalRepresentation(publicKey, nil) as? Data,
              let attributes = SecKeyCopyAttributes(publicKey) as? [CFString: Any],
              let keyType = attributes[kSecAttrKeyType] as? String,
              let keySize = attributes[kSecAttrKeySizeInBits] as? Int else {
            return nil
        }

        let algorithmIdentifier: Data
        switch keyType {
        case String(kSecAttrKeyTypeRSA):
            algorithmIdentifier = rsaAlgorithmIdentifier
        case String(kSecAttrKeyTypeECSECPrimeRandom):
            guard let curveOID = ecCurveOIDs[keySize] else {
                return nil
            }
            algorithmIdentifier = derSequence(ecPublicKeyOID + curveOID)
        default:
            return nil
        }

        return derSequence(algorithmIdentifier + derBitString(keyData))
    }

    private static func derSequence(_ data: Data) -> Data {
        Data([0x30]) + derLength(data.count) + data
    }

    private static func derBitString(_ data: Data) -> Data {
        Data([0x03]) + derLength(data.count + 1) + Data([0x00]) + data
    }

    private static func derLength(_ length: Int) -> Data {
        precondition(length >= 0)
        if length < 0x80 {
            return Data([UInt8(length)])
        }

        var value = length
        var bytes: [UInt8] = []
        while value > 0 {
            bytes.insert(UInt8(value & 0xFF), at: 0)
            value >>= 8
        }
        return Data([0x80 | UInt8(bytes.count)] + bytes)
    }
}

// MARK: - Convenience

extension CertificatePinningDelegate {
    /// Pre-configured delegate for the BudgetMaster production backend.
    ///
    /// Refresh these hashes whenever the production certificate chain rotates.
    /// Keep both the active leaf pin and a stable backup/intermediate pin.
    public static let production = CertificatePinningDelegate(
        host: "expense-tracker-nsz3hblwea-uc.a.run.app",
        hashes: [
            // Leaf certificate pin (retrieved 2026-04-03).
            "ZH9Wl1V/JRgGxBaN245J8J3TslzpssU99cNEBuHqbzM=",
            // Intermediate CA pin to survive routine leaf rotation.
            "YPtHaftLw6/0vnc2BnNKGF54xiCA28WFcccjkA4ypCM=",
        ]
    )
}
