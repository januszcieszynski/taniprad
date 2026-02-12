# 🚀 Szybki Start - Kalkulator "Tani Prąd"

## Instalacja w 3 krokach

### 1️⃣ Przygotuj klucz API

Pobierz klucz API z [Anthropic Console](https://console.anthropic.com/):

```bash
cp .env.example .env
nano .env  # Wpisz swój klucz ANTHROPIC_API_KEY
```

### 2️⃣ Uruchom aplikację

**Z Dockerem (zalecane):**
```bash
docker-compose up --build
```

**Bez Dockera:**
```bash
make install-local
export ANTHROPIC_API_KEY="sk-ant-..."
make dev-backend &
make dev-frontend
```

### 3️⃣ Otwórz w przeglądarce

```
http://localhost:3000
```

## 📱 Jak używać

1. **Przeciągnij fakturę** (PDF lub JPG) na stronę
2. **Kliknij "Analizuj fakturę"**
3. **Poczekaj 10-30 sekund** (AI analizuje dokument)
4. **Zobacz szczegółowe wyniki** oszczędności

## 🎯 Przykładowe wyniki

Dla typowej faktury za prąd ~610 zł:

```
💰 Oszczędność miesięczna: ~170 zł (28%)
📊 Rachunek: 610 zł → 440 zł

Breakdown:
✓ Filar 1 (VAT 23%→5%):      76 zł
✓ Filar 2 (Certyfikaty):      7 zł  
✓ Filar 3 (Dystrybucja -15%): 45 zł
✓ Filar 4 (Opłaty zerowane):  38 zł
```

## 🆘 Pomoc

**Backend nie startuje?**
```bash
docker-compose logs backend
```

**Frontend nie łączy się z API?**
- Sprawdź czy backend działa: http://localhost:5000/api/health
- Upewnij się że oba kontenery są uruchomione: `docker-compose ps`

**Inne problemy?**
- Zobacz pełną dokumentację w README.md
- Sprawdź sekcję Troubleshooting

## 📚 Więcej

- [README.md](README.md) - Pełna dokumentacja
- [backend/README.md](backend/README.md) - Dokumentacja API
- [Makefile](Makefile) - Wszystkie dostępne komendy
