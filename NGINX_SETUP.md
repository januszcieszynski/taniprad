# 🔧 Konfiguracja Nginx dla Tani Prąd

## Problem

Frontend nie może połączyć się z backendem, ponieważ:
- Frontend ma `API_URL = 'http://localhost:8080'`
- Przeglądarka próbuje połączyć się z localhost **na komputerze użytkownika**, nie na serwerze
- To powoduje błąd "load failed"

## Rozwiązanie

Konfigurujemy nginx jako reverse proxy:
- Frontend: `https://prad.januszcieszynski.pl/` → pliki statyczne
- Backend API: `https://prad.januszcieszynski.pl/api/*` → proxy do kontenera `taniprad-backend:8080`

---

## Krok 1: Sprawdź obecną konfigurację nginx

```bash
# Na droplecie:
docker exec ksef-nginx ls -la /etc/nginx/conf.d/
docker exec ksef-nginx cat /etc/nginx/conf.d/prad.conf
```

**Jeśli plik `prad.conf` już istnieje**, sprawdź czy ma sekcję `location /api/`. Jeśli nie, dodaj ją.

---

## Krok 2: Znajdź katalog konfiguracji nginx (na hoście)

```bash
# Sprawdź gdzie nginx montuje konfigurację
docker inspect ksef-nginx | grep -A 10 '"Mounts"'
```

Prawdopodobnie zobaczysz coś jak:
```
"Source": "/home/clawd/ksef-auto-invoices/nginx/conf.d"
```

To jest katalog na hoście, który jest montowany do kontenera.

---

## Krok 3: Skopiuj konfigurację

### Opcja A: Jeśli plik prad.conf NIE istnieje

```bash
cd ~/apps/taniprad

# Znajdź katalog konfiguracji nginx (zamień ścieżkę na właściwą)
NGINX_CONF_DIR="/home/clawd/ksef-auto-invoices/nginx/conf.d"

# Skopiuj nową konfigurację
cp nginx-prad-config.conf $NGINX_CONF_DIR/prad.conf

# Sprawdź czy skopiowano
ls -la $NGINX_CONF_DIR/prad.conf
```

### Opcja B: Jeśli plik prad.conf już istnieje

Edytuj istniejący plik i dodaj sekcję proxy API:

```bash
NGINX_CONF_DIR="/home/clawd/ksef-auto-invoices/nginx/conf.d"
nano $NGINX_CONF_DIR/prad.conf
```

Dodaj tę sekcję **wewnątrz bloku `server { listen 443 ssl; ... }`**:

```nginx
    # Backend API - proxy to Docker container
    location /api/ {
        proxy_pass http://taniprad-backend:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        client_max_body_size 10M;
    }
```

---

## Krok 4: Sprawdź poprawność konfiguracji

```bash
docker exec ksef-nginx nginx -t
```

Powinno zwrócić:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

---

## Krok 5: Przeładuj nginx

```bash
docker exec ksef-nginx nginx -s reload
```

Lub:

```bash
docker restart ksef-nginx
```

---

## Krok 6: Wdróż zaktualizowany frontend

```bash
cd ~/apps/taniprad
git pull
./deploy-update.sh
```

Skrypt automatycznie:
- Pobierze nowy `index.html` (z poprawionym API_URL)
- Skopiuje do `/var/www/taniprad/`
- Przeładuje nginx

---

## Weryfikacja

### 1. Sprawdź czy backend jest dostępny przez nginx

```bash
curl https://prad.januszcieszynski.pl/api/health
```

Powinno zwrócić:
```json
{"service":"tani-prad-api","status":"ok"}
```

### 2. Sprawdź czy frontend się ładuje

```bash
curl -I https://prad.januszcieszynski.pl
```

### 3. Test w przeglądarce

Otwórz: **https://prad.januszcieszynski.pl**

1. Otwórz DevTools (F12) → zakładka Network
2. Wybierz plik faktury i kliknij "Analizuj fakturę"
3. Sprawdź czy request idzie do `https://prad.januszcieszynski.pl/api/analyze-invoice`
4. Sprawdź czy NIE ma błędu "load failed"

---

## Rozwiązywanie problemów

### Problem: nginx -t pokazuje błąd "unknown directive"

**Przyczyna:** Stara wersja nginx lub błąd składni

**Rozwiązanie:**
```bash
docker exec ksef-nginx nginx -t
# Przeczytaj dokładny komunikat błędu i popraw składnię
```

### Problem: 502 Bad Gateway na /api/

**Przyczyna:** Nginx nie może połączyć się z kontenerem `taniprad-backend`

**Rozwiązanie:**
```bash
# Sprawdź czy kontenery są w tej samej sieci Docker
docker network inspect $(docker inspect ksef-nginx -f '{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}') | grep taniprad

# Jeśli nie widać taniprad-backend, sprawdź docker-compose.droplet-shared.yml
# Upewnij się że backend jest w tej samej sieci co nginx
```

### Problem: 404 na /api/

**Przyczyna:** Niepoprawna konfiguracja proxy_pass

**Rozwiązanie:**
Sprawdź czy `proxy_pass` ma trailing slash:
```nginx
proxy_pass http://taniprad-backend:8080/api/;  # ✓ Poprawne (ze slashem)
```

### Problem: CORS error

**Przyczyna:** Backend nie akceptuje requestów z tej domeny

**Rozwiązanie:**
Backend już ma CORS skonfigurowany (`CORS(app)` w `app.py`), ale jeśli problem nadal występuje, sprawdź logi:
```bash
docker logs taniprad-backend --tail 50
```

---

## Alternatywna metoda (bez edycji plików na hoście)

Jeśli wolisz, możesz skopiować konfigurację bezpośrednio do kontenera:

```bash
# Skopiuj plik do kontenera
docker cp nginx-prad-config.conf ksef-nginx:/etc/nginx/conf.d/prad.conf

# Sprawdź
docker exec ksef-nginx nginx -t

# Przeładuj
docker exec ksef-nginx nginx -s reload
```

**Uwaga:** Ta metoda zadziała, ale konfiguracja zostanie utracona po restarcie kontenera.

---

## Podsumowanie zmian

Po wykonaniu tych kroków:

✅ Frontend używa relative path `/api/` zamiast `http://localhost:8080`
✅ Nginx przekierowuje `/api/*` do kontenera `taniprad-backend:8080`
✅ Wszystko działa przez HTTPS
✅ Brak błędów CORS
✅ Brak błędów "load failed"

---

**Po skonfigurowaniu nginx, uruchom deployment ponownie:**

```bash
cd ~/apps/taniprad
git pull
./deploy-update.sh
```
