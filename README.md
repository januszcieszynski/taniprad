# 🔌 Kalkulator "Tani Prąd"

Kompletna aplikacja webowa do obliczania oszczędności na rachunku za energię elektryczną po wejściu w życie ustawy prezydenckiej "Tani prąd".

## 📋 Funkcjonalności

✅ **Upload faktury** - PDF lub zdjęcie (JPG/PNG)  
✅ **Automatyczna ekstrakcja danych** - AI wyciąga wszystkie dane z faktury  
✅ **Kalkulacja oszczędności** według 4 filarów ustawy:
- **Filar 1**: Obniżka VAT z 23% → 5%
- **Filar 2**: Reforma certyfikatów (~80 zł/rok)
- **Filar 3**: Obniżka taryf dystrybucyjnych (~15%)
- **Filar 4**: Zerowanie opłat (mocowa, OZE, kogeneracyjna, przejściowa)

✅ **Responsywny interface** z drag & drop  
✅ **Szczegółowe zestawienie** przed/po  
✅ **Breakdown oszczędności** po filarach

## 📁 Struktura projektu

```
tani-prad/
├── backend/              # Flask API
│   ├── app.py           # Główna aplikacja
│   ├── requirements.txt # Zależności Python
│   ├── Dockerfile       # Docker backend
│   └── .env.example     # Przykładowa konfiguracja
├── frontend/            # Statyczna strona HTML/JS
│   └── index.html       # Główny interface
├── docker-compose.yml   # Orkiestracja Docker
└── README.md           # Ta dokumentacja
```

## 🚀 Szybki start

### ⚡ Najszybsza metoda (lokalne uruchomienie)

```bash
# 1. Uruchom aplikację
./start.sh

# 2. Otwórz w przeglądarce
# Frontend: http://localhost:8000
# Backend:  http://localhost:8080
```

```bash
# Zatrzymaj aplikację
./stop.sh
```

**Gotowe!** 🎉 Aplikacja działa lokalnie bez Dockera.

---

### 📦 Alternatywnie: Docker (deployment produkcyjny)

### Wymagania
- Docker & Docker Compose
- (Opcjonalnie) Klucz API Anthropic

### Instalacja

1. **Sklonuj/rozpakuj projekt**
```bash
cd tani-prad
```

2. **Skonfiguruj klucz API** (opcjonalne)
```bash
cp backend/.env.example backend/.env
# Edytuj backend/.env i wpisz swój klucz API
nano backend/.env
```

3. **Uruchom z Docker Compose**
```bash
docker-compose up --build
```

4. **Otwórz w przeglądarce**
```
http://localhost:3000
```

Gotowe! 🎉

## 🛠️ Instalacja bez Dockera

### Backend

```bash
cd backend

# Zainstaluj zależności systemowe (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-pol poppler-utils

# Zainstaluj pakiety Python
pip install -r requirements.txt

# Ustaw klucz API
export ANTHROPIC_API_KEY="sk-ant-..."

# Uruchom
python app.py
```

Backend będzie dostępny na `http://localhost:5000`

### Frontend

```bash
cd frontend

# Uruchom prosty serwer HTTP (Python)
python -m http.server 3000

# Lub Node.js
npx http-server -p 3000
```

Frontend będzie dostępny na `http://localhost:3000`

**WAŻNE**: Edytuj `frontend/index.html` i zmień `API_URL` na właściwy adres backendu.

## 📡 API Documentation

### POST /api/analyze-invoice

Analizuje fakturę za energię elektryczną.

**Request:**
```bash
curl -X POST http://localhost:5000/api/analyze-invoice \
  -F "file=@faktura.pdf"
```

**Response:**
```json
{
  "before": {
    "pozycje": [...],
    "suma_netto": 496.10,
    "vat_procent": 23,
    "vat_kwota": 114.10,
    "suma_brutto": 610.20
  },
  "after": {
    "pozycje": [...],
    "suma_netto": 420.50,
    "vat_procent": 5,
    "vat_kwota": 21.03,
    "suma_brutto": 441.53
  },
  "savings": {
    "filar1_vat": 75.69,
    "filar2_certyfikaty": 6.67,
    "filar3_dystrybucja": 45.20,
    "filar4_oplaty": 37.89,
    "total": 168.67,
    "percent": 27.6
  },
  "metadata": {
    "numer_faktury": "229250916302",
    "data_faktury": "2025-01-15",
    "okres_rozliczeniowy": "01.12.2024 - 31.12.2024",
    "zuzycie_kwh": 460
  }
}
```

### GET /api/health

Health check endpoint.

```bash
curl http://localhost:5000/api/health
```

## 🌐 Deployment na VPS

### Nginx reverse proxy

```nginx
# /etc/nginx/sites-available/tani-prad

server {
    listen 80;
    server_name tani-prad.example.com;

    # Frontend
    location / {
        root /var/www/tani-prad/frontend;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd service dla backendu

```ini
# /etc/systemd/system/tani-prad.service

[Unit]
Description=Tani Prad API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/tani-prad/backend
Environment="ANTHROPIC_API_KEY=sk-ant-..."
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable tani-prad
sudo systemctl start tani-prad
```

### Docker na VPS

```bash
# Sklonuj projekt
git clone https://github.com/your-repo/tani-prad.git
cd tani-prad

# Skonfiguruj .env
cp backend/.env.example backend/.env
nano backend/.env  # wpisz ANTHROPIC_API_KEY

# Uruchom
docker-compose up -d

# Sprawdź logi
docker-compose logs -f
```

## 🔧 Konfiguracja

### Backend (.env)

```bash
# Klucz API Anthropic (WYMAGANY)
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXX

# Port aplikacji (opcjonalny, domyślnie 5000)
PORT=5000

# Maksymalny rozmiar pliku w MB (opcjonalny, domyślnie 10)
MAX_FILE_SIZE_MB=10
```

### Frontend (index.html)

Zmień adres API w linii ~232:

```javascript
const API_URL = 'http://localhost:5000';  // Zmień na właściwy URL
```

Dla produkcji:
```javascript
const API_URL = 'https://tani-prad.example.com';
```

## 🧪 Testowanie

1. Otwórz http://localhost:3000
2. Przeciągnij fakturę PDF lub JPG na stronę (lub kliknij "Wybierz plik")
3. Kliknij "Analizuj fakturę"
4. Poczekaj ~10-30 sekund (Claude analizuje fakturę)
5. Zobacz szczegółowe wyniki oszczędności

## 📊 Przykładowe wyniki

Dla typowej faktury ~610 zł:
- **Oszczędność**: ~170 zł miesięcznie (~28%)
- **Rocznie**: ~2040 zł zaoszczędzone

Breakdown:
- Filar 1 (VAT): ~76 zł
- Filar 2 (certyfikaty): ~7 zł  
- Filar 3 (dystrybucja): ~45 zł
- Filar 4 (opłaty zerowane): ~38 zł

## 🐛 Troubleshooting

### Backend nie startuje

```bash
# Sprawdź czy Tesseract jest zainstalowany
tesseract --version

# Zainstaluj brakujące zależności
sudo apt-get install -y tesseract-ocr tesseract-ocr-pol poppler-utils

# Sprawdź logi
docker-compose logs backend
```

### CORS errors w przeglądarce

Upewnij się, że:
1. Backend działa na `http://localhost:5000`
2. Frontend używa właściwego `API_URL`
3. Flask CORS jest włączony (domyślnie jest)

### Claude API errors

```bash
# Sprawdź czy klucz API jest ustawiony
echo $ANTHROPIC_API_KEY

# W Docker
docker-compose exec backend env | grep ANTHROPIC
```

### OCR nie działa na zdjęciach

```bash
# Zainstaluj polski język dla Tesseract
sudo apt-get install tesseract-ocr-pol

# Sprawdź dostępne języki
tesseract --list-langs
```

## 📝 Licencja

Proprietary - Janusz Bryzek

## 👤 Autor

Janusz Bryzek - Poseł na Sejm RP

## 🔧 Rozwiązywanie problemów

### Problem: "load failed" przy dodawaniu faktury

**Przyczyna:** Backend nie działa.

**Rozwiązanie:**
```bash
./stop.sh   # Zatrzymaj
./start.sh  # Uruchom ponownie
```

Szczegółowa dokumentacja: **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

### Inne problemy

Zobacz pełną dokumentację rozwiązywania problemów:
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Wszystkie znane problemy i rozwiązania
- **[URUCHOMIENIE.md](URUCHOMIENIE.md)** - Szczegółowa instrukcja uruchomienia

## 🤝 Wsparcie

W razie pytań lub problemów:
- Zobacz dokumentację w plikach `.md`
- Stwórz issue na GitHub
- Skontaktuj się mailowo
