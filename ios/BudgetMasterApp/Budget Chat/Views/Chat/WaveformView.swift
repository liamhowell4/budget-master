import SwiftUI

// MARK: - WaveformView

/// A reusable waveform visualization that renders normalized amplitude samples
/// as vertical rounded bars. Supports a playback-progress split so bars to the
/// left of `progress` are drawn in `activeColor` and the remainder in
/// `inactiveColor` — identical to iMessage's audio message treatment.
struct WaveformView: View {
    /// Raw amplitude samples in the range [0, 1].
    let samples: [Float]

    /// Playback position in [0, 1]. Defaults to 1.0 (all bars active) for
    /// a fully-played or non-playback context.
    var progress: Double = 1.0

    var activeColor: Color = .red
    var inactiveColor: Color = Color(uiColor: .systemGray3).opacity(0.6)
    var maxBars: Int = 40
    var barWidth: CGFloat = 2.5
    var barSpacing: CGFloat = 1.5
    var minBarHeight: CGFloat = 2

    var body: some View {
        GeometryReader { geometry in
            HStack(alignment: .center, spacing: barSpacing) {
                ForEach(Array(downsampledBars.enumerated()), id: \.offset) { index, amplitude in
                    let barProgress = Double(index) / Double(max(downsampledBars.count - 1, 1))
                    RoundedRectangle(cornerRadius: barWidth / 2)
                        .fill(barProgress <= progress ? activeColor : inactiveColor)
                        .frame(
                            width: barWidth,
                            height: max(minBarHeight, CGFloat(amplitude) * geometry.size.height)
                        )
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        }
    }

    // MARK: Private

    /// Down-samples `samples` to at most `maxBars` bars by averaging each chunk.
    private var downsampledBars: [Float] {
        guard !samples.isEmpty else { return [] }
        if samples.count <= maxBars { return samples }

        let chunkSize = samples.count / maxBars
        return stride(from: 0, to: samples.count, by: max(chunkSize, 1))
            .prefix(maxBars)
            .map { start in
                let end = min(start + chunkSize, samples.count)
                let chunk = samples[start..<end]
                return chunk.reduce(0, +) / Float(chunk.count)
            }
    }
}

// MARK: - Preview

#if DEBUG
#Preview {
    let fakeSamples: [Float] = (0..<80).map { i in
        Float.random(in: 0.1...1.0) * abs(sin(Float(i) * 0.3))
    }
    return VStack(spacing: 24) {
        // Full active (recording state)
        WaveformView(samples: fakeSamples, progress: 1.0, activeColor: .red)
            .frame(height: 32)
            .padding(.horizontal)

        // Mid-playback state
        WaveformView(
            samples: fakeSamples,
            progress: 0.45,
            activeColor: .white,
            inactiveColor: .white.opacity(0.35)
        )
        .frame(height: 28)
        .padding(.horizontal)
        .background(Color.blue.clipShape(Capsule()))
        .padding(.horizontal)

        // Empty / idle state
        WaveformView(samples: [], progress: 0)
            .frame(height: 28)
            .padding(.horizontal)
    }
    .padding()
}
#endif
