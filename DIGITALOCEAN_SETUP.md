# 🚀 Deployment na DigitalOcean - prad.januszcieszynski.pl

## Wymagania wstępne
- ✅ Konto DigitalOcean
- ✅ Repozytorium GitHub (połączone z DigitalOcean)
- ✅ Domena prad.januszcieszynski.pl skonfigurowana w DNS

---

## Opcja 1: DigitalOcean App Platform (Zalecane - Najprostsze)

### Krok 1: Przygotowanie repozytorium GitHub

```bash
# 1. Stwórz nowe repozytorium na GitHub (np. taniprad)
# 2. Dodaj remote i wypchnij kod:
git remote add origin https://github.com/TWOJ_USERNAME/taniprad.git
git add .
git commit -m "Initial commit - Tani Prąd calculator"
git branch -M main
git push -u origin main
```

### Krok 2: Połącz DigitalOcean z GitHub

1. Przejdź do DigitalOcean Dashboard
2. **Settings** → **Applications** → **GitHub**
3. Kliknij **Install GitHub App** i autoryzuj dostęp do repozytorium

### Krok 3: Utwórz aplikację w App Platform

#### Opcja A: Przez Web Interface

1. W DigitalOcean Dashboard kliknij **Create** → **Apps**
2. Wybierz **GitHub** jako źródło
3. Wybierz repozytorium `taniprad` i branch `main`
4. DigitalOcean automatycznie wykryje Dockerfile

**Konfiguracja:**
- **Service Name:** backend
- **HTTP Port:** 8080
- **Run Command:** (zostaw auto-detect)
- **Instance Size:** Basic (1 vCPU, 512 MB RAM) - $5/miesiąc
- **Region:** Frankfurt (fra1)

5. Dodaj Static Site dla frontendu:
   - **Source Directory:** `/`
   - **Output Directory:** `/`
   - **Index Document:** `index.html`

6. Dodaj domenę:
   - **Domain:** `prad.januszcieszynski.pl`

7. Kliknij **Create Resources**

#### Opcja B: Przez CLI (doctl)

```bash
# Zainstaluj doctl
brew install doctl  # macOS
# lub pobierz z https://docs.digitalocean.com/reference/doctl/how-to/install/

# Autoryzacja
doctl auth init

# Deploy aplikacji
doctl apps create --spec .do/app.yaml

# Monitorowanie
doctl apps list
doctl apps logs <APP_ID> --type run
```

### Krok 4: Konfiguracja DNS

W panelu domeny (np. nazwa.pl, cloudflare):

```
Type    Name    Value                              TTL
A       prad    <IP_Z_DIGITALOCEAN_APP>            3600
CNAME   www     prad.januszcieszynski.pl           3600
```

DigitalOcean App Platform automatycznie zarządza SSL (Let's Encrypt).

### Krok 5: Automatyczne deployments

App Platform automatycznie wdraża zmiany z GitHub:
```bash
git add .
git commit -m "Update feature"
git push origin main
# DigitalOcean automatycznie zbuduje i wdroży nową wersję
```

**Koszt:** ~$5-12/miesiąc (Basic plan)

---

## Opcja 2: DigitalOcean Droplet + Docker (Więcej kontroli)

### Krok 1: Utwórz Droplet

1. **Create** → **Droplets**
2. **Distribution:** Ubuntu 22.04 LTS
3. **Plan:** Basic Shared CPU - $6/miesiąc (1 GB RAM, 1 vCPU)
4. **Region:** Frankfurt
5. Dodaj SSH key lub użyj hasła

### Krok 2: Zainstaluj Docker na Droplet

```bash
# Połącz się z droplet
ssh root@<DROPLET_IP>

# Instalacja Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Instalacja docker-compose
apt-get install -y docker-compose

# Klonowanie repozytorium
git clone https://github.com/TWOJ_USERNAME/taniprad.git
cd taniprad
```

### Krok 3: Deploy aplikacji

```bash
# Uruchom w trybie produkcyjnym
docker-compose -f docker-compose.prod.yml up -d

# Sprawdź status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

### Krok 4: Konfiguracja SSL (Let's Encrypt)

```bash
# Zainstaluj certbot
apt-get install -y certbot python3-certbot-nginx

# Uzyskaj certyfikat
certbot --nginx -d prad.januszcieszynski.pl

# Certbot automatycznie zaktualizuje nginx.conf
# Certyfikaty odnowią się automatycznie (cron)
```

### Krok 5: Automatyczne aktualizacje z GitHub

```bash
# Skrypt update.sh
cat > /root/taniprad/update.sh << 'EOF'
#!/bin/bash
cd /root/taniprad
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
docker system prune -f
EOF

chmod +x /root/taniprad/update.sh

# GitHub Webhook (opcjonalnie)
# Możesz skonfigurować webhook w GitHub Settings → Webhooks
# URL: http://prad.januszcieszynski.pl/webhook
# Dodaj endpoint w app.py do obsługi webhooków
```

**Koszt:** ~$6-12/miesiąc (Droplet)

---

## Opcja 3: DigitalOcean Kubernetes (Skalowalne - Dla dużego ruchu)

Dla aplikacji z dużym ruchem (1000+ równoczesnych użytkowników).

```bash
# Utwórz klaster Kubernetes
doctl kubernetes cluster create taniprad-cluster \
  --region fra1 \
  --node-pool "name=worker-pool;size=s-2vcpu-4gb;count=2"

# Deploy aplikacji
kubectl apply -f k8s/

# Skonfiguruj Ingress z automatycznym SSL
kubectl apply -f k8s/ingress.yaml
```

**Koszt:** ~$24/miesiąc (2 nody)

---

## Porównanie opcji

| Opcja | Koszt/miesiąc | Trudność | Skala | SSL | Auto-deploy |
|-------|---------------|----------|-------|-----|-------------|
| **App Platform** | $5-12 | ⭐ Łatwe | 100 użytk. | ✅ Auto | ✅ GitHub |
| **Droplet + Docker** | $6-12 | ⭐⭐ Średnie | 500 użytk. | ⚙️ Certbot | ⚙️ Manual |
| **Kubernetes** | $24+ | ⭐⭐⭐ Trudne | 1000+ użytk. | ✅ Ingress | ✅ GitOps |

---

## Rekomendacja

### Dla Twojej aplikacji (Kalkulator "Tani Prąd"):
✅ **Opcja 1: DigitalOcean App Platform**

**Dlaczego?**
- Prosta konfiguracja (10 minut)
- Automatyczny SSL
- Auto-deploy z GitHub
- Wystarczająca wydajność (100+ równoczesnych użytkowników)
- Niski koszt ($5-12/miesiąc)
- Nie wymaga zarządzania serwerem

---

## Monitoring i debugging

### App Platform
```bash
# Logi
doctl apps logs <APP_ID> --type run --follow

# Status
doctl apps get <APP_ID>

# Restart
doctl apps create-deployment <APP_ID>
```

### Droplet
```bash
# Logi
docker-compose -f docker-compose.prod.yml logs -f backend

# Status kontenerów
docker ps

# Restart
docker-compose -f docker-compose.prod.yml restart
```

### Sprawdzenie działania
```bash
# Test API
curl https://prad.januszcieszynski.pl/api/health

# Test frontendu
curl https://prad.januszcieszynski.pl/
```

---

## Troubleshooting

### Problem: 502 Bad Gateway
```bash
# Sprawdź czy backend działa
docker-compose ps
docker-compose logs backend

# Sprawdź porty
netstat -tulpn | grep 8080
```

### Problem: SSL nie działa
```bash
# App Platform: SSL konfiguruje się automatycznie (5-15 min)
# Droplet: Uruchom ponownie certbot
certbot renew --dry-run
```

### Problem: Aplikacja jest wolna
```bash
# Zwiększ instance size w App Platform
# LUB
# Dodaj więcej workers w Dockerfile:
CMD ["gunicorn", "-w", "8", "-b", "0.0.0.0:8080", "app:app"]
```

---

## Następne kroki

1. ✅ Stwórz repozytorium GitHub
2. ✅ Wypchnij kod do GitHub
3. ✅ Połącz DigitalOcean z GitHub
4. ✅ Utwórz App w App Platform
5. ✅ Skonfiguruj domenę
6. ✅ Gotowe! 🎉

---

## Pytania?

- DigitalOcean Docs: https://docs.digitalocean.com/products/app-platform/
- Community: https://www.digitalocean.com/community/tags/app-platform
