import SwiftUI

struct IconPicker: View {
    @Binding var selectedIcon: String
    let accentColor: Color

    private let icons = [
        "fork.knife", "cup.and.saucer.fill", "cart.fill", "car.fill",
        "fuelpump.fill", "house.fill", "heart.fill", "airplane",
        "laptopcomputer", "building.2.fill", "bolt.fill", "creditcard.fill",
        "headphones", "bag.fill", "dumbbell.fill", "book.fill",
        "wifi", "gift.fill", "gamecontroller.fill", "camera.fill",
        "paintbrush.fill", "wrench.fill", "leaf.fill", "star.fill",
        "music.note", "tv.fill", "bicycle", "tram.fill",
        "stethoscope", "pills.fill", "graduationcap.fill", "theatermasks.fill"
    ]

    private let columns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 6)

    var body: some View {
        LazyVGrid(columns: columns, spacing: 8) {
            ForEach(icons, id: \.self) { icon in
                Button {
                    selectedIcon = icon
                } label: {
                    Image(systemName: icon)
                        .font(.title3)
                        .frame(width: 44, height: 44)
                        .foregroundStyle(
                            selectedIcon == icon ? .white : accentColor
                        )
                        .background(
                            selectedIcon == icon
                                ? accentColor
                                : Color(uiColor: .secondarySystemBackground)
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                }
            }
        }
    }
}
