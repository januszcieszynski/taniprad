# 🚀 Deployment z istniejącym nginx w Dockerze

## Twoja obecna konfiguracja:
- ✅ Docker nginx już działa na portach 80/443 (ksef-nginx)
- ✅ Masz działającą aplikację ksef-auto-invoices
- 📍 IP: 188.166.77.171

## Architektura docelowa:
```
Internet (80/443)
       ↓
   ksef-nginx (Docker)
       ↓
   ├─→ istniejące domeny → ksef-auto-invoices:5001
   └─→ prad.januszcieszynski.pl → taniprad-backend:8080
```

---

## Krok 1: Zainstaluj docker-compose

```bash
# Na dropecie:
sudo apt update
sudo apt install -y docker-compose

# Sprawdź wersję
docker-compose --version
```

---

## Krok 2: Znajdź konfigurację istniejącego nginx

```bash
# Sprawdź gdzie jest docker-compose dla ksef
cd ~
find . -name "docker-compose.yml" -o -name "docker-compose.yaml" 2>/dev/null

# LUB
docker inspect ksef-nginx | grep -A 10 "Mounts"
```

**Powiedz mi gdzie jest plik docker-compose.yml dla ksef-nginx!**
Prawdopodobnie w: `~/ksef-auto-invoices/` lub podobnym katalogu.

---

## Krok 3: Sklonuj repozytorium Tani Prąd

```bash
# Stwórz katalog
mkdir -p ~/apps
cd ~/apps

# Sklonuj repo
git clone https://github.com/januszcieszynski/taniprad.git
cd taniprad
```

---

## Krok 4: Dołącz do istniejącej sieci Docker

Najpierw sprawdź nazwę sieci Docker, której używa ksef-nginx:

```bash
# Sprawdź sieć
docker network ls

# Sprawdź do jakiej sieci podłączony jest ksef-nginx
docker inspect ksef-nginx | grep -A 5 "Networks"
```

Prawdopodobnie używasz sieci `ksef-auto-invoices_default` lub podobnej.

Zaktualizuj `docker-compose.droplet.yml`:

```bash
cd ~/apps/taniprad

# Edytuj docker-compose
nano docker-compose.droplet.yml
```

Zmień ostatnie linie na:

```yaml
networks:
  taniprad-network:
    driver: bridge
  ksef-network:  # Dodaj to
    external: true
    name: ksef-auto-invoices_default  # Wpisz prawdziwą nazwę sieci z poprzedniego kroku
```

I w sekcji `backend` dodaj obie sieci:

```yaml
services:
  backend:
    # ... reszta konfiguracji ...
    networks:
      - taniprad-network
      - ksef-network  # Dodaj to
```

---

## Krok 5: Uruchom backend Tani Prąd

```bash
cd ~/apps/taniprad

# Uruchom backend
docker-compose -f docker-compose.droplet.yml up -d

# Sprawdź czy działa
docker ps | grep taniprad
docker logs taniprad-backend

# Test API
curl http://localhost:8080/api/health
```

---

## Krok 6: Dodaj konfigurację do istniejącego nginx

Teraz musimy dodać konfigurację dla `prad.januszcieszynski.pl` do istniejącego nginx.

### Znajdź konfigurację nginx:

```bash
# Sprawdź gdzie są pliki nginx
docker exec ksef-nginx ls -la /etc/nginx/conf.d/
docker exec ksef-nginx ls -la /etc/nginx/sites-enabled/
```

### Stwórz konfigurację dla prad.januszcieszynski.pl:

```bash
# Stwórz plik konfiguracyjny
cd ~/apps/taniprad
nano nginx-taniprad.conf
```

Wklej (uproszczoną wersję bez SSL - certbot doda później):

```nginx
# HTTP server
server {
    listen 80;
    server_name prad.januszcieszynski.pl;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Frontend
    location / {
        root /usr/share/nginx/html/taniprad;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API
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

### Skopiuj konfigurację do nginx:

```bash
# Sprawdź gdzie nginx montuje konfigurację (volume)
docker inspect ksef-nginx | grep -A 10 "Mounts"
```

Prawdopodobnie będzie coś typu: `/home/clawd/ksef-auto-invoices/nginx/conf.d`

```bash
# Skopiuj konfigurację (użyj właściwej ścieżki)
cp nginx-taniprad.conf /path/to/your/nginx/conf.d/

# Skopiuj frontend
docker exec ksef-nginx mkdir -p /usr/share/nginx/html/taniprad
docker cp index.html ksef-nginx:/usr/share/nginx/html/taniprad/

# Reload nginx
docker exec ksef-nginx nginx -t
docker exec ksef-nginx nginx -s reload
```

---

## Krok 7: Skonfiguruj DNS

W panelu domeny (np. cloudflare, nazwa.pl) ustaw:

```
Type: A
Name: prad
Value: 188.166.77.171
TTL: 3600
```

Sprawdź DNS:
```bash
dig prad.januszcieszynski.pl +short
# Powinno pokazać: 188.166.77.171
```

---

## Krok 8: Dodaj SSL (certbot)

```bash
# Użyj istniejącego kontenera certbot lub uruchom nowy
docker exec ksef-certbot certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d prad.januszcieszynski.pl \
  --email twoj@email.pl \
  --agree-tos \
  --no-eff-email

# Certbot zapisze certyfikaty w /etc/letsencrypt/
```

Zaktualizuj `nginx-taniprad.conf` dodając sekcję HTTPS:

```nginx
# HTTPS server
server {
    listen 443 ssl http2;
    server_name prad.januszcieszynski.pl;

    ssl_certificate /etc/letsencrypt/live/prad.januszcieszynski.pl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/prad.januszcieszynski.pl/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Reszta konfiguracji jak w sekcji HTTP
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
docker exec ksef-nginx nginx -s reload
```

---

## Krok 9: Testuj aplikację

```bash
# Test HTTP
curl http://prad.januszcieszynski.pl

# Test HTTPS
curl https://prad.januszcieszynski.pl

# Test API
curl https://prad.januszcieszynski.pl/api/health
```

Otwórz w przeglądarce: **https://prad.januszcieszynski.pl**

---

## Automatyczne deployments

### Opcja 1: Ręczny deployment

```bash
# Stwórz skrypt deploy
cat > ~/apps/taniprad/deploy.sh << 'EOF'
#!/bin/bash
cd ~/apps/taniprad
git pull origin main
docker-compose -f docker-compose.droplet.yml down
docker-compose -f docker-compose.droplet.yml build --no-cache
docker-compose -f docker-compose.droplet.yml up -d

# Update frontend
docker cp index.html ksef-nginx:/usr/share/nginx/html/taniprad/
docker exec ksef-nginx nginx -s reload

echo "✅ Deployment complete!"
EOF

chmod +x ~/apps/taniprad/deploy.sh
```

Po każdej zmianie w kodzie:
```bash
cd ~/apps/taniprad
./deploy.sh
```

### Opcja 2: Automatyczny deployment przez GitHub Actions

Stwórzę dla Ciebie GitHub Actions workflow, który automatycznie wdroży zmiany na droplet po każdym push.

---

## Troubleshooting

### Backend nie łączy się z nginx:

```bash
# Sprawdź czy backend jest w tej samej sieci co nginx
docker network inspect ksef-auto-invoices_default | grep taniprad-backend

# Jeśli nie ma, dodaj ręcznie:
docker network connect ksef-auto-invoices_default taniprad-backend
```

### Nginx nie widzi backendu:

```bash
# Test z kontenera nginx
docker exec ksef-nginx curl http://taniprad-backend:8080/api/health

# Jeśli nie działa, sprawdź sieci:
docker network ls
docker inspect taniprad-backend
docker inspect ksef-nginx
```

### Certbot nie może uzyskać certyfikatu:

```bash
# Upewnij się że DNS wskazuje na droplet
dig prad.januszcieszynski.pl +short

# Sprawdź czy port 80 jest dostępny
curl -I http://prad.januszcieszynski.pl/.well-known/acme-challenge/test
```

---

## Podsumowanie

Po tych krokach będziesz mieć:
- ✅ Backend Tani Prąd w Docker (port 8080)
- ✅ Frontend serwowany przez istniejący nginx
- ✅ SSL/HTTPS z certbot
- ✅ Wszystko na jednym IP (188.166.77.171)
- ✅ Nie zakłóca istniejącej aplikacji ksef

**Koszt:** $0 (używasz istniejącego dropleta!)

---

## Potrzebujesz pomocy?

1. Znajdź ścieżkę do konfiguracji nginx ksef:
   ```bash
   docker inspect ksef-nginx | grep -A 10 "Mounts"
   ```

2. Znajdź nazwę sieci Docker:
   ```bash
   docker network ls
   docker inspect ksef-nginx | grep -A 5 "Networks"
   ```

Prześlij mi te informacje, a pomogę dopasować konfigurację! 🚀
