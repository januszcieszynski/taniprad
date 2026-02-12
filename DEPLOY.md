# 🚀 Deployment na produkcję - Instrukcja

## Aktualizacja aplikacji na serwerze produkcyjnym

### Metoda 1: Automatyczny skrypt (Zalecana)

1. **Zaloguj się na serwer:**
```bash
ssh root@188.166.77.171
```

2. **Przejdź do katalogu aplikacji:**
```bash
cd /opt/taniprad
```

3. **Uruchom skrypt aktualizacji:**
```bash
./deploy-update.sh
```

Skrypt automatycznie:
- ✅ Pobierze najnowsze zmiany z GitHub
- ✅ Pokaże listę zmian do zaciągnięcia
- ✅ Poprosi o potwierdzenie
- ✅ Zatrzyma stare kontenery
- ✅ Zbuduje nowy obraz backendu
- ✅ Uruchomi zaktualizowane kontenery
- ✅ Zaktualizuje frontend
- ✅ Przeładuje nginx
- ✅ Sprawdzi czy wszystko działa

---

### Metoda 2: Ręczna aktualizacja

Jeśli wolisz wykonać kroki ręcznie:

#### 1. Zaloguj się na serwer
```bash
ssh root@188.166.77.171
cd ~/apps/taniprad
# Lub jeśli aplikacja jest w /opt/taniprad:
# cd /opt/taniprad
```

#### 2. Pobierz zmiany z GitHub
```bash
git pull origin main
```

#### 3. Zatrzymaj obecne kontenery
```bash
docker-compose -f docker-compose.droplet-shared.yml down
```

#### 4. Zbuduj nowy obraz
```bash
docker-compose -f docker-compose.droplet-shared.yml build --no-cache backend
```

#### 5. Uruchom zaktualizowane kontenery
```bash
docker-compose -f docker-compose.droplet-shared.yml up -d
```

#### 6. Zaktualizuj frontend
```bash
sudo cp index.html /var/www/taniprad/
sudo chown -R www-data:www-data /var/www/taniprad
```

#### 7. Przeładuj nginx
```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### 8. Sprawdź status
```bash
# Sprawdź kontenery
docker-compose -f docker-compose.droplet-shared.yml ps

# Sprawdź backend
curl http://localhost:8080/api/health

# Sprawdź logi
docker-compose -f docker-compose.droplet-shared.yml logs -f backend
```

---

## Weryfikacja deployment

### 1. Sprawdź backend lokalnie
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

### 2. Sprawdź frontend publicznie
```bash
curl https://prad.januszcieszynski.pl
```

### 3. Test przeglądarką
Otwórz: **https://prad.januszcieszynski.pl**

Spróbuj przesłać fakturę i sprawdź czy:
- ✅ Nie pojawia się błąd "load failed"
- ✅ Przed wysłaniem pliku jest sprawdzane połączenie z backendem
- ✅ Komunikaty błędów są bardziej szczegółowe

---

## Sprawdzanie logów

### Logi backendu (na żywo)
```bash
docker-compose -f docker-compose.droplet.yml logs -f backend
```

### Ostatnie 100 linii logów
```bash
docker-compose -f docker-compose.droplet.yml logs --tail=100 backend
```

### Logi nginx
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## Rollback (powrót do poprzedniej wersji)

Jeśli coś pójdzie nie tak:

### 1. Zobacz ostatnie commity
```bash
git log --oneline -5
```

### 2. Wróć do poprzedniej wersji
```bash
# Zamień <commit-hash> na hash poprzedniego commita
git checkout <commit-hash>
```

### 3. Przebuduj i uruchom
```bash
docker-compose -f docker-compose.droplet.yml down
docker-compose -f docker-compose.droplet.yml build --no-cache
docker-compose -f docker-compose.droplet.yml up -d
```

---

## Rozwiązywanie problemów po deployment

### Problem: Backend nie startuje

**Sprawdź logi:**
```bash
docker-compose -f docker-compose.droplet.yml logs backend
```

**Sprawdź czy obraz został zbudowany:**
```bash
docker images | grep taniprad
```

**Przebuduj z czystym cachem:**
```bash
docker-compose -f docker-compose.droplet.yml build --no-cache backend
docker-compose -f docker-compose.droplet.yml up -d
```

### Problem: Frontend nie ładuje się

**Sprawdź czy plik istnieje:**
```bash
ls -la /var/www/taniprad/index.html
```

**Sprawdź uprawnienia:**
```bash
sudo chown -R www-data:www-data /var/www/taniprad
sudo chmod -R 755 /var/www/taniprad
```

**Sprawdź konfigurację nginx:**
```bash
sudo nginx -t
cat /etc/nginx/sites-enabled/prad.januszcieszynski.pl
```

### Problem: SSL nie działa

**Odnów certyfikat:**
```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Problem: "load failed" nadal występuje

**Sprawdź czy backend odpowiada:**
```bash
curl http://localhost:8080/api/health
```

**Sprawdź logi backendu w czasie rzeczywistym:**
```bash
docker-compose -f docker-compose.droplet.yml logs -f backend
```

**Sprawdź sieć Docker:**
```bash
docker network ls
docker network inspect <network-name>
```

---

## Monitorowanie produkcji

### Sprawdź status wszystkich serwisów
```bash
docker-compose -f docker-compose.droplet.yml ps
sudo systemctl status nginx
```

### Sprawdź użycie zasobów
```bash
docker stats
htop  # jeśli zainstalowane
```

### Sprawdź miejsce na dysku
```bash
df -h
docker system df
```

### Wyczyść stare obrazy (oszczędzaj miejsce)
```bash
docker system prune -a -f
```

---

## Checklist po deployment

- [ ] Backend odpowiada na health check
- [ ] Frontend ładuje się publicznie
- [ ] Możesz przesłać fakturę bez błędu "load failed"
- [ ] Logi backendu nie pokazują błędów
- [ ] Nginx nie ma błędów w konfiguracji
- [ ] SSL działa poprawnie (HTTPS)
- [ ] Wszystkie kontenery są uruchomione

---

## Kontakt w razie problemów

Jeśli deployment nie powiódł się:

1. Zapisz logi:
   ```bash
   docker-compose -f docker-compose.droplet.yml logs > deployment-error.log
   ```

2. Sprawdź status:
   ```bash
   docker-compose -f docker-compose.droplet.yml ps > deployment-status.txt
   ```

3. Zrób rollback do poprzedniej wersji (patrz sekcja "Rollback" powyżej)

---

**Powodzenia z deploymentem! 🚀**
