#!/bin/bash
# Kiha Sunucu — Ubuntu/Debian Kurulum Scripti
# Kullanım: bash deploy.sh

set -e  # hata olursa dur

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Kiha Sunucu Kurulumu${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# ── 1. Sistem paketleri ───────────────────────────────────────────────────────
echo -e "${GREEN}[1/5] Sistem paketleri güncelleniyor...${NC}"
sudo apt-get update -q
sudo apt-get install -y -q python3.12 python3.12-venv python3-pip curl git

# ── 2. Ollama kurulumu ────────────────────────────────────────────────────────
echo -e "\n${GREEN}[2/5] Ollama kuruluyor...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "  ${YELLOW}Ollama zaten kurulu, atlanıyor.${NC}"
else
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Ollama servisini başlat
echo -e "  Ollama servisi başlatılıyor..."
sudo systemctl enable ollama 2>/dev/null || true
sudo systemctl start  ollama 2>/dev/null || ollama serve &
sleep 3

# LLaVA vision modeli indir
echo -e "  LLaVA modeli indiriliyor (ilk seferinde ~4GB, bekleyin)..."
ollama pull llava:7b

# ── 3. Python sanal ortamı ────────────────────────────────────────────────────
echo -e "\n${GREEN}[3/5] Python bağımlılıkları yükleniyor...${NC}"
cd server
python3.12 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip -q
pip install -e ".[dev]" -q
# httpx (Ollama iletişimi için — pyproject.toml'da dev'de var, prod'a da ekle)
pip install httpx -q
# YOLOv8 model indir (ilk çalıştırmada otomatik de olur, ama önceden indirelim)
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>/dev/null || true

echo -e "  ${GREEN}✓ Bağımlılıklar kuruldu${NC}"

# ── 4. .env dosyası ───────────────────────────────────────────────────────────
echo -e "\n${GREEN}[4/5] .env dosyası ayarlanıyor...${NC}"
cd ..   # proje kökü
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
# Kiha Sunucu — Ortam Değişkenleri

# Ollama (yerel LLM)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b

# Sunucu
KIHA_SERVER_HOST=0.0.0.0
KIHA_SERVER_PORT=8000
KIHA_DEBUG=false

# Veritabanı (opsiyonel, demo için gerekli değil)
KIHA_DB_HOST=localhost
KIHA_DB_PORT=5432
KIHA_DB_NAME=kiha
KIHA_DB_USER=kiha_user
KIHA_DB_PASSWORD=

# Güvenlik (demo için boş bırakılabilir)
KIHA_JWT_SECRET=change_me_in_production
KIHA_API_SECRET=
EOF
    echo -e "  ${YELLOW}.env oluşturuldu — gerekirse düzenleyin.${NC}"
else
    echo -e "  ${YELLOW}.env zaten mevcut, atlanıyor.${NC}"
fi

# ── 5. Sunucuyu başlat ────────────────────────────────────────────────────────
echo -e "\n${GREEN}[5/5] Sunucu başlatılıyor...${NC}"
cd server
source .venv/bin/activate

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Kurulum tamamlandı!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  API:       http://0.0.0.0:8000"
echo "  Dokümantasyon: http://0.0.0.0:8000/docs"
echo ""
echo "  Demo çalıştırmak için:"
echo "    .venv/bin/python scripts/demo_30s_sorgu.py"
echo ""

python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
