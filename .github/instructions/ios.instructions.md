# iOS Swift Dosyaları İçin Kurallar

Bu kurallar `ios/` klasöründeki tüm Swift dosyaları için geçerlidir.

## Pattern'ler
- Her View bir ViewModel'e bağlı olmalı (@StateObject veya @EnvironmentObject)
- ViewModel'ler @MainActor + ObservableObject
- Service'ler actor (thread-safe)
- Network response'ları Codable struct, keyDecodingStrategy = .convertFromSnakeCase
- Hata mesajları Türkçe

## API Modelleri
Backend snake_case JSON döner. iOS modelleri:
- UploadResponse: fileId (String), sizeMb (Double)
- ProcessResponse: jobId (String), estimatedSeconds (Int)
- StatusResponse: status, progress, step, outputUrl, question, options, stats

## Dosya Organizasyonu
- Yeni View → Views/ klasörüne
- Yeni ViewModel → ViewModels/ klasörüne
- Yeni Service → Services/ klasörüne
- Yeni Model → Models/ klasörüne
