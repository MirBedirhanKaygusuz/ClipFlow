# Xcode Agent — MCP Yapılandırma Rehberi

## Önerilen MCP'ler

Xcode agent'ın "her şeyi yapıp kontrol sağlayabilmesi" için gereken MCP'ler:

### 1. Filesystem MCP (ZORUNLU)
**Ne yapar:** Backend kodunu okur, iOS kodunu yazar, config dosyalarını düzenler
**Neden gerekli:** Agent backend API'yi görmeden doğru iOS kodu yazamaz

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-ai/mcp-filesystem",
        "/Users/mirkaygusuz/Desktop/Kişisel/ClipFlow"
      ]
    }
  }
}
```

**Erişim kapsamı:** Tüm proje dizini (backend + iOS + docs + config)

---

### 2. Fetch/HTTP MCP (ZORUNLU)
**Ne yapar:** Backend API endpoint'lerini test eder
**Neden gerekli:** iOS kodu yazarken API'nin gerçekten çalıştığını doğrulayabilmeli

```json
{
  "mcpServers": {
    "fetch": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-fetch"]
    }
  }
}
```

**Kullanım örnekleri:**
- `GET http://localhost:8000/health` → backend çalışıyor mu?
- `POST http://localhost:8000/api/v1/upload` → upload endpoint test
- `GET http://localhost:8000/api/v1/process/{id}` → status response format kontrol

---

### 3. Git MCP (ÖNERİLEN)
**Ne yapar:** Commit, branch, diff, log
**Neden gerekli:** iOS değişikliklerini commit edebilmeli, backend değişikliklerini görebilmeli

```json
{
  "mcpServers": {
    "git": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-git", "--repository", "/Users/mirkaygusuz/Desktop/Kişisel/ClipFlow"]
    }
  }
}
```

---

### 4. Shell/Terminal MCP (OPSİYONEL)
**Ne yapar:** Xcode build, swift compiler, simctl (simulator kontrol)
**Neden gerekli:** Build hatalarını görebilmeli, simulator'ı yönetebilmeli

```bash
# Yararlı komutlar:
xcodebuild -project ClipFlow.xcodeproj -scheme ClipFlow -sdk iphonesimulator build
xcrun simctl list devices
xcrun simctl boot "iPhone 15 Pro"
swift build  # SPM paketleri için
```

---

## Tam MCP Config (Xcode Agent settings.json)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-ai/mcp-filesystem",
        "/Users/mirkaygusuz/Desktop/Kişisel/ClipFlow"
      ]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-fetch"]
    },
    "git": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-ai/mcp-git",
        "--repository",
        "/Users/mirkaygusuz/Desktop/Kişisel/ClipFlow"
      ]
    }
  }
}
```

## Agent'a Verilecek System Prompt Önerisi

```
Sen ClipFlow iOS uygulamasının baş geliştiricisisin.

CLAUDE.md ve XCODE-AGENT-BRIEFING.md dosyalarını oku — projenin tüm bağlamı orada.

Kuralların:
1. SwiftUI + MVVM + async/await kullan
2. UIKit sadece PHPicker wrapper için
3. Video işleme ASLA iOS'ta yapma
4. URLSession kullan, 3rd party library yok
5. Backend API kontratına uy (api-integration skill)
6. Türkçe UI metinleri
7. Her değişiklikten önce backend kodu oku, API kontratını doğrula

MCP'lerin:
- filesystem: Tüm proje dosyalarını oku/yaz
- fetch: Backend API'yi test et
- git: Değişiklikleri commit et

Skills:
- ios-swiftui: SwiftUI pattern'leri
- api-integration: iOS ↔ Backend kontratı
- xcode-setup: Xcode proje ayarları
```

## MCP Kullanım Senaryoları

| Senaryo | Hangi MCP | Nasıl |
|---------|-----------|-------|
| "Upload endpoint ne döner?" | filesystem | backend/app/api/routes/upload.py oku |
| "API çalışıyor mu?" | fetch | GET http://localhost:8000/health |
| "StatusResponse'a yeni field ekle" | filesystem | job.py + APIModels.swift birlikte güncelle |
| "Son değişiklikleri commit et" | git | git add + commit |
| "Backend'de ne değişmiş?" | git | git log / git diff |
| "Upload test et" | fetch | POST multipart /upload |
