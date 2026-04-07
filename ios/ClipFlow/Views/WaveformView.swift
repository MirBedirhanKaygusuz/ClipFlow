import SwiftUI

/// Renders an audio waveform visualization from normalized sample data.
/// Samples should be floats in the range 0.0 to 1.0.
struct WaveformView: View {
    let samples: [Double]
    var barColor: Color = .blue
    var backgroundColor: Color = .clear
    var barSpacing: CGFloat = 1

    var body: some View {
        GeometryReader { geo in
            let barCount = samples.count
            let totalSpacing = barSpacing * CGFloat(max(barCount - 1, 0))
            let barWidth = max(1, (geo.size.width - totalSpacing) / CGFloat(max(barCount, 1)))

            HStack(alignment: .center, spacing: barSpacing) {
                ForEach(0..<barCount, id: \.self) { i in
                    let height = max(2, geo.size.height * CGFloat(samples[i]))
                    RoundedRectangle(cornerRadius: barWidth / 2)
                        .fill(barColor)
                        .frame(width: barWidth, height: height)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        }
        .background(backgroundColor)
    }
}

/// Async waveform view that loads data from the API.
struct AsyncWaveformView: View {
    let fileId: String
    var samples: Int = 100
    var barColor: Color = .blue

    @State private var waveformData: [Double] = []
    @State private var isLoading = true

    private let api = APIService.shared

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
                    .frame(height: 40)
            } else if waveformData.isEmpty {
                Text("Ses verisi yok")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .frame(height: 40)
            } else {
                WaveformView(samples: waveformData, barColor: barColor)
            }
        }
        .task {
            await loadWaveform()
        }
    }

    private func loadWaveform() async {
        defer { isLoading = false }

        do {
            let url = URL(string: "http://192.168.1.101:8000/api/v1/waveform/\(fileId)?samples=\(samples)")!
            let (data, _) = try await URLSession.shared.data(from: url)

            struct WaveformResponse: Codable {
                let samples: [Double]
            }
            let response = try JSONDecoder().decode(WaveformResponse.self, from: data)
            waveformData = response.samples
        } catch {
            waveformData = []
        }
    }
}
