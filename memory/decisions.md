# Architecture Decisions

## AD-001: Backend Framework — FastAPI (not Flask)
- **Karar:** FastAPI kullanacağız
- **Neden:** Async native, Pydantic entegre, otomatik docs, background tasks built-in
- **Alternatif:** Flask (doküman bunu öneriyordu ama FastAPI solo dev için daha iyi)

## AD-002: FFmpeg çağrım yöntemi — subprocess (not ffmpeg-python)
- **Karar:** FFmpeg'i doğrudan subprocess.run() ile çağıracağız
- **Neden:** ffmpeg-python wrapper bug'lı, karmaşık filter_complex'te sorun çıkarıyor
- **Trade-off:** Daha fazla string manipulation ama daha fazla kontrol

## AD-003: V1 Storage — Local disk (not R2)
- **Karar:** V1'de /tmp klasörü, V2'de R2
- **Neden:** Complexity azalt, V1 tek sunucu, scale henüz gerekmez
- **Geçiş planı:** storage.py abstraction layer ile, V2'de sadece implementation değişir

## AD-004: Job Queue — V1 BackgroundTasks, V2 Redis
- **Karar:** V1'de FastAPI BackgroundTasks, V2'de Redis + Celery
- **Neden:** V1'de tek worker yeterli, overhead ekleme
- **Risk:** Concurrent job sınırı → V1'de max 3 simultaneous job
