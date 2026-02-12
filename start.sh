#!/bin/bash

# Skrypt startowy dla aplikacji "Tani Prąd"
# Uruchamia backend (Flask) i frontend (SimpleHTTPServer)

set -e

echo "🔌 Uruchamianie aplikacji 'Tani Prąd'..."
echo ""

# Kolory
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Sprawdź czy Python3 jest zainstalowany
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 nie jest zainstalowany${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python3 zainstalowany${NC}"

# Sprawdź czy zależności są zainstalowane
echo "🔍 Sprawdzanie zależności..."
python3 -c "import flask, flask_cors, pdfplumber, PIL" 2>/dev/null || {
    echo -e "${RED}❌ Brakujące zależności. Instaluję...${NC}"
    pip3 install -r requirements.txt
}

echo -e "${GREEN}✅ Wszystkie zależności zainstalowane${NC}"
echo ""

# Zabij poprzednie procesy
echo "🧹 Czyszczenie poprzednich procesów..."
pkill -f "python3.*app.py" 2>/dev/null || true
pkill -f "python3.*-m http.server" 2>/dev/null || true
sleep 1

# Uruchom backend (Flask na porcie 8080)
echo -e "${BLUE}🚀 Uruchamianie backendu (Flask)...${NC}"
python3 app.py > backend.log 2>&1 &
BACKEND_PID=$!

# Poczekaj aż backend się uruchomi
sleep 3

# Sprawdź czy backend działa
if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend działa na http://localhost:8080${NC}"
else
    echo -e "${RED}❌ Backend nie uruchomił się poprawnie${NC}"
    echo "Sprawdź logi w pliku backend.log"
    exit 1
fi

# Uruchom frontend (SimpleHTTPServer na porcie 8000)
echo -e "${BLUE}🚀 Uruchamianie frontendu (HTTP Server)...${NC}"
python3 -m http.server 8000 > frontend.log 2>&1 &
FRONTEND_PID=$!

sleep 2

# Sprawdź czy frontend działa
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend działa na http://localhost:8000${NC}"
else
    echo -e "${RED}❌ Frontend nie uruchomił się poprawnie${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Aplikacja uruchomiona pomyślnie!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "📱 Frontend:  ${BLUE}http://localhost:8000${NC}"
echo -e "🔌 Backend:   ${BLUE}http://localhost:8080${NC}"
echo -e "📊 Health:    ${BLUE}http://localhost:8080/api/health${NC}"
echo ""
echo -e "Backend PID:  ${BACKEND_PID}"
echo -e "Frontend PID: ${FRONTEND_PID}"
echo ""
echo -e "📝 Logi:"
echo -e "   Backend:  backend.log"
echo -e "   Frontend: frontend.log"
echo ""
echo -e "${BLUE}Aby zatrzymać aplikację, naciśnij Ctrl+C${NC}"
echo ""

# Funkcja czyszcząca przy wyjściu
cleanup() {
    echo ""
    echo "🛑 Zatrzymywanie aplikacji..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✅ Aplikacja zatrzymana"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Czekaj w nieskończoność (lub do Ctrl+C)
wait
