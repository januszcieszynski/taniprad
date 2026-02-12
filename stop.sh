#!/bin/bash

# Skrypt zatrzymujący aplikację "Tani Prąd"

echo "🛑 Zatrzymywanie aplikacji 'Tani Prąd'..."

# Zatrzymaj backend
echo "   Zatrzymywanie backendu..."
pkill -f "python3.*app.py" 2>/dev/null && echo "   ✅ Backend zatrzymany" || echo "   ℹ️  Backend nie był uruchomiony"

# Zatrzymaj frontend
echo "   Zatrzymywanie frontendu..."
pkill -f "python3.*-m http.server" 2>/dev/null && echo "   ✅ Frontend zatrzymany" || echo "   ℹ️  Frontend nie był uruchomiony"

echo ""
echo "✅ Aplikacja zatrzymana"
