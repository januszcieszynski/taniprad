#!/bin/bash
# Skrypt aktualizacji aplikacji na produkcji
# Uruchom na serwerze: ./deploy-update.sh

set -e

echo "🚀 Aktualizacja aplikacji Tani Prąd na produkcji..."
echo ""

# Kolory
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Konfiguracja
APP_DIR="/opt/taniprad"
FRONTEND_DIR="/var/www/taniprad"
DOCKER_COMPOSE_FILE="docker-compose.droplet.yml"

# Sprawdź czy jesteśmy w odpowiednim katalogu
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}❌ Katalog $APP_DIR nie istnieje${NC}"
    echo "Uruchom najpierw pełną instalację zgodnie z QUICK_INSTALL.md"
    exit 1
fi

cd $APP_DIR

echo -e "${BLUE}📥 Pobieranie najnowszych zmian z GitHub...${NC}"
git fetch origin
git status

echo ""
echo -e "${YELLOW}Aktualne zmiany do zaciągnięcia:${NC}"
git log --oneline HEAD..origin/main | head -10

echo ""
read -p "Czy chcesz kontynuować aktualizację? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Anulowano"
    exit 0
fi

echo ""
echo -e "${BLUE}🔄 Aktualizacja kodu...${NC}"
git pull origin main

echo ""
echo -e "${BLUE}🛑 Zatrzymywanie obecnych kontenerów...${NC}"
if [ -f "$DOCKER_COMPOSE_FILE" ]; then
    docker-compose -f $DOCKER_COMPOSE_FILE down
else
    echo -e "${YELLOW}⚠️  Plik $DOCKER_COMPOSE_FILE nie znaleziony, używam standardowego${NC}"
    DOCKER_COMPOSE_FILE="docker-compose.yml"
fi

echo ""
echo -e "${BLUE}🔨 Budowanie nowego obrazu backendu...${NC}"
docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache backend

echo ""
echo -e "${BLUE}🚀 Uruchamianie zaktualizowanych kontenerów...${NC}"
docker-compose -f $DOCKER_COMPOSE_FILE up -d

echo ""
echo -e "${BLUE}📄 Aktualizacja frontendu...${NC}"
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${YELLOW}Tworzenie katalogu frontendu...${NC}"
    sudo mkdir -p $FRONTEND_DIR
fi

sudo cp index.html $FRONTEND_DIR/
sudo chown -R www-data:www-data $FRONTEND_DIR
sudo chmod -R 755 $FRONTEND_DIR

echo -e "${GREEN}✅ Frontend zaktualizowany${NC}"

echo ""
echo -e "${BLUE}🔧 Sprawdzanie konfiguracji nginx...${NC}"
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo -e "${GREEN}✅ Konfiguracja nginx prawidłowa${NC}"
    echo -e "${BLUE}🔄 Przeładowanie nginx...${NC}"
    sudo systemctl reload nginx
    echo -e "${GREEN}✅ Nginx przeładowany${NC}"
else
    echo -e "${RED}❌ Błąd w konfiguracji nginx!${NC}"
    sudo nginx -t
fi

echo ""
echo -e "${BLUE}⏳ Czekam 5 sekund na uruchomienie backendu...${NC}"
sleep 5

echo ""
echo -e "${BLUE}🏥 Sprawdzanie stanu aplikacji...${NC}"
echo ""

# Sprawdź kontenery
echo "Kontenery Docker:"
docker-compose -f $DOCKER_COMPOSE_FILE ps

echo ""
# Sprawdź backend health
echo "Test backendu:"
if curl -s http://localhost:8080/api/health | grep -q "ok"; then
    echo -e "${GREEN}✅ Backend działa poprawnie${NC}"
else
    echo -e "${RED}❌ Backend nie odpowiada!${NC}"
    echo "Sprawdź logi: docker-compose -f $DOCKER_COMPOSE_FILE logs backend"
fi

echo ""
# Sprawdź frontend
echo "Test frontendu (localhost):"
if curl -s http://localhost | grep -q "Kalkulator"; then
    echo -e "${GREEN}✅ Frontend dostępny lokalnie${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend może nie być dostępny${NC}"
fi

echo ""
echo -e "${BLUE}🧹 Czyszczenie starych obrazów Docker...${NC}"
docker system prune -f -a --volumes 2>&1 | grep -v "WARNING" || true

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Aktualizacja zakończona pomyślnie!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "📊 Sprawdź działanie:"
echo -e "   Backend:  ${BLUE}curl http://localhost:8080/api/health${NC}"
echo -e "   Frontend: ${BLUE}https://prad.januszcieszynski.pl${NC}"
echo ""
echo -e "📝 Logi:"
echo -e "   ${BLUE}docker-compose -f $DOCKER_COMPOSE_FILE logs -f backend${NC}"
echo ""
echo -e "📈 Status:"
echo -e "   ${BLUE}docker-compose -f $DOCKER_COMPOSE_FILE ps${NC}"
echo ""

# Pokaż ostatnie logi backendu
echo -e "${BLUE}📋 Ostatnie 20 linii logów backendu:${NC}"
docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=20 backend

echo ""
echo -e "${GREEN}Gotowe! 🎉${NC}"
