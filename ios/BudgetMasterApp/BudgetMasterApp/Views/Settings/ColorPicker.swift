import SwiftUI

struct ColorPalettePicker: View {
    @Binding var selectedColor: String

    private let presetColors = [
        "#ef4444", "#f97316", "#eab308", "#22c55e",
        "#14b8a6", "#06b6d4", "#3b82f6", "#6366f1",
        "#8b5cf6", "#a855f7", "#ec4899", "#f43f5e",
        "#a16038", "#64748b"
    ]

    private let columns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 7)

    var body: some View {
        LazyVGrid(columns: columns, spacing: 8) {
            ForEach(presetColors, id: \.self) { color in
                Button {
                    selectedColor = color
                } label: {
                    Circle()
                        .fill(Color(hex: color) ?? .gray)
                        .frame(width: 36, height: 36)
                        .overlay(
                            Circle()
                                .stroke(Color.white, lineWidth: selectedColor == color ? 3 : 0)
                        )
                        .overlay(
                            Circle()
                                .stroke(Color(hex: color) ?? .gray, lineWidth: selectedColor == color ? 1 : 0)
                                .padding(3)
                        )
                }
            }
        }
    }
}
