#!/bin/bash
# Skrypt diagnostyczny dla dropleta
# Uruchom to na dropecie: bash <(curl -s https://raw.githubusercontent.com/januszcieszynski/taniprad/main/diagnose-droplet.sh)

echo "🔍 Diagnostyka dropleta DigitalOcean"
echo "===================================="
echo ""

echo "📊 Informacje o systemie:"
echo "------------------------"
uname -a
echo ""

echo "🌐 Adres IP:"
echo "------------------------"
hostname -I
curl -s ifconfig.me
echo ""
echo ""

echo "🔧 Zainstalowane narzędzia:"
echo "------------------------"
echo -n "Nginx: "
if command -v nginx &> /dev/null; then
    nginx -v 2>&1 | grep -oP 'nginx/\K[0-9.]+'
else
    echo "❌ Nie zainstalowany"
fi

echo -n "Docker: "
if command -v docker &> /dev/null; then
    docker --version | grep -oP 'Docker version \K[0-9.]+'
else
    echo "❌ Nie zainstalowany"
fi

echo -n "Docker Compose: "
if command -v docker-compose &> /dev/null; then
    docker-compose --version | grep -oP 'docker-compose version \K[0-9.]+'
else
    echo "❌ Nie zainstalowany"
fi

echo -n "Certbot: "
if command -v certbot &> /dev/null; then
    certbot --version 2>&1 | grep -oP 'certbot \K[0-9.]+'
else
    echo "❌ Nie zainstalowany"
fi
echo ""

echo "🔌 Zajęte porty:"
echo "------------------------"
sudo netstat -tulpn 2>/dev/null | grep LISTEN | awk '{print $4 "\t" $7}' | sort -u || \
    sudo ss -tulpn | grep LISTEN | awk '{print $5 "\t" $7}' | sort -u
echo ""

echo "🌍 Nginx - aktywne serwisy:"
echo "------------------------"
if [ -d /etc/nginx/sites-enabled ]; then
    ls -la /etc/nginx/sites-enabled/ | grep -v ^d | grep -v ^l | awk '{print $9}' | grep -v "^$"

    echo ""
    echo "Domeny skonfigurowane w nginx:"
    for site in /etc/nginx/sites-enabled/*; do
        if [ -f "$site" ]; then
            echo "  - $(basename $site):"
            grep -h "server_name" "$site" | grep -v "#" | awk '{print "    " $0}'
        fi
    done
else
    echo "❌ Brak katalogu /etc/nginx/sites-enabled"
fi
echo ""

echo "🐳 Docker - działające kontenery:"
echo "------------------------"
if command -v docker &> /dev/null; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    if [ $(docker ps -q | wc -l) -eq 0 ]; then
        echo "Brak działających kontenerów"
    fi
else
    echo "Docker nie jest zainstalowany"
fi
echo ""

echo "💾 Wolne miejsce na dysku:"
echo "------------------------"
df -h / | tail -1 | awk '{print "Użyte: " $3 " / " $2 " (" $5 ")"}'
echo ""

echo "🧠 Wykorzystanie RAM:"
echo "------------------------"
free -h | grep Mem | awk '{print "Użyte: " $3 " / " $2}'
echo ""

echo "📜 Ostatnie logi nginx (jeśli jest):"
echo "------------------------"
if [ -f /var/log/nginx/error.log ]; then
    tail -5 /var/log/nginx/error.log
else
    echo "Brak logów nginx"
fi
echo ""

echo "✅ Diagnostyka zakończona!"
echo ""
echo "Teraz możesz:"
echo "1. Skopiować wynik i wysłać do Claude"
echo "2. Zainstalować brakujące narzędzia (jeśli są potrzebne)"
echo "3. Przejść do instalacji aplikacji według DROPLET_SETUP.md"
