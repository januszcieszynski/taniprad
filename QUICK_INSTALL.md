# ⚡ Szybka instalacja na istniejącym dropecie

**Dla Twojego dropleta:** 188.166.77.171 (z działającym ksef-nginx)

---

## 🎯 Co zrobimy (15 minut):

1. Zainstaluj docker-compose
2. Sklonuj repo
3. Uruchom backend Tani Prąd
4. Dodaj konfigurację do nginx
5. Skonfiguruj SSL
6. Gotowe! 🎉

---

## Krok 1: Zainstaluj docker-compose (2 min)

```bash
sudo apt update
sudo apt install -y docker-compose
docker-compose --version
```

---

## Krok 2: Sklonuj repozytorium (1 min)

```bash
mkdir -p ~/apps
cd ~/apps
git clone https://github.com/januszcieszynski/taniprad.git
cd taniprad
```

---

## Krok 3: Diagnoza sieci Docker (1 min)

```bash
# Uruchom diagnostykę
./diagnose-docker-network.sh
```

**ZAPISZ WYNIK!** Szczególnie:
- Nazwę sieci (np. `ksef-auto-invoices_default`)
- Nazwę kontenera nginx (prawdopodobnie `ksef-nginx`)
- Ścieżkę do konfiguracji nginx

---

## Krok 4: Zaktualizuj konfigurację (2 min)

Edytuj `docker-compose.droplet-shared.yml`:

```bash
nano docker-compose.droplet-shared.yml
```

Zmień ostatnią linię na prawdziwą nazwę sieci z kroku 3:

```yaml
networks:
  # ...
  ksef-network:
    external: true
    name: TUTAJ_WPISZ_NAZWE_SIECI  # np: ksef-auto-invoices_default
```

---

## Krok 5: Uruchom backend (2 min)

```bash
# Zbuduj i uruchom
docker-compose -f docker-compose.droplet-shared.yml up -d

# Sprawdź czy działa
docker ps | grep taniprad
docker logs taniprad-backend

# Test API
curl http://localhost:8080/api/health
# Powinno zwrócić: {"status":"ok"}
```

---

## Krok 6: Znajdź katalog konfiguracji nginx (2 min)

```bash
# Sprawdź gdzie nginx montuje konfigurację
docker inspect ksef-nginx | grep -A 10 "Mounts"
```

Prawdopodobnie zobaczysz coś jak:
```
"Source": "/home/clawd/ksef-auto-invoices/nginx/conf.d"
```

**ZAPISZ TĘ ŚCIEŻKĘ!**

---

## Krok 7: Dodaj konfigurację nginx (3 min)

```bash
# Przejdź do katalogu z konfiguracją nginx (użyj ścieżki z kroku 6)
cd /home/clawd/ksef-auto-invoices/nginx/conf.d

# Skopiuj template
cp ~/apps/taniprad/nginx-multi-domain.conf ./prad.conf

# Edytuj konfigurację
nano prad.conf
```

**Uproszczona wersja dla początku (bez SSL):**

```nginx
server {
    listen 80;
    server_name prad.januszcieszynski.pl;

    location / {
        root /usr/share/nginx/html/taniprad;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://taniprad-backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    client_max_body_size 10M;
}
```

---

## Krok 8: Skopiuj frontend (1 min)

```bash
# Utwórz katalog w nginx
docker exec ksef-nginx mkdir -p /usr/share/nginx/html/taniprad

# Skopiuj index.html
docker cp ~/apps/taniprad/index.html ksef-nginx:/usr/share/nginx/html/taniprad/

# Test i reload nginx
docker exec ksef-nginx nginx -t
docker exec ksef-nginx nginx -s reload
```

---

## Krok 9: Skonfiguruj DNS (2 min)

W panelu domeny (np. cloudflare, nazwa.pl):

```
Type: A
Name: prad
Value: 188.166.77.171
TTL: 3600
```

Sprawdź DNS (z lokalnego komputera):
```bash
dig prad.januszcieszynski.pl +short
# Powinno pokazać: 188.166.77.171
```

**Poczekaj 2-5 minut na propagację DNS!**

---

## Krok 10: Test! (1 min)

```bash
# Test HTTP
curl http://prad.januszcieszynski.pl
curl http://prad.januszcieszynski.pl/api/health

# Otwórz w przeglądarce:
# http://prad.januszcieszynski.pl
```

---

## Krok 11: Dodaj SSL (5 min)

```bash
# Uruchom certbot w istniejącym kontenerze
docker exec ksef-certbot certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d prad.januszcieszynski.pl \
  --email twoj@email.com \
  --agree-tos \
  --no-eff-email

# Zaktualizuj konfigurację nginx (dodaj HTTPS)
nano /home/clawd/ksef-auto-invoices/nginx/conf.d/prad.conf
```

Dodaj sekcję HTTPS:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name prad.januszcieszynski.pl;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name prad.januszcieszynski.pl;

    ssl_certificate /etc/letsencrypt/live/prad.januszcieszynski.pl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/prad.januszcieszynski.pl/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    location / {
        root /usr/share/nginx/html/taniprad;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://taniprad-backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    client_max_body_size 10M;
}
```

```bash
# Reload nginx
docker exec ksef-nginx nginx -t
docker exec ksef-nginx nginx -s reload
```

---

## ✅ Gotowe!

Otwórz w przeglądarce: **https://prad.januszcieszynski.pl**

---

## 🔄 Aktualizacje (po zmianach w kodzie)

Stwórz skrypt:

```bash
cat > ~/apps/taniprad/update.sh << 'EOF'
#!/bin/bash
cd ~/apps/taniprad
git pull origin main
docker-compose -f docker-compose.droplet-shared.yml down
docker-compose -f docker-compose.droplet-shared.yml up -d --build
docker cp index.html ksef-nginx:/usr/share/nginx/html/taniprad/
docker exec ksef-nginx nginx -s reload
echo "✅ Updated!"
EOF

chmod +x ~/apps/taniprad/update.sh
```

Po każdej zmianie w GitHub:
```bash
cd ~/apps/taniprad
./update.sh
```

---

## 📊 Monitoring

```bash
# Logi backend
docker logs -f taniprad-backend

# Logi nginx
docker logs -f ksef-nginx

# Status
docker ps
```

---

## 🐛 Troubleshooting

### Backend nie łączy się z nginx?

```bash
# Sprawdź czy backend jest w sieci nginx
docker network inspect <NAZWA_SIECI> | grep taniprad

# Jeśli nie, dodaj ręcznie:
docker network connect <NAZWA_SIECI> taniprad-backend
docker restart taniprad-backend
```

### Nginx nie widzi backendu?

```bash
# Test z kontenera nginx
docker exec ksef-nginx curl http://taniprad-backend:8080/api/health

# Jeśli zwraca error, sprawdź sieci:
docker network ls
docker inspect taniprad-backend | grep -A 5 Networks
docker inspect ksef-nginx | grep -A 5 Networks
```

### Certbot nie może uzyskać certyfikatu?

```bash
# Sprawdź DNS
dig prad.januszcieszynski.pl +short

# Sprawdź czy port 80 działa
curl -I http://prad.januszcieszynski.pl

# Sprawdź logi certbot
docker logs ksef-certbot
```

---

## 💰 Koszt: $0

Używasz istniejącego dropleta! Żadnych dodatkowych kosztów! 🎉

---

## Potrzebujesz pomocy?

Jeśli coś nie działa, uruchom diagnostykę i prześlij wynik:

```bash
cd ~/apps/taniprad
./diagnose-docker-network.sh > diagnostyka.txt
cat diagnostyka.txt
```
