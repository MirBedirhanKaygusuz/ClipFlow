# Xcode Project Setup — ClipFlow iOS

Bu skill, Xcode projesinin sıfırdan kurulumu ve yapılandırması için referans.

## Proje Oluşturma

### Xcode'da
1. File > New > Project > iOS > App
2. **Product Name:** ClipFlow
3. **Team:** Developer hesabı (gerçek cihaz testi için gerekli)
4. **Organization Identifier:** com.clipflow
5. **Bundle Identifier:** com.clipflow.app
6. **Interface:** SwiftUI
7. **Language:** Swift
8. **Storage:** None
9. **Include Tests:** Yes (Unit + UI)
10. **Minimum Deployments:** iOS 17.0

### Proje Konumu
```
ios/ClipFlow/ClipFlow.xcodeproj    → Xcode proje dosyası
ios/ClipFlow/ClipFlow/             → Source dosyalar
```

## Dosya Yapısı (Xcode Groups)

Xcode'da şu group yapısını oluştur:
```
ClipFlow/
├── ClipFlowApp.swift
├── Models/
│   └── APIModels.swift
├── ViewModels/
│   └── MainViewModel.swift
├── Views/
│   ├── HomeView.swift
│   ├── VideoPicker.swift
│   └── PreviewView.swift
├── Services/
│   └── APIService.swift
└── Info.plist
```

## Framework'ler (Import)

Projede kullanılan framework'ler (ek linking gerekmez):
```
SwiftUI       → Tüm UI
PhotosUI      → PHPickerViewController
Photos        → PHPhotoLibrary (Camera Roll kaydetme)
AVKit         → VideoPlayer (preview)
UniformTypeIdentifiers → UTType.movie
```

## Info.plist Ayarları

### Zorunlu İzinler
```xml
<key>NSPhotoLibraryUsageDescription</key>
<string>ClipFlow video seçmek ve kaydetmek için fotoğraf kütüphanenize erişir.</string>
<key>NSPhotoLibraryAddUsageDescription</key>
<string>ClipFlow işlenmiş videoları kamera rulonuza kaydetmek ister.</string>
```

### App Transport Security (Development)
Local HTTP backend'e bağlanmak için:
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

**Production'da** bu kaldırılır, HTTPS kullanılır.

## Build Settings

### Önemli Ayarlar
- **Swift Language Version:** Swift 5.9+
- **iOS Deployment Target:** 17.0
- **Build Active Architecture Only (Debug):** Yes
- **Enable Bitcode:** No (deprecated)

### Signing
- **Automatically manage signing:** Yes
- **Team:** Apple Developer hesabı
- **Provisioning Profile:** Automatic

## Capabilities (V2'de eklenecek)
- Push Notifications (APNs)
- Background Modes: Remote notifications

## Scheme Ayarları

### Debug
- API Base URL: `http://<mac-local-ip>:8000/api/v1`
- Log level: verbose

### Release
- API Base URL: `https://api.clipflow.app/api/v1`
- Log level: error only

### Environment Variables (Scheme > Run > Arguments)
```
API_BASE_URL = http://192.168.1.X:8000/api/v1
```

## Simulator vs Real Device

### Simulator
- PHPicker çalışır ama sınırlı video kütüphanesi
- Camera erişimi yok
- Network: localhost direkt çalışır

### Real Device (Önerilen)
- Full PHPicker erişimi
- Background upload desteği
- Network: Mac'in local IP'sini kullan (aynı WiFi)
- Signing gerekli (Apple Developer hesabı)

## Assets Catalog

### App Icon
- 1024x1024 tek icon yeterli (Xcode otomatik resize eder)

### Colors (opsiyonel, V2)
```
AccentColor  → Ana renk
Background   → Arka plan
```

## Sık Karşılaşılan Sorunlar

### "App Transport Security" hatası
→ NSAllowsLocalNetworking ekle (yukarıda)

### PHPicker URL expire oluyor
→ loadFileRepresentation callback'inde hemen kopyala

### "Unable to find provisioning profile"
→ Signing & Capabilities > Automatically manage signing

### Simulator'da video yok
→ Simulator'a Photos app'ten video ekle: Drag & drop

### "Cannot connect to server"
→ Mac firewall kontrolü, aynı WiFi ağı, doğru IP adresi
```bash
# Mac IP'ni bul:
ifconfig | grep "inet " | grep -v 127.0.0.1
```
