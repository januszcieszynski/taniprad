#!/bin/bash
# Skrypt do diagnozy sieci Docker dla istniejącego nginx
# Uruchom na dropecie przed instalacją

echo "🔍 Diagnostyka sieci Docker dla nginx"
echo "======================================"
echo ""

echo "📦 Działające kontenery:"
echo "------------------------"
docker ps --format "table {{.Names}}\t{{.Networks}}\t{{.Ports}}"
echo ""

echo "🌐 Dostępne sieci Docker:"
echo "------------------------"
docker network ls
echo ""

echo "🔎 Szczegóły sieci ksef-nginx:"
echo "------------------------"
NGINX_CONTAINER=$(docker ps --format "{{.Names}}" | grep nginx | head -1)

if [ -n "$NGINX_CONTAINER" ]; then
    echo "Znaleziono kontener nginx: $NGINX_CONTAINER"
    echo ""

    echo "Sieci kontenera $NGINX_CONTAINER:"
    docker inspect $NGINX_CONTAINER | grep -A 5 '"Networks"' | head -20
    echo ""

    echo "Wolumeny (mounty) kontenera $NGINX_CONTAINER:"
    docker inspect $NGINX_CONTAINER | grep -A 3 '"Mounts"' | head -30
    echo ""

    # Znajdź nazwę sieci
    NETWORK_NAME=$(docker inspect $NGINX_CONTAINER --format='{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}')
    echo "Główna sieć: $NETWORK_NAME"
    echo ""

    echo "Kontenery w sieci $NETWORK_NAME:"
    docker network inspect $NETWORK_NAME --format='{{range .Containers}}{{.Name}} ({{.IPv4Address}}){{println}}{{end}}'
    echo ""

    echo "Ścieżki konfiguracji nginx:"
    docker exec $NGINX_CONTAINER find /etc/nginx -name "*.conf" 2>/dev/null | head -10
    echo ""

    echo "📋 PODSUMOWANIE DLA KONFIGURACJI:"
    echo "================================="
    echo "1. Nazwa sieci do użycia w docker-compose:"
    echo "   name: $NETWORK_NAME"
    echo ""
    echo "2. Nazwa kontenera nginx:"
    echo "   $NGINX_CONTAINER"
    echo ""
    echo "3. Polecenia do sprawdzenia konfiguracji nginx:"
    echo "   docker exec $NGINX_CONTAINER ls -la /etc/nginx/conf.d/"
    echo "   docker exec $NGINX_CONTAINER cat /etc/nginx/nginx.conf"
    echo ""
else
    echo "❌ Nie znaleziono kontenera nginx!"
    echo "Sprawdź ręcznie:"
    docker ps
fi

echo ""
echo "✅ Diagnostyka zakończona!"
echo ""
echo "Następne kroki:"
echo "1. Zaktualizuj docker-compose.droplet-shared.yml - zmień 'name:' na właściwą nazwę sieci"
echo "2. Znajdź katalog z konfiguracją nginx (volume mount)"
echo "3. Dodaj konfigurację dla prad.januszcieszynski.pl"
