#!/bin/bash
# ===========================================
# ClipFlow — Sunucu İlk Kurulum Scripti
# Hetzner VPS (Ubuntu 22.04+) için
# ===========================================
set -euo pipefail

DOMAIN="${1:?Kullanım: ./setup.sh YOUR_DOMAIN}"
EMAIL="${2:-admin@$DOMAIN}"

echo "=== ClipFlow Sunucu Kurulumu ==="
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

# --- 1. Sistem Güncellemesi ---
echo "[1/7] Sistem güncelleniyor..."
apt-get update && apt-get upgrade -y

# --- 2. Docker Kurulumu ---
echo "[2/7] Docker kuruluyor..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
fi

echo "Docker version: $(docker --version)"

# --- 3. Firewall ---
echo "[3/7] Firewall ayarlanıyor..."
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP (certbot + redirect)
ufw allow 443/tcp  # HTTPS
ufw --force enable
echo "Firewall aktif: SSH(22), HTTP(80), HTTPS(443)"

# --- 4. Proje Dosyaları ---
echo "[4/7] Proje dizini oluşturuluyor..."
PROJECT_DIR="/opt/clipflow"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

if [ ! -d ".git" ]; then
    echo "Projeyi klonla veya dosyaları kopyala: $PROJECT_DIR"
    echo "  git clone https://github.com/mirbedirhankaygusuz/clipflow.git ."
fi

# --- 5. Nginx Konfigürasyonu ---
echo "[5/7] Nginx config ayarlanıyor..."
mkdir -p nginx/ssl
if [ -f "nginx/nginx.conf" ]; then
    sed -i "s/YOUR_DOMAIN/$DOMAIN/g" nginx/nginx.conf
    echo "Domain nginx.conf'a yazıldı: $DOMAIN"
else
    echo "UYARI: nginx/nginx.conf bulunamadı. Manuel oluşturman gerekiyor."
fi

# --- 6. Environment Dosyası ---
echo "[6/7] Environment dosyası kontrol ediliyor..."
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        echo ".env.example → .env kopyalandı. Değerleri düzenle:"
        echo "  nano $PROJECT_DIR/backend/.env"
    else
        echo "UYARI: backend/.env.example bulunamadı."
    fi
else
    echo ".env zaten mevcut."
fi

# --- 7. SSL Sertifikası (Let's Encrypt) ---
echo "[7/7] SSL sertifikası alınıyor..."

# İlk sertifika almak için geçici nginx başlat (sadece HTTP)
# Geçici self-signed cert oluştur (nginx başlayabilsin)
mkdir -p "nginx/ssl/live/$DOMAIN"
if [ ! -f "nginx/ssl/live/$DOMAIN/fullchain.pem" ]; then
    openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
        -keyout "nginx/ssl/live/$DOMAIN/privkey.pem" \
        -out "nginx/ssl/live/$DOMAIN/fullchain.pem" \
        -subj "/CN=$DOMAIN" 2>/dev/null
    echo "Geçici self-signed sertifika oluşturuldu."
fi

# Docker servislerini başlat
docker compose up -d nginx

# Certbot ile gerçek sertifika al
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# Nginx'i yeniden başlat (gerçek sertifika ile)
docker compose restart nginx

# --- Tamamlandı ---
echo ""
echo "=== Kurulum Tamamlandı ==="
echo ""
echo "Sonraki adımlar:"
echo "  1. backend/.env dosyasını düzenle:  nano $PROJECT_DIR/backend/.env"
echo "  2. Tüm servisleri başlat:          docker compose up -d"
echo "  3. Logları kontrol et:             docker compose logs -f"
echo "  4. Health check:                   curl https://$DOMAIN/health"
echo ""
echo "Faydalı komutlar:"
echo "  docker compose logs -f backend    # Backend logları"
echo "  docker compose restart backend    # Backend yeniden başlat"
echo "  docker compose down               # Tüm servisleri durdur"
echo "  docker compose pull && docker compose up -d  # Güncelle"
