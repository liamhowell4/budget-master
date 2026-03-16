import SwiftUI

struct WhatsNewView: View {
    let data: WhatsNewData
    let onDismiss: () -> Void

    @Environment(\.appAccent) private var accent

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            Text(data.title)
                .font(.largeTitle.bold())
                .padding(.bottom, 4)

            Text(data.subtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .padding(.bottom, 32)

            VStack(alignment: .leading, spacing: 24) {
                ForEach(data.features) { feature in
                    HStack(alignment: .top, spacing: 16) {
                        Image(systemName: feature.sfSymbol)
                            .font(.title2)
                            .foregroundStyle(accent)
                            .frame(width: 36, alignment: .center)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(feature.title)
                                .font(.headline)
                            Text(feature.description)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
            .padding(.horizontal)

            Spacer()
            Spacer()

            Button {
                onDismiss()
            } label: {
                Text("Continue")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .tint(accent)
            .padding(.horizontal)
            .padding(.bottom, 24)
        }
        .padding(.top, 40)
    }
}
