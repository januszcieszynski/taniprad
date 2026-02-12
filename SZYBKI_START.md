# 🚀 Szybki Start - Deployment na DigitalOcean

## ✅ Co już jest gotowe:

- ✅ Repozytorium GitHub: https://github.com/januszcieszynski/taniprad
- ✅ Kod wgrany na GitHub
- ✅ Dockerfile produkcyjny
- ✅ Konfiguracja nginx
- ✅ Spec dla DigitalOcean App Platform (`.do/app.yaml`)

---

## 📋 Co musisz teraz zrobić:

### Krok 1: Połącz DigitalOcean z GitHub (jeśli jeszcze nie zrobione)

1. Zaloguj się na **DigitalOcean**: https://cloud.digitalocean.com/
2. Przejdź do **Settings** (ikona koła zębatego w lewym dolnym rogu)
3. Wybierz **Applications** → **GitHub**
4. Kliknij **Install GitHub App**
5. Autoryzuj DigitalOcean do dostępu do repozytorium `taniprad`

### Krok 2: Utwórz aplikację w App Platform

#### Opcja A: Przez interfejs webowy (ZALECANE)

1. W DigitalOcean Dashboard kliknij **Create** → **Apps**
2. Wybierz **GitHub** jako źródło
3. Wybierz repozytorium: **januszcieszynski/taniprad**
4. Branch: **main**
5. DigitalOcean automatycznie wykryje **Dockerfile**

**Konfiguracja backendu:**
- Name: `backend`
- HTTP Port: `8080`
- Build Command: (zostaw auto-detect)
- Run Command: (zostaw auto-detect)
- Instance Size: **Basic** (512 MB RAM, $5/miesiąc)
- Region: **Frankfurt** (fra1)

**Dodaj Route dla frontendu:**
- Kliknij **Add Component** → **Static Site**
- Source Directory: `/`
- Build Command: (zostaw puste)
- Output Directory: `/`

**Dodaj domenę:**
- W sekcji "Settings" → "Domains"
- Kliknij **Add Domain**
- Wpisz: `prad.januszcieszynski.pl`
- DigitalOcean automatycznie wygeneruje SSL (Let's Encrypt)

6. Kliknij **Create Resources**

#### Opcja B: Przez CLI (szybsza)

```bash
# Jeśli masz zainstalowane doctl:
doctl apps create --spec .do/app.yaml

# Sprawdź status:
doctl apps list

# Zobacz logi:
doctl apps logs <APP_ID> --type run --follow
```

### Krok 3: Skonfiguruj DNS

W panelu Twojego domainy providera (np. nazwa.pl, cloudflare):

1. Znajdź IP lub CNAME, które DigitalOcean pokazuje dla Twojej aplikacji
2. Utwórz rekord DNS:

```
Type: A (lub CNAME)
Name: prad
Value: <IP_LUB_CNAME_Z_DIGITALOCEAN>
TTL: 3600
```

**Przykład:**
```
A       prad    134.209.xxx.xxx     3600
```

### Krok 4: Poczekaj na deployment

- Deployment trwa zwykle **5-10 minut**
- SSL konfiguruje się automatycznie (może zająć dodatkowe 5-15 minut)
- Możesz sprawdzić status w zakładce **Activity** w DigitalOcean

### Krok 5: Testuj aplikację

Po zakończeniu deploymentu:

```bash
# Test API
curl https://prad.januszcieszynski.pl/api/health

# Powinno zwrócić:
# {"status": "ok"}

# Test frontendu
curl https://prad.januszcieszynski.pl/
```

Lub otwórz w przeglądarce: **https://prad.januszcieszynski.pl**

---

## 🔄 Automatyczne deployments

Od teraz każdy push do GitHub automatycznie wdroży nową wersję:

```bash
# Wprowadź zmiany w kodzie
git add .
git commit -m "Nowa funkcjonalność"
git push

# DigitalOcean automatycznie:
# 1. Wykryje zmianę w repozytorium
# 2. Zbuduje nowy obraz Docker
# 3. Wdroży nową wersję (zero downtime)
```

---

## 💰 Koszty

- **Basic Plan**: ~$5/miesiąc (512 MB RAM, 1 vCPU)
- **Professional Plan**: ~$12/miesiąc (1 GB RAM, 1 vCPU) - dla większego ruchu

Możesz zacząć od Basic i skalować w górę w razie potrzeby.

---

## 📊 Monitoring

W DigitalOcean Dashboard:
- **Metrics**: CPU, RAM, ruch sieciowy
- **Logs**: Logi aplikacji w czasie rzeczywistym
- **Activity**: Historia deploymentów

---

## 🐛 Troubleshooting

### Problem: Deployment się nie udaje

```bash
# Sprawdź logi budowania
doctl apps logs <APP_ID> --type build

# Sprawdź logi runtime
doctl apps logs <APP_ID> --type run
```

### Problem: 502 Bad Gateway

- Poczekaj 5-10 minut (startup może trwać)
- Sprawdź czy port 8080 jest poprawnie skonfigurowany
- Sprawdź logi: `doctl apps logs <APP_ID> --type run`

### Problem: SSL nie działa

- SSL konfiguruje się automatycznie, ale może zająć 5-15 minut
- Upewnij się, że DNS jest poprawnie skonfigurowany
- Sprawdź w DigitalOcean Settings → Domains

---

## 📚 Dodatkowe zasoby

- **Szczegółowy przewodnik**: Zobacz `DIGITALOCEAN_SETUP.md`
- **Dokumentacja DigitalOcean**: https://docs.digitalocean.com/products/app-platform/
- **Repozytorium GitHub**: https://github.com/januszcieszynski/taniprad

---

## ✅ Checklist

- [ ] DigitalOcean połączony z GitHub
- [ ] Aplikacja utworzona w App Platform
- [ ] Domena `prad.januszcieszynski.pl` skonfigurowana
- [ ] DNS zaktualizowany
- [ ] SSL aktywny
- [ ] Aplikacja działa: https://prad.januszcieszynski.pl

---

## 🎉 Gotowe!

Po wykonaniu tych kroków Twoja aplikacja będzie dostępna pod adresem:

**https://prad.januszcieszynski.pl**

Każda zmiana w kodzie będzie automatycznie wdrażana na produkcję! 🚀
