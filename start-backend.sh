#!/bin/bash
# Eğer port 8000 kullanımdaysa önceki process'i durdur
lsof -ti:8000 | xargs kill -9 2>/dev/null

cd "$(dirname "$0")/backend"
PATH="/opt/homebrew/bin:$PATH" .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
