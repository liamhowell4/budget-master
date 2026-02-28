import SwiftUI
import Combine

// MARK: - ChipConveyorView
//
// A two-row marquee of tappable suggestion chips shown in the chat empty state.
// Row 1 drifts left; Row 2 drifts right. Both pause while the user holds a chip.
// Tapping any chip fires the provided `onSelect` closure.
//
// Implementation notes:
//   - Each row duplicates its chip array so the content wraps seamlessly when the
//     offset cycles back. The cycle width is measured after the first layout pass
//     via a background GeometryReader on the first copy of each row.
//   - Animation is driven by a shared Combine timer received with `.onReceive`.
//     The timer publisher is stored as @State so it can be cancelled via
//     `.onDisappear`, preventing the timer from leaking after navigation.
//   - `isPaused` is set while a long-press gesture is active, giving the user
//     a moment to read chips before lifting their finger to tap.

struct ChipConveyorView: View {

    // Called when the user taps a chip. The parent is responsible for sending.
    let onSelect: (String) -> Void

    @Environment(\.appAccent) private var appAccent
    @Environment(\.colorScheme) private var colorScheme

    // MARK: Chip content

    private let row1Chips = [
        "Chipotle $14.50 for lunch",
        "How much on food this month?",
        "Groceries $67 at Whole Foods",
        "Delete that last one",
        "Uber home $18",
        "Compare this month to last",
    ]

    private let row2Chips = [
        "What's left in my dining budget?",
        "Amazon order $34.99",
        "Am I on track this month?",
        "Add $1,400 rent every month",
        "Coffee $4.75 this morning",
        "Show my top 5 expenses",
    ]

    // MARK: Animation state

    // `phase` advances every timer tick. Each row derives its pixel offset
    // from phase, so both rows stay in sync without needing separate timers.
    @State private var phase: CGFloat = 0
    @State private var isPaused = false

    // Measured natural widths of one copy of each row's chip strip.
    // Set once after the first layout pass and then read every tick.
    @State private var row1ContentWidth: CGFloat = 0
    @State private var row2ContentWidth: CGFloat = 0

    // Pixels per second for the drift — deliberately slow, ambient feel.
    private let driftSpeed: CGFloat = 28
    // Timer fires at 60 fps.
    private let tickInterval: TimeInterval = 1.0 / 60.0

    // The publisher is created once and retained so we can cancel it on disappear.
    // `autoconnect()` starts immediately; `.onReceive` delivers to the main run loop.
    @State private var timerCancellable: AnyCancellable?

    // MARK: Body

    var body: some View {
        VStack(spacing: 24) {
            headerSection
            conveyorSection
        }
        .frame(maxWidth: .infinity)
        .onDisappear {
            timerCancellable?.cancel()
            timerCancellable = nil
        }
    }

    // MARK: Header

    private var headerSection: some View {
        VStack(spacing: 16) {
            // Icon
            Image(systemName: "message.fill")
                .font(.system(size: 48, weight: .medium))
                .foregroundStyle(appAccent)
                .accessibilityHidden(true)

            // Heading + subtitle
            VStack(spacing: 6) {
                Text("Ask me anything")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundStyle(.primary)

                Text("Log expenses, track budgets, and query your spending, all in plain English.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .lineSpacing(2)
                    .padding(.horizontal, 24)
            }

            // "Try asking" divider row
            HStack(spacing: 10) {
                dividerLine
                Text("Try asking")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(.tertiary)
                    .fixedSize()
                dividerLine
            }
            .padding(.horizontal, 32)
        }
    }

    private var dividerLine: some View {
        Rectangle()
            .fill(Color(.separator))
            .frame(height: 0.5)
    }

    // MARK: Conveyor Section

    private var conveyorSection: some View {
        GeometryReader { proxy in
            let w = proxy.size.width
            VStack(spacing: 10) {
                conveyorRow(chips: row1Chips, measuredWidth: $row1ContentWidth, direction: .left,  containerWidth: w)
                conveyorRow(chips: row2Chips, measuredWidth: $row2ContentWidth, direction: .right, containerWidth: w)
            }
        }
        // 2 rows × 36 + 10 spacing
        .frame(height: 82)
        .clipped()
        .onAppear {
            // Create and store the timer cancellable once.
            timerCancellable = Timer.publish(every: tickInterval, on: .main, in: .common)
                .autoconnect()
                .sink { [self] _ in
                    guard !isPaused else { return }
                    phase += CGFloat(driftSpeed * tickInterval)
                }
        }
    }

    // MARK: Single Row

    private enum ScrollDirection { case left, right }

    @ViewBuilder
    private func conveyorRow(
        chips: [String],
        measuredWidth: Binding<CGFloat>,
        direction: ScrollDirection,
        containerWidth: CGFloat
    ) -> some View {
        let halfWidth = measuredWidth.wrappedValue
        let cyclePhase = halfWidth > 0
            ? phase.truncatingRemainder(dividingBy: halfWidth)
            : 0
        let rawOffset: CGFloat = direction == .left
            ? -cyclePhase
            : -(halfWidth - cyclePhase)

        chipStrip(chips: chips, measuredWidth: measuredWidth)
            .offset(x: rawOffset)
            .frame(width: containerWidth, height: 36, alignment: .leading)
            .clipped()
            .mask(edgeFadeMask)
    }

    // MARK: Chip Strip

    private func chipStrip(chips: [String], measuredWidth: Binding<CGFloat>) -> some View {
        // Double the array so the strip wraps seamlessly.
        let doubled = chips + chips

        return HStack(spacing: 8) {
            ForEach(Array(doubled.enumerated()), id: \.offset) { index, text in
                chipView(text: text)
            }
        }
        // Keep the HStack left-aligned; do not let it expand to fill the row.
        .fixedSize(horizontal: true, vertical: false)
        // Measure the full doubled strip width on first appearance, then halve
        // to get the single-copy cycle width.
        .background(
            GeometryReader { geo in
                Color.clear
                    .onAppear {
                        measuredWidth.wrappedValue = geo.size.width / 2
                    }
            }
        )
    }

    // MARK: Individual Chip

    private func chipView(text: String) -> some View {
        ChipButton(
            text: text,
            appAccent: appAccent,
            colorScheme: colorScheme,
            onTap: { onSelect(text) },
            onHoldChanged: { holding in
                withAnimation(.easeInOut(duration: 0.15)) {
                    isPaused = holding
                }
            }
        )
    }

    // MARK: Edge Fade Masks

    private var edgeFadeMask: some View {
        HStack(spacing: 0) {
            LinearGradient(
                colors: [.black.opacity(0), .black],
                startPoint: .leading,
                endPoint: .trailing
            )
            .frame(width: 44)

            Rectangle().fill(.black)

            LinearGradient(
                colors: [.black, .black.opacity(0)],
                startPoint: .leading,
                endPoint: .trailing
            )
            .frame(width: 44)
        }
    }
}

// MARK: - ChipButton
//
// Isolated chip view so that hold-gesture `@State` is self-contained and does
// not trigger re-renders of the full conveyor on every press change.

private struct ChipButton: View {
    let text: String
    let appAccent: Color
    let colorScheme: ColorScheme
    let onTap: () -> Void
    let onHoldChanged: (Bool) -> Void

    @State private var isHolding = false

    // Chip surface color adapts to color scheme for correct contrast in both modes.
    private var chipBackground: Color {
        colorScheme == .dark
            ? Color(.secondarySystemBackground)
            : Color(.systemBackground)
    }

    private var chipBorder: Color {
        Color(.separator)
    }

    var body: some View {
        Text(text)
            .font(.system(size: 13, weight: .regular))
            .foregroundStyle(.primary)
            .lineLimit(1)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                Capsule()
                    .fill(chipBackground)
                    .overlay(
                        Capsule()
                            .strokeBorder(chipBorder, lineWidth: 0.5)
                    )
            )
            // Subtle press-down feedback.
            .scaleEffect(isHolding ? 0.94 : 1.0)
            .animation(.spring(response: 0.2, dampingFraction: 0.65), value: isHolding)
            .onTapGesture {
                onTap()
            }
            // Long-press: pauses conveyor while held; releases fire onTap.
            .onLongPressGesture(
                minimumDuration: 0.3,
                maximumDistance: 20,
                perform: {
                    onTap()
                },
                onPressingChanged: { pressing in
                    isHolding = pressing
                    onHoldChanged(pressing)
                }
            )
            .accessibilityLabel(text)
            .accessibilityHint("Tap to send this message")
            .accessibilityAddTraits(.isButton)
    }
}

// MARK: - Preview

#Preview {
    VStack {
        Spacer()
        ChipConveyorView { text in
            print("Selected: \(text)")
        }
        Spacer()
    }
    .padding(.vertical, 40)
}
