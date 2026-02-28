import SwiftUI

/// A simplified waveform bar chart for watchOS.
/// Downsamples the incoming samples array to ~40 bars for display.
struct WatchWaveformView: View {

    let samples: [Float]

    private static let targetBars = 40

    private var downsampled: [Float] {
        guard !samples.isEmpty else { return [] }
        let step = max(1, samples.count / Self.targetBars)
        return stride(from: 0, to: samples.count, by: step).map { samples[$0] }
    }

    var body: some View {
        GeometryReader { geometry in
            let bars = downsampled
            let count = max(1, bars.count)
            let spacing: CGFloat = 1
            let barWidth = max(1, (geometry.size.width - spacing * CGFloat(count - 1)) / CGFloat(count))

            HStack(alignment: .center, spacing: spacing) {
                ForEach(Array(bars.enumerated()), id: \.offset) { _, sample in
                    Capsule()
                        .fill(Color.red.opacity(0.85))
                        .frame(
                            width: barWidth,
                            height: max(3, CGFloat(sample) * geometry.size.height)
                        )
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        }
    }
}
