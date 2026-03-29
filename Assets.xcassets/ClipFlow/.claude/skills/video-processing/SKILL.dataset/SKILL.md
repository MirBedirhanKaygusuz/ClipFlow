# Video Processing — FFmpeg + librosa + Whisper

Bu projedeki tüm video işleme görevlerinde bu bilgiyi kullan.

## FFmpeg Temel Kurallar
- subprocess.run() ile çağır, ffmpeg-python KULLANMA
- Her zaman capture_output=True, text=True
- check=True ile hata yakala
- Path'leri shlex.quote() ile escape et

## Sık Kullanılan FFmpeg Komutları

### Sessizlik Tespiti
```bash
ffmpeg -i input.mp4 -af silencedetect=noise=-30dB:d=0.3 -f null -
# stderr'dan parse et: silence_start, silence_end
```

### Video Kırpma (Trim)
```bash
ffmpeg -i input.mp4 -ss 00:00:05 -to 00:00:15 -c:v libx264 -c:a aac output.mp4
# -ss ÖNCE -i'den gelirse seek hızlı (keyframe), SONRA gelirse doğru (frame-accurate)
# Kısa kliplerde -ss'i -i'den SONRA koy (doğruluk önemli)
```

### Birden Fazla Klibi Birleştirme
```bash
# Yöntem 1: concat demuxer (aynı codec)
echo "file 'clip1.mp4'" > list.txt
echo "file 'clip2.mp4'" >> list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4

# Yöntem 2: filter_complex (farklı codec/boyut — re-encode)
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" -c:v libx264 -preset fast -c:a aac output.mp4
```

### 9:16 Dikey Format (Reels/Shorts)
```bash
# Yatay videoyu 9:16'ya çevir (crop center)
ffmpeg -i input.mp4 -vf "crop=ih*9/16:ih" -c:v libx264 -c:a aac output.mp4

# Yatay videoyu 9:16'ya pad (siyah bar ekle)
ffmpeg -i input.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" output.mp4
```

### Geçiş Efektleri (xfade)
```bash
# 2 klip arası 0.5sn crossfade
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=CLIP1_DURATION_MINUS_0.5[outv];[0:a][1:a]acrossfade=d=0.5[outa]" \
  -map "[outv]" -map "[outa]" output.mp4
# offset = clip1 süresi - fade süresi
```

### Video Bilgisi Alma
```bash
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
# duration, width, height, codec, fps
```

## librosa — Ses Analizi

### Beat Detection
```python
import librosa
y, sr = librosa.load(audio_path, sr=22050)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
beat_times = librosa.frames_to_time(beats, sr=sr)
# beat_times = [0.5, 1.0, 1.5, ...] saniye cinsinden
```

### Sessizlik Tespiti (alternatif)
```python
import librosa
intervals = librosa.effects.split(y, top_db=30)
# intervals = [[start_sample, end_sample], ...]
# Zamana çevir: librosa.samples_to_time(intervals, sr=sr)
```

### Tempo Sınıflandırma
```python
# BPM'e göre sınıfla
if tempo < 90: category = "slow"
elif tempo < 130: category = "medium"
else: category = "fast"
```

## Whisper — Transkript

### API Kullanımı
```python
from openai import OpenAI
client = OpenAI()

with open(audio_path, "rb") as f:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        response_format="verbose_json",
        timestamp_granularities=["word"]
    )
# transcript.words = [{"word": "merhaba", "start": 0.5, "end": 0.8}, ...]
```

### Dolgu Sesi Tespiti
```python
FILLER_WORDS_TR = {"mm", "mmm", "ee", "eee", "şey", "yani", "işte", "hani", "aslında"}
FILLER_WORDS_EN = {"um", "uh", "like", "you know", "basically", "actually"}

fillers = [w for w in transcript.words
           if w["word"].strip().lower() in FILLER_WORDS_TR | FILLER_WORDS_EN]
```

## PySceneDetect — Sahne Değişimi
```python
from scenedetect import detect, ContentDetector
scenes = detect("input.mp4", ContentDetector(threshold=30))
# scenes = [(start_timecode, end_timecode), ...]
```

## Highlight Detection Pattern
```python
# Her klip için skor hesapla:
# 1. Hareket skoru: optical flow magnitude ortalaması
# 2. Ses skoru: RMS energy peak'leri
# 3. Yüz skoru: face detection confidence × face size
# Ağırlıklı toplam: 0.4*hareket + 0.3*ses + 0.3*yüz
# En yüksek skorlu segmentleri seç
```

## Performans Notları
- 1 dakika video ≈ 30-60sn işleme (FFmpeg) + 10-20sn (Whisper)
- librosa.load() büyük dosyalarda yavaş → sadece audio extract edip yükle
- FFmpeg -preset fast kullan (ultrafast kalitesiz, slow çok yavaş)
- Geçici dosyalar /tmp'de oluştur, işlem bitince sil
