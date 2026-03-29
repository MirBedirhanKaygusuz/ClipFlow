# API Endpoint Test

Backend API endpoint'lerini test et ve sonuçları raporla.

## Adımlar

1. Backend'in çalıştığını kontrol et:
   ```bash
   curl -s http://localhost:8000/health
   ```
   Çalışmıyorsa: "Backend çalışmıyor. Başlatmak için: `uvicorn app.main:app --reload`"

2. İstenen endpoint'i test et (argüman yoksa hepsini test et):

   ### Health Check
   ```bash
   curl -s http://localhost:8000/health | python -m json.tool
   ```

   ### Upload Test
   ```bash
   # Test video oluştur (1sn)
   ffmpeg -f lavfi -i testsrc=duration=1:size=1080x1920 -f lavfi -i sine=frequency=440:duration=1 -c:v libx264 -c:a aac -shortest /tmp/test_clipflow.mp4 -y 2>/dev/null
   # Upload
   curl -s -X POST http://localhost:8000/api/v1/upload -F "file=@/tmp/test_clipflow.mp4" | python -m json.tool
   ```

   ### Process Test
   ```bash
   # file_id'yi upload'dan al, sonra:
   curl -s -X POST http://localhost:8000/api/v1/process \
     -H "Content-Type: application/json" \
     -d '{"clip_ids": ["FILE_ID"], "mode": "talking_reels"}' | python -m json.tool
   ```

   ### Status Test
   ```bash
   curl -s http://localhost:8000/api/v1/process/JOB_ID | python -m json.tool
   ```

3. Sonuçları raporla:
   - Her endpoint: OK / FAIL
   - Response format doğru mu?
   - iOS tarafında beklenen struct'larla uyumlu mu?
