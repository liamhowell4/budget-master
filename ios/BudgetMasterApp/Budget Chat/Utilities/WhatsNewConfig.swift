import Foundation

struct WhatsNewFeature: Decodable, Identifiable {
    let sfSymbol: String
    let title: String
    let description: String

    var id: String { title }
}

struct WhatsNewData: Decodable, Identifiable {
    let version: String
    let title: String
    let subtitle: String
    let features: [WhatsNewFeature]

    var id: String { version }
}

enum WhatsNewConfig {
    private static let userDefaultsKey = "lastSeenWhatsNewVersion"

    static func loadIfNeeded() -> WhatsNewData? {
        guard let url = Bundle.main.url(forResource: "whats_new", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let whatsNew = try? JSONDecoder().decode(WhatsNewData.self, from: data) else {
            return nil
        }

        let lastSeen = UserDefaults.standard.string(forKey: userDefaultsKey)
        if lastSeen == whatsNew.version {
            return nil
        }

        return whatsNew
    }

    static func markAsSeen(_ data: WhatsNewData) {
        UserDefaults.standard.set(data.version, forKey: userDefaultsKey)
    }
}
