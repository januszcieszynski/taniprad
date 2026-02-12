# ⚡ Szybka aktualizacja produkcji

## Krok 1: Zaloguj się na droplet

```bash
ssh root@188.166.77.171
```

## Krok 2: Uruchom aktualizację

```bash
cd ~/apps/taniprad && git pull && ./deploy-update.sh
```

> **Uwaga:** Jeśli aplikacja jest w innym katalogu, dostosuj ścieżkę.
> Skrypt automatycznie wykryje lokalizację jeśli jesteś w katalogu aplikacji.

**To wszystko!** 🎉

---

## Co się dzieje?

1. `cd /opt/taniprad` - przejście do katalogu aplikacji
2. `git pull` - pobranie najnowszych zmian z GitHub
3. `./deploy-update.sh` - automatyczny deployment:
   - Zatrzymanie starych kontenerów
   - Zbudowanie nowego obrazu
   - Uruchomienie zaktualizowanych kontenerów
   - Aktualizacja frontendu
   - Przeładowanie nginx
   - Sprawdzenie czy wszystko działa

---

## Alternatywnie: Krok po kroku

Jeśli wolisz mieć kontrolę nad każdym krokiem:

```bash
# 1. Zaloguj się
ssh root@188.166.77.171

# 2. Przejdź do katalogu aplikacji
cd ~/apps/taniprad
# Lub jeśli jest w innym miejscu:
# cd /opt/taniprad

# 3. Pobierz zmiany
git pull origin main

# 4. Zobacz co się zmieniło
git log --oneline -5

# 5. Uruchom deployment
./deploy-update.sh
```

---

## Sprawdź czy działa

Po deployment otwórz w przeglądarce:

**https://prad.januszcieszynski.pl**

Sprawdź czy:
- ✅ Strona się ładuje
- ✅ Możesz przesłać fakturę
- ✅ Nie pojawia się błąd "load failed"

---

## W razie problemów

Zobacz pełną dokumentację: **[DEPLOY.md](DEPLOY.md)**

Lub sprawdź logi:
```bash
docker-compose -f docker-compose.droplet.yml logs -f backend
```

---

**Łączny czas aktualizacji: ~3 minuty** ⏱️
