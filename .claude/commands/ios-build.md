# iOS Build & Test

Xcode projesini build et ve hataları kontrol et.

## Adımlar

1. Xcode projesinin var olduğunu doğrula:
   - `ios/ClipFlow/ClipFlow.xcodeproj` mevcut mu?
   - Değilse kullanıcıya Xcode'da oluşturmasını söyle

2. Build komutunu çalıştır:
   ```bash
   cd ios/ClipFlow
   xcodebuild -project ClipFlow.xcodeproj -scheme ClipFlow -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 15 Pro' build 2>&1
   ```

3. Build hatalarını analiz et:
   - Compile error → ilgili .swift dosyasını oku ve düzelt
   - Linking error → framework eksik mi kontrol et
   - Signing error → automatic signing öner

4. Başarılıysa rapor ver:
   - Build süresi
   - Warning sayısı
   - "Build başarılı, simulator'da test edebilirsin"
