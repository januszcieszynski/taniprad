# 🔌 Kalkulator "Tani Prąd" - Instrukcja uruchomienia

## Szybki start

### 1. Uruchom aplikację

```bash
./start.sh
```

Skrypt automatycznie:
- ✅ Sprawdzi czy Python3 jest zainstalowany
- ✅ Zainstaluje brakujące zależności (jeśli potrzeba)
- ✅ Uruchomi backend Flask na porcie 8080
- ✅ Uruchomi frontend HTTP server na porcie 8000
- ✅ Sprawdzi czy wszystko działa poprawnie

Po uruchomieniu zobaczysz:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Aplikacja uruchomiona pomyślnie!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 Frontend:  http://localhost:8000
🔌 Backend:   http://localhost:8080
📊 Health:    http://localhost:8080/api/health
```

### 2. Otwórz aplikację w przeglądarce

Przejdź do: **http://localhost:8000**

### 3. Zatrzymaj aplikację

Naciśnij `Ctrl+C` w terminalu **LUB** uruchom:

```bash
./stop.sh
```

## Rozwiązywanie problemów

### Problem: "load failed" przy dodawaniu faktury

**Przyczyna:** Backend nie jest uruchomiony lub nie odpowiada.

**Rozwiązanie:**
1. Zatrzymaj aplikację: `./stop.sh`
2. Uruchom ponownie: `./start.sh`
3. Sprawdź logi w plikach `backend.log` i `frontend.log`

### Problem: Port 8080 lub 8000 jest zajęty

**Rozwiązanie:**
```bash
# Znajdź proces zajmujący port
lsof -i :8080
lsof -i :8000

# Zatrzymaj aplikację
./stop.sh
```

### Problem: Brakujące zależności

**Rozwiązanie:**
```bash
pip3 install -r requirements.txt
```

### Problem: Backend nie parsuje mojej faktury

**Przyczyna:** Parser może nie obsługiwać formatu Twojej faktury.

**Rozwiązanie:**
1. Sprawdź logi w pliku `backend.log`
2. Wyślij przykładową fakturę do wsparcia technicznego

## Logi

Aplikacja zapisuje logi w następujących plikach:

- `backend.log` - logi backendu Flask
- `frontend.log` - logi serwera HTTP

Aby śledzić logi w czasie rzeczywistym:

```bash
# Backend
tail -f backend.log

# Frontend
tail -f frontend.log
```

## Testowanie API

### Sprawdź czy backend działa:

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

### Przetestuj analizę faktury:

```bash
curl -X POST http://localhost:8080/api/analyze-invoice \
  -F "file=@twoja-faktura.pdf"
```

## Struktura projektu

```
taniprad/
├── app.py                 # Backend Flask
├── index.html             # Frontend (interfejs użytkownika)
├── parser_advanced.py     # Parser faktur PDF
├── parser_simple.py       # Parser prosty (fallback)
├── requirements.txt       # Zależności Python
├── start.sh              # ⭐ Skrypt startowy
├── stop.sh               # ⭐ Skrypt zatrzymujący
├── backend.log           # Logi backendu
├── frontend.log          # Logi frontendu
└── URUCHOMIENIE.md       # Ten plik
```

## Wsparcie

Jeśli napotkasz problemy:

1. Sprawdź logi: `cat backend.log`
2. Sprawdź czy porty nie są zajęte: `lsof -i :8080 -i :8000`
3. Upewnij się, że wszystkie zależności są zainstalowane: `pip3 install -r requirements.txt`

---

**Powodzenia! 🚀**
