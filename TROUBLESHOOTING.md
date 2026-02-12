# 🔧 Rozwiązywanie problemów - Kalkulator "Tani Prąd"

## Problem: "load failed" przy dodawaniu faktury

### Objawy
- Po wybraniu pliku i kliknięciu "Analizuj fakturę" pojawia się komunikat "load failed"
- W konsoli przeglądarki (F12) może pojawić się błąd:
  - `Failed to fetch`
  - `NetworkError`
  - `ERR_CONNECTION_REFUSED`

### Przyczyna
Backend Flask nie jest uruchomiony lub nie odpowiada na porcie 8080.

### Rozwiązanie

#### Krok 1: Zatrzymaj wszystkie procesy
```bash
./stop.sh
```

#### Krok 2: Uruchom aplikację ponownie
```bash
./start.sh
```

#### Krok 3: Sprawdź czy backend działa
```bash
curl http://localhost:8080/api/health
```

Powinno zwrócić:
```json
{
  "service": "tani-prad-api",
  "status": "ok"
}
```

#### Krok 4: Otwórz aplikację
Przejdź do: **http://localhost:8000**

---

## Problem: Backend się zatrzymał

### Jak sprawdzić czy backend działa?

```bash
# Sprawdź czy proces działa
ps aux | grep "python.*app.py"

# Sprawdź czy port 8080 jest zajęty
lsof -i :8080
```

### Jeśli backend nie działa:

```bash
# Uruchom backend
python3 app.py
```

Lub użyj skryptu startowego:
```bash
./start.sh
```

---

## Problem: Port zajęty

### Objawy
```
OSError: [Errno 48] Address already in use
```

### Rozwiązanie

```bash
# Zatrzymaj aplikację
./stop.sh

# Alternatywnie: zabij procesy ręcznie
pkill -f "python.*app.py"
pkill -f "python.*http.server"

# Uruchom ponownie
./start.sh
```

---

## Problem: CORS - Cross-Origin Request Blocked

### Objawy
W konsoli przeglądarki:
```
Access to fetch at 'http://localhost:8080' from origin 'http://localhost:8000' has been blocked by CORS policy
```

### Przyczyna
Frontend (port 8000) próbuje połączyć się z backendem (port 8080), ale CORS nie jest poprawnie skonfigurowany.

### Rozwiązanie
CORS jest już skonfigurowany w `app.py`:
```python
from flask_cors import CORS
CORS(app)
```

Jeśli problem nadal występuje:
1. Upewnij się, że otwierasz aplikację przez `http://localhost:8000`, a nie przez `file://`
2. Sprawdź czy backend działa: `curl http://localhost:8080/api/health`
3. Zrestartuj aplikację: `./stop.sh && ./start.sh`

---

## Problem: Faktura nie jest parsowana

### Objawy
- Błąd: "Nie udało się sparsować faktury PDF"
- Backend zwraca status 500

### Diagnostyka

1. **Sprawdź logi backendu:**
```bash
tail -50 backend.log
```

2. **Przetestuj parser bezpośrednio:**
```bash
python3 parser_advanced.py twoja-faktura.pdf
```

3. **Sprawdź czy plik jest poprawnym PDF:**
```bash
file twoja-faktura.pdf
```

### Możliwe przyczyny:

#### 1. Uszkodzony plik PDF
**Rozwiązanie:** Sprawdź czy plik otwiera się w przeglądarce PDF

#### 2. Faktura w formacie obrazu (zeskanowana)
**Rozwiązanie:** Parser wymaga PDF z warstwą tekstową. Dla obrazów użyj OCR:
- Zapisz jako JPG/PNG
- Backend użyje Tesseract OCR (ale ta funkcja jest w trakcie implementacji)

#### 3. Nieobsługiwany format faktury
**Rozwiązanie:**
- Sprawdź logi: `cat backend.log`
- Parser obsługuje obecnie faktury E.ON i podobne formaty
- Możesz rozszerzyć parser dodając nowe wzorce w `parser_advanced.py`

---

## Problem: Brakujące zależności

### Objawy
```
ModuleNotFoundError: No module named 'flask'
ModuleNotFoundError: No module named 'pdfplumber'
```

### Rozwiązanie

```bash
pip3 install -r requirements.txt
```

Lub zainstaluj ręcznie:
```bash
pip3 install flask flask-cors pdfplumber pillow pytesseract
```

---

## Problem: Frontend nie ładuje się

### Objawy
- Przeglądarka pokazuje "Cannot connect"
- `curl http://localhost:8000` zwraca błąd

### Rozwiązanie

1. **Sprawdź czy serwer HTTP działa:**
```bash
lsof -i :8000
```

2. **Uruchom serwer ręcznie:**
```bash
python3 -m http.server 8000
```

3. **Lub użyj skryptu startowego:**
```bash
./start.sh
```

---

## Debugowanie - krok po kroku

### 1. Sprawdź czy Python3 działa
```bash
python3 --version
```

### 2. Sprawdź zależności
```bash
python3 -c "import flask, flask_cors, pdfplumber, PIL; print('OK')"
```

### 3. Sprawdź czy porty są wolne
```bash
lsof -i :8080 -i :8000
```

### 4. Uruchom backend z debugowaniem
```bash
python3 app.py
```

Obserwuj logi w konsoli - każdy request powinien być widoczny:
```
📨 Otrzymano request do /api/analyze-invoice
   Method: POST
   Content-Type: multipart/form-data
   Files: ['file']
🔍 Parsowanie pliku: abc123.pdf
✅ Faktura sparsowana: 123456
```

### 5. Przetestuj API bezpośrednio
```bash
# Health check
curl http://localhost:8080/api/health

# Upload test
curl -X POST http://localhost:8080/api/analyze-invoice \
  -F "file=@faktura.pdf" \
  -v
```

### 6. Sprawdź konsolę przeglądarki
1. Otwórz http://localhost:8000
2. Naciśnij F12 (DevTools)
3. Przejdź do zakładki "Console"
4. Spróbuj przesłać fakturę
5. Sprawdź komunikaty błędów

---

## Często zadawane pytania

### Dlaczego muszę uruchamiać backend i frontend osobno?

Aplikacja składa się z dwóch części:
- **Backend** (Flask, port 8080) - obsługuje analizę faktur, parsowanie PDF
- **Frontend** (HTTP server, port 8000) - serwuje interfejs HTML

To typowa architektura aplikacji webowych.

### Czy mogę zmienić porty?

Tak! Edytuj:
- Backend port: w `app.py`, linia `app.run(host='0.0.0.0', port=8080)`
- Frontend port: w `start.sh`, zmień `8000` na inny port
- **Ważne:** Zmień również `API_URL` w `index.html` (linia 522)

### Jak wdrożyć aplikację w produkcji?

Zobacz pliki:
- `DEPLOYMENT.md` - ogólny deployment
- `DIGITALOCEAN_SETUP.md` - deployment na DigitalOcean
- `DROPLET_SETUP.md` - szczegółowa konfiguracja droplet

---

## Wsparcie techniczne

Jeśli żadne z powyższych rozwiązań nie pomogło:

1. Zbierz informacje:
   - Zawartość `backend.log`
   - Zawartość `frontend.log`
   - Output z `curl http://localhost:8080/api/health`
   - Wersja Python: `python3 --version`
   - System operacyjny

2. Sprawdź czy to znany problem w dokumentacji

3. Utwórz nowy issue z zebranymi informacjami

---

**Powodzenia! 🚀**
