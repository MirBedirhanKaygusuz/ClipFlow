# ClipFlow — Claude Code ile Nasıl Kullanılır?

## Bu klasörde ne var?

```
clipflow/
├── CLAUDE.md                          ← Claude Code bunu OTOMATİK okur
├── NASIL-KULLANILIR.md                ← Bu dosya (oku, sil)
│
├── .claude/
│   ├── commands/                      ← /fix, /feature, /review gibi kısayollar
│   │   ├── fix.md                     ← Bug fix workflow
│   │   ├── feature.md                 ← Yeni özellik ekleme
│   │   ├── review.md                  ← Kod review
│   │   ├── test.md                    ← Test yazma
│   │   ├── status.md                  ← Proje durumu
│   │   └── refactor.md               ← Kod iyileştirme
│   │
│   └── skills/                        ← Domain bilgisi (Claude bunları okur)
│       ├── video-processing/SKILL.md  ← FFmpeg, librosa, Whisper bilgisi
│       ├── ios-swiftui/SKILL.md       ← Swift, SwiftUI pattern'leri
│       └── fastapi-backend/SKILL.md   ← FastAPI, Pydantic pattern'leri
│
├── docs/
│   ├── api-spec.md                    ← API endpoint dokümanı
│   └── milestones.md                  ← İlerleme takibi
│
├── memory/
│   ├── decisions.md                   ← Mimari kararlar kaydı
│   └── learnings.md                   ← Bug/hata dersleri (Claude öğrenir)
│
└── backend/                           ← Çalışır Python kodu
    ├── app/main.py                    ← FastAPI uygulaması
    ├── app/config.py                  ← Ayarlar (.env'den okur)
    ├── app/api/routes/                ← Endpoint'ler
    ├── app/services/                  ← İş mantığı (silence_detector, format_converter)
    ├── app/workers/                   ← Video pipeline'ları
    ├── app/models/                    ← Pydantic modeller
    ├── requirements.txt
    └── .env.example                   ← Bunu .env'ye kopyala
```

---

## Adım 1: Kurulum (Bir kere yap)

```bash
# 1. Claude Code kur (yoksa)
npm install -g @anthropic-ai/claude-code

# 2. Bu klasörü istediğin yere kopyala
cp -r clipflow/ ~/projects/clipflow/
cd ~/projects/clipflow/

# 3. Git başlat
git init
git add .
git commit -m "Initial project setup"

# 4. Python ortamını kur
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. .env dosyasını oluştur
cp .env.example .env
# .env'yi editleyip API key'lerini ekle

# 6. FFmpeg'in kurulu olduğundan emin ol
ffmpeg -version
# Yoksa: brew install ffmpeg (Mac) veya apt install ffmpeg (Linux)
```

---

## Adım 2: Claude Code'u Başlat

```bash
cd ~/projects/clipflow
claude
```

Claude Code açıldığında OTOMATIK olarak:
- `CLAUDE.md` dosyasını okur → projeyi bilir
- Tech stack'i, kuralları, aktif milestone'u bilir
- Hangi dosyalara dokunmaması gerektiğini bilir

---

## Adım 3: Günlük Kullanım

### Normal sohbet — direkt yaz:
```
> sessizlik tespitini test et, test_video.mp4 ile
> upload endpoint'ine dosya boyutu validasyonu ekle
> neden bu hata alıyorum: [hata mesajı yapıştır]
```

### Slash commands — kısayollar kullan:
```
> /fix upload endpoint 500 hatası veriyor büyük dosyalarda
> /feature dolgu sesi (eee, mmm) tespiti ekle
> /review son commit'leri review et
> /test silence_detector modülü için test yaz
> /status projenin durumunu göster
> /refactor silence_detector.py'i temizle
```

### Skills otomatik devreye girer:
Claude video işleme sorusu sorduğunda → `video-processing/SKILL.md` bilgisini kullanır
iOS kodu yazarken → `ios-swiftui/SKILL.md` pattern'lerini takip eder
API endpoint yazarken → `fastapi-backend/SKILL.md` standartlarını uygular

---

## Adım 4: Bir Şey Öğrendiğinde Kaydet

Bug buldun, çözdün. Claude'a de ki:
```
> Bu bug'ı memory/learnings.md'ye kaydet
```

Mimari karar aldın:
```
> Bu kararı memory/decisions.md'ye ekle: V1'de Whisper yerine
> local whisper.cpp kullanmaya karar verdik çünkü API maliyeti yüksek
```

Sonraki session'da Claude bu bilgileri bilir.

---

## Adım 5: Backend'i Çalıştır ve Test Et

```bash
cd backend
source .venv/bin/activate

# Server'ı başlat
uvicorn app.main:app --reload --port 8000

# Başka terminal:
# Health check
curl http://localhost:8000/health

# Video yükle
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@test_video.mp4"

# İşleme başlat (upload'dan gelen file_id'yi kullan)
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"clip_ids": ["FILE_ID_BURAYA"], "mode": "talking_reels"}'

# Durumu kontrol et
curl http://localhost:8000/api/v1/process/JOB_ID_BURAYA
```

---

## Dosya Nedir Ne İşe Yarar — Özet

| Dosya | Ne Yapar | Ne Zaman Güncelle |
|-------|----------|-------------------|
| `CLAUDE.md` | Proje bağlamı, Claude her seferinde okur | Milestone değiştiğinde |
| `commands/*.md` | Slash komutları (/fix, /feature vs.) | Yeni workflow eklerken |
| `skills/*.md` | Domain bilgisi (FFmpeg, Swift vs.) | Yeni teknik öğrendiğinde |
| `memory/decisions.md` | Mimari kararlar | Her önemli kararda |
| `memory/learnings.md` | Bug dersleri | Her bug çözümünde |
| `docs/milestones.md` | İlerleme takibi | Task tamamlandığında |
| `docs/api-spec.md` | API dokümanı | Endpoint eklerken |
