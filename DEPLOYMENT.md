# 🚀 Deployment - Kalkulator "Tani Prąd"

## Obecny stan (Development)

✅ **Zaimplementowane zabezpieczenia:**
- Unikalne nazwy plików (UUID + timestamp) - zapobiega kolizjom
- Rate limiting: 10 requestów / 60 sekund na IP
- Automatyczne czyszczenie starych plików (max 1h)
- Walidacja rozmiaru plików (max 10MB)
- Minimalne opóźnienie 3s (UX + backend throttling)

⚠️ **Ograniczenia:**
- Flask development server - obsługuje tylko **1 request na raz**
- Rate limiting w pamięci (resetuje się po restarcie)
- Debug mode włączony

## Deployment dla większej skali (100+ równoczesnych użytkowników)

### Opcja 1: Gunicorn + Nginx (Prosty deployment)

```bash
# 1. Zainstaluj gunicorn
pip install gunicorn

# 2. Uruchom z wieloma workerami
gunicorn -w 4 -b 0.0.0.0:8080 app:app
# -w 4 = 4 workery (można 2x liczba CPU)
```

**Wydajność:** ~40-100 równoczesnych requestów

### Opcja 2: Docker + Nginx + Redis (Production-ready)

```yaml
# docker-compose-production.yml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-prod.conf:/etc/nginx/nginx.conf

  backend:
    build: .
    command: gunicorn -w 4 -b 0.0.0.0:8080 app:app
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:alpine
    # Rate limiting storage
```

**Wydajność:** ~200-500 równoczesnych requestów

### Opcja 3: Kubernetes + CDN (Skala korporacyjna)

Dla 1000+ równoczesnych użytkowników:
- Kubernetes autoscaling
- CloudFlare/Cloudinary dla plików
- PostgreSQL dla statystyk
- Celery + RabbitMQ dla kolejkowania

**Wydajność:** 1000+ równoczesnych requestów

## Co obecnie obsługuje aplikacja?

### Scenariusze testowe:

**✅ Pojedynczy użytkownik:** Działa płynnie
**✅ 2-3 użytkowników równolegle:** Działa, ale może być wolno (jeden request na raz)
**⚠️ 10+ użytkowników równolegle:** Będą problemy - requesty w kolejce
**❌ 100+ użytkowników równolegle:** Aplikacja padnie

## Rekomendacje

### Dla małej kampanii (<50 użytkowników dziennie):
✅ Obecna konfiguracja wystarczy

### Dla średniej kampanii (50-500 użytkowników dziennie):
🔄 Przejdź na Opcję 1 (Gunicorn)

### Dla dużej kampanii (500+ użytkowników dziennie):
🚀 Opcja 2 (Docker + Redis)

### Dla kampanii narodowej (10k+ użytkowników dziennie):
☁️ Opcja 3 (Kubernetes + Cloud)

## Quick deployment script

```bash
# Development (obecny)
python3 app.py

# Production-light (gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 app:app --timeout 120

# Production-full (docker)
docker-compose up -d
```

## Monitoring

Dodaj do app.py metryki:
- Liczba requestów / minuta
- Średni czas przetwarzania
- Liczba błędów
- Wykorzystanie CPU/RAM

```python
# Przykład:
@app.route('/api/stats', methods=['GET'])
def stats():
    return jsonify({
        'total_requests': total_requests,
        'avg_processing_time': avg_time,
        'error_rate': error_rate
    })
```
