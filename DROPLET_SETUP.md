# 🖥️ Deployment na istniejącym DigitalOcean Droplet

## Scenariusz: Wiele domen/aplikacji na tym samym IP

Ta konfiguracja pozwala uruchomić wiele aplikacji na tym samym dropecie używając **nginx jako reverse proxy**.

---

## Krok 0: Diagnoza obecnej konfiguracji

Zaloguj się na droplet przez SSH i wykonaj:

```bash
# Sprawdź czy nginx jest zainstalowany
nginx -v

# Sprawdź obecne serwisy nginx
ls -la /etc/nginx/sites-enabled/

# Sprawdź zajęte porty
sudo netstat -tulpn | grep LISTEN

# Sprawdź czy Docker działa
docker --version
docker ps

# Sprawdź obecne kontenery
docker ps -a
```

**Zapisz wyniki**, żeby wiedzieć jakie porty są zajęte!

---

## Architektura

```
Internet (port 80/443)
         ↓
    Nginx (reverse proxy)
         ↓
    ├─→ domena1.pl → localhost:3000 (istniejąca aplikacja)
    ├─→ domena2.pl → localhost:4000 (inna aplikacja)
    └─→ prad.januszcieszynski.pl → localhost:8080 (Tani Prąd)
```

---

## Krok 1: Przygotuj droplet

### 1.1 Zainstaluj wymagane narzędzia (jeśli jeszcze nie masz)

```bash
# Zaktualizuj system
sudo apt update && sudo apt upgrade -y

# Zainstaluj Docker (jeśli nie masz)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Zainstaluj docker-compose (jeśli nie masz)
sudo apt install -y docker-compose

# Zainstaluj nginx (jeśli nie masz)
sudo apt install -y nginx

# Zainstaluj certbot dla SSL (jeśli nie masz)
sudo apt install -y certbot python3-certbot-nginx
```

### 1.2 Sklonuj repozytorium

```bash
# Utwórz katalog dla aplikacji
sudo mkdir -p /opt/taniprad
sudo chown $USER:$USER /opt/taniprad

# Sklonuj repozytorium
cd /opt
git clone https://github.com/januszcieszynski/taniprad.git
cd taniprad
```

---

## Krok 2: Konfiguracja Nginx (Multi-domain)

### 2.1 Skopiuj konfigurację nginx

```bash
# Skopiuj plik konfiguracyjny
sudo cp nginx-multi-domain.conf /etc/nginx/sites-available/prad.januszcieszynski.pl

# Utwórz katalog dla frontendu
sudo mkdir -p /var/www/taniprad

# Skopiuj pliki frontendu
sudo cp index.html /var/www/taniprad/

# Ustaw właściciela
sudo chown -R www-data:www-data /var/www/taniprad
```

### 2.2 Uzyskaj certyfikat SSL

**WAŻNE:** Najpierw upewnij się, że DNS domeny `prad.januszcieszynski.pl` wskazuje na IP dropleta!

```bash
# Sprawdź DNS (z lokalnego komputera)
dig prad.januszcieszynski.pl +short
# Powinno pokazać IP twojego dropleta

# Tymczasowo włącz tylko HTTP (bez SSL)
# Edytuj plik i zakomentuj sekcję HTTPS:
sudo nano /etc/nginx/sites-available/prad.januszcieszynski.pl
```

Zakomentuj sekcję `server` na porcie 443 (dodaj `#` przed każdą linią), zostaw tylko sekcję na porcie 80.

```bash
# Włącz konfigurację
sudo ln -s /etc/nginx/sites-available/prad.januszcieszynski.pl /etc/nginx/sites-enabled/

# Testuj konfigurację
sudo nginx -t

# Przeładuj nginx
sudo systemctl reload nginx

# Uzyskaj certyfikat SSL
sudo certbot --nginx -d prad.januszcieszynski.pl

# Certbot automatycznie zaktualizuje konfigurację nginx i włączy HTTPS!
```

### 2.3 Przywróć pełną konfigurację

```bash
# Przywróć oryginalną konfigurację (z HTTPS)
sudo cp /opt/taniprad/nginx-multi-domain.conf /etc/nginx/sites-available/prad.januszcieszynski.pl

# Test konfiguracji
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## Krok 3: Uruchom aplikację

### 3.1 Deploy backendu

```bash
cd /opt/taniprad

# Uruchom backend w Docker
docker-compose -f docker-compose.droplet.yml up -d

# Sprawdź czy działa
docker-compose -f docker-compose.droplet.yml ps
docker-compose -f docker-compose.droplet.yml logs -f backend

# Test API
curl http://localhost:8080/api/health
# Powinno zwrócić: {"status": "ok"}
```

### 3.2 Test przez przeglądarkę

Otwórz w przeglądarce:
```
https://prad.januszcieszynski.pl
```

Powinien załadować się kalkulator!

---

## Krok 4: Automatyczne deploymenty z GitHub

### Opcja A: Webhook (Zalecane)

Stwórz prosty webhook endpoint:

```bash
# Zainstaluj webhook handler
cd /opt
git clone https://github.com/adnanh/webhook.git
cd webhook
go build
sudo mv webhook /usr/local/bin/

# Stwórz konfigurację webhook
sudo nano /opt/webhook-config.json
```

Wklej:
```json
[
  {
    "id": "taniprad-deploy",
    "execute-command": "/opt/taniprad/deploy.sh",
    "command-working-directory": "/opt/taniprad",
    "response-message": "Deployment started",
    "trigger-rule": {
      "match": {
        "type": "payload-hash-sha1",
        "secret": "TWOJ_SEKRET",
        "parameter": {
          "source": "header",
          "name": "X-Hub-Signature"
        }
      }
    }
  }
]
```

```bash
# Uruchom webhook jako service
sudo nano /etc/systemd/system/webhook.service
```

Wklej:
```ini
[Unit]
Description=Webhook Handler
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/webhook -hooks /opt/webhook-config.json -port 9000 -verbose
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Włącz service
sudo systemctl daemon-reload
sudo systemctl enable webhook
sudo systemctl start webhook

# Dodaj webhook w GitHub:
# GitHub repo → Settings → Webhooks → Add webhook
# Payload URL: http://TWOJ_IP:9000/hooks/taniprad-deploy
# Content type: application/json
# Secret: TWOJ_SEKRET
# Events: Just the push event
```

### Opcja B: Cron + Git Pull (Prostsze, ale mniej eleganckie)

```bash
# Dodaj do crontaba
crontab -e

# Dodaj linię (sprawdza co 5 minut):
*/5 * * * * cd /opt/taniprad && git fetch origin main && [ $(git rev-parse HEAD) != $(git rev-parse @{u}) ] && /opt/taniprad/deploy.sh >> /var/log/taniprad-deploy.log 2>&1
```

### Opcja C: Ręczny deployment

```bash
# Po każdej zmianie w kodzie, na dropecie wykonaj:
cd /opt/taniprad
./deploy.sh
```

---

## Krok 5: Dobre praktyki

### 5.1 Monitoring

```bash
# Logi backendu
docker-compose -f docker-compose.droplet.yml logs -f backend

# Logi nginx
sudo tail -f /var/log/nginx/taniprad_access.log
sudo tail -f /var/log/nginx/taniprad_error.log

# Status kontenerów
docker ps
```

### 5.2 Backup

```bash
# Backup bazy danych (jeśli będzie)
docker exec taniprad-backend backup-script.sh

# Backup plików
sudo tar -czf /backup/taniprad-$(date +%Y%m%d).tar.gz /opt/taniprad
```

### 5.3 Aktualizacje

```bash
# Aktualizuj regularnie
cd /opt/taniprad
git pull origin main
./deploy.sh
```

---

## Troubleshooting

### Problem: Port 8080 już zajęty

```bash
# Sprawdź co używa portu
sudo netstat -tulpn | grep 8080

# Zmień port w docker-compose.droplet.yml
# Na przykład na 8081:
ports:
  - "127.0.0.1:8081:8080"

# Zaktualizuj nginx-multi-domain.conf:
upstream taniprad_backend {
    server localhost:8081;  # Zmień z 8080 na 8081
}

# Restart
docker-compose -f docker-compose.droplet.yml down
docker-compose -f docker-compose.droplet.yml up -d
sudo systemctl reload nginx
```

### Problem: Nginx pokazuje 502 Bad Gateway

```bash
# Sprawdź czy backend działa
curl http://localhost:8080/api/health

# Sprawdź logi nginx
sudo tail -f /var/log/nginx/taniprad_error.log

# Sprawdź logi backendu
docker-compose -f docker-compose.droplet.yml logs backend

# Sprawdź czy nginx może połączyć się z Dockerem
sudo nginx -t
```

### Problem: SSL nie działa

```bash
# Sprawdź certyfikaty
sudo certbot certificates

# Odnów certyfikat
sudo certbot renew --dry-run

# Sprawdź konfigurację nginx
sudo nginx -t

# Sprawdź czy DNS jest poprawne
dig prad.januszcieszynski.pl +short
```

### Problem: Istniejąca aplikacja przestała działać

```bash
# Sprawdź wszystkie konfiguracje nginx
ls -la /etc/nginx/sites-enabled/

# Sprawdź zajęte porty
sudo netstat -tulpn | grep LISTEN

# Test wszystkich konfiguracji nginx
sudo nginx -t

# Sprawdź logi nginx
sudo tail -f /var/log/nginx/error.log
```

---

## Porty standardowe (dla wielu aplikacji)

| Aplikacja | Port wewnętrzny | Domena |
|-----------|----------------|--------|
| Istniejąca app | 3000 | twoja-domena.pl |
| Tani Prąd | 8080 | prad.januszcieszynski.pl |
| Inna app | 8081 | inna-domena.pl |

Nginx nasłuchuje na portach **80** (HTTP) i **443** (HTTPS) i przekierowuje ruch na podstawie domeny.

---

## Koszty

- **Droplet:** Już masz (bez dodatkowych kosztów)
- **SSL:** Darmowy (Let's Encrypt)
- **Domena:** ~$10-15/rok

**Dodatkowy koszt:** $0/miesiąc (używasz istniejącego dropleta!) 🎉

---

## Checklist

- [ ] Nginx zainstalowany
- [ ] Docker zainstalowany
- [ ] Repozytorium sklonowane do `/opt/taniprad`
- [ ] Nginx konfiguracja skopiowana
- [ ] DNS skonfigurowany (prad.januszcieszynski.pl → IP dropleta)
- [ ] SSL certyfikat uzyskany (certbot)
- [ ] Backend uruchomiony (docker-compose)
- [ ] Frontend skopiowany do `/var/www/taniprad`
- [ ] Nginx przeładowany
- [ ] Aplikacja działa: https://prad.januszcieszynski.pl
- [ ] Automatyczny deployment skonfigurowany (webhook lub cron)

---

## Następne kroki

1. Zaloguj się na droplet przez SSH
2. Wykonaj polecenia z **Kroku 0** (diagnoza)
3. Prześlij mi wyniki, a pomogę dopasować konfigurację
4. Postępuj zgodnie z krokami 1-4

Powodzenia! 🚀
