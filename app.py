#!/usr/bin/env python3
"""
Backend dla kalkulatora "Tani prąd"
Obsługuje upload faktury PDF lub zdjęcia i ekstraktuje dane do kalkulatora
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pytesseract
from PIL import Image
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from parser_advanced import parse_invoice

app = Flask(__name__)
CORS(app)

# Konfiguracja
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Rate limiting - prosty mechanizm w pamięci (dla production użyj Redis)
from collections import defaultdict
from threading import Lock
import time

rate_limit_data = defaultdict(list)
rate_limit_lock = Lock()

def check_rate_limit(ip_address, max_requests=10, window_seconds=60):
    """
    Sprawdza czy użytkownik nie przekroczył limitu requestów
    max_requests: maksymalna liczba requestów
    window_seconds: okno czasowe w sekundach
    """
    with rate_limit_lock:
        now = time.time()
        # Usuń stare requesty sprzed okna czasowego
        rate_limit_data[ip_address] = [
            req_time for req_time in rate_limit_data[ip_address]
            if now - req_time < window_seconds
        ]

        # Sprawdź limit
        if len(rate_limit_data[ip_address]) >= max_requests:
            return False

        # Dodaj nowy request
        rate_limit_data[ip_address].append(now)
        return True

def cleanup_old_files(folder, max_age_seconds=3600):
    """
    Usuwa stare pliki z folderu tymczasowego
    max_age_seconds: maksymalny wiek pliku w sekundach (domyślnie 1 godzina)
    """
    try:
        now = time.time()
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    os.remove(filepath)
                    print(f"🗑️  Usunięto stary plik: {filename}")
    except Exception as e:
        print(f"⚠️  Błąd podczas czyszczenia plików: {e}")

# Wyczyść stare pliki przy starcie
cleanup_old_files(UPLOAD_FOLDER)

print("✅ Parser faktur zainicjalizowany (pdfplumber + regex)")
print("✅ Rate limiting: 10 requestów / 60 sekund na IP")
print("✅ Unikalne nazwy plików (UUID + timestamp)")
print("✅ Automatyczne czyszczenie plików (max 1h)")


def allowed_file(filename):
    """Sprawdza czy rozszerzenie pliku jest dozwolone"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_image(filepath):
    """Ekstraktuje tekst ze zdjęcia używając OCR (Tesseract)"""
    try:
        image = Image.open(filepath)
        text = pytesseract.image_to_string(image, lang='pol')
        return text
    except Exception as e:
        print(f"Błąd przy OCR: {e}")
        return None


def calculate_savings(invoice_data):
    """
    Oblicza oszczędności na podstawie danych z faktury
    według 4 filarów ustawy "Tani prąd"
    """
    
    # Dane wejściowe
    pozycje = invoice_data.get('pozycje', [])
    suma_netto_before = invoice_data.get('suma_netto', 0)
    vat_before = invoice_data.get('vat_procent', 23) / 100
    vat_kwota_before = invoice_data.get('vat_kwota', 0)
    suma_brutto_before = invoice_data.get('suma_brutto', 0)
    zuzycie_kwh = invoice_data.get('zuzycie_kwh', 0)
    
    # Filar 4: Zerowanie opłat (mocowa, OZE, kogeneracyjna, przejściowa)
    oplaty_do_zerowania = ['mocowa', 'oze', 'kogeneracyjna', 'przejściowa']
    filar4_savings = 0
    
    pozycje_after = []
    for pozycja in pozycje:
        nazwa_lower = pozycja['nazwa'].lower()
        zerowana = any(oplata in nazwa_lower for oplata in oplaty_do_zerowania)
        
        pozycja_after = {
            'nazwa': pozycja['nazwa'],
            'before': pozycja['wartosc_netto'],
            'after': 0 if zerowana else pozycja['wartosc_netto'],
            'kategoria': pozycja['kategoria'],
            'zerowana': zerowana
        }
        
        if zerowana:
            filar4_savings += pozycja['wartosc_netto']
        
        pozycje_after.append(pozycja_after)
    
    # Filar 2: Reforma certyfikatów (~80 zł/rok dla przeciętnego gospodarstwa 2200 kWh/rok)
    # Proporcjonalnie do zużycia
    przecietne_zuzycie_rok = 2200
    filar2_oszczednosc_rok = 80
    
    if zuzycie_kwh > 0:
        # Szacujemy roczne zużycie na podstawie okresu faktury
        # Zakładamy że faktura jest za 1 miesiąc (można to poprawić analizując okres)
        zuzycie_rok_szacowane = zuzycie_kwh * 12
        filar2_savings = (zuzycie_rok_szacowane / przecietne_zuzycie_rok) * filar2_oszczednosc_rok / 12
    else:
        filar2_savings = 0
    
    # Filar 3: Obniżka taryf dystrybucyjnych o ~15% (limit WACC do NBP+3pp)
    suma_dystrybucja = sum(p['after'] for p in pozycje_after if p['kategoria'] == 'dystrybucja')
    filar3_savings = suma_dystrybucja * 0.15
    
    # Stosujemy Filar 3 do pozycji dystrybucyjnych
    for pozycja in pozycje_after:
        if pozycja['kategoria'] == 'dystrybucja':
            pozycja['after'] = pozycja['after'] * 0.85  # -15%
    
    # Odejmujemy Filar 2 od energii czynnej
    for pozycja in pozycje_after:
        if 'energia czynna' in pozycja['nazwa'].lower():
            pozycja['after'] = max(0, pozycja['after'] - filar2_savings)
            break
    
    # Suma netto po zmianach
    suma_netto_after = sum(p['after'] for p in pozycje_after)
    
    # Filar 1: VAT 23% → 5%
    vat_after = 0.05
    vat_kwota_after = suma_netto_after * vat_after
    suma_brutto_after = suma_netto_after + vat_kwota_after
    
    filar1_savings = (vat_before - vat_after) * suma_netto_after
    
    # Całkowita oszczędność
    total_savings = suma_brutto_before - suma_brutto_after
    savings_percent = (total_savings / suma_brutto_before * 100) if suma_brutto_before > 0 else 0
    
    return {
        'before': {
            'pozycje': [{'nazwa': p['nazwa'], 'wartosc': p['before'], 'kategoria': p['kategoria']} 
                       for p in pozycje_after],
            'suma_netto': round(suma_netto_before, 2),
            'vat_procent': round(vat_before * 100, 0),
            'vat_kwota': round(vat_kwota_before, 2),
            'suma_brutto': round(suma_brutto_before, 2)
        },
        'after': {
            'pozycje': [{'nazwa': p['nazwa'], 'wartosc': p['after'], 'kategoria': p['kategoria'], 
                        'zerowana': p.get('zerowana', False)} 
                       for p in pozycje_after],
            'suma_netto': round(suma_netto_after, 2),
            'vat_procent': round(vat_after * 100, 0),
            'vat_kwota': round(vat_kwota_after, 2),
            'suma_brutto': round(suma_brutto_after, 2)
        },
        'savings': {
            'filar1_vat': round(filar1_savings, 2),
            'filar2_certyfikaty': round(filar2_savings, 2),
            'filar3_dystrybucja': round(filar3_savings, 2),
            'filar4_oplaty': round(filar4_savings, 2),
            'total': round(total_savings, 2),
            'percent': round(savings_percent, 1)
        },
        'metadata': {
            'numer_faktury': invoice_data.get('numer_faktury', ''),
            'data_faktury': invoice_data.get('data_faktury', ''),
            'okres_rozliczeniowy': invoice_data.get('okres_rozliczeniowy', ''),
            'zuzycie_kwh': zuzycie_kwh
        }
    }


@app.route('/')
def index():
    """Strona główna z prostym HTML do testowania"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tani Prąd - Backend API</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .upload-form { border: 2px dashed #ccc; padding: 30px; border-radius: 10px; }
            input[type="file"] { margin: 20px 0; }
            button { background: #22d3ee; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #0e7490; }
            #result { margin-top: 30px; }
            pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🔌 Kalkulator "Tani Prąd" - API</h1>
        <div class="upload-form">
            <h2>Prześlij fakturę za prąd</h2>
            <p>Akceptowane formaty: PDF, JPG, PNG</p>
            <form id="uploadForm">
                <input type="file" id="fileInput" accept=".pdf,.jpg,.jpeg,.png" required>
                <br>
                <button type="submit">Analizuj fakturę</button>
            </form>
        </div>
        <div id="result"></div>
        
        <script>
        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData();
            const file = document.getElementById('fileInput').files[0];
            formData.append('file', file);
            
            document.getElementById('result').innerHTML = '<p>Analizuję fakturę...</p>';
            
            try {
                const response = await fetch('/api/analyze-invoice', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('result').innerHTML = 
                        '<h3>✅ Wynik analizy:</h3><pre>' + 
                        JSON.stringify(data, null, 2) + 
                        '</pre>';
                } else {
                    document.getElementById('result').innerHTML = 
                        '<h3>❌ Błąd:</h3><p>' + data.error + '</p>';
                }
            } catch (error) {
                document.getElementById('result').innerHTML = 
                    '<h3>❌ Błąd:</h3><p>' + error.message + '</p>';
            }
        };
        </script>
    </body>
    </html>
    """


@app.route('/api/analyze-invoice', methods=['POST'])
def analyze_invoice():
    """
    Endpoint do analizy faktury
    Akceptuje PDF lub zdjęcie, zwraca strukturyzowane dane i wyliczone oszczędności
    """

    # Rate limiting
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({
            'error': 'Zbyt wiele requestów. Spróbuj ponownie za chwilę.',
            'retry_after': 60
        }), 429

    # Sprawdź rozmiar pliku
    if request.content_length and request.content_length > MAX_FILE_SIZE:
        return jsonify({
            'error': f'Plik jest za duży. Maksymalny rozmiar to {MAX_FILE_SIZE / 1024 / 1024:.0f} MB'
        }), 413

    # Sprawdź czy plik został przesłany
    if 'file' not in request.files:
        return jsonify({'error': 'Brak pliku'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Nie wybrano pliku'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Niedozwolony format pliku. Użyj PDF, JPG lub PNG'}), 400

    # Generuj unikalną nazwę pliku (UUID + timestamp)
    original_filename = secure_filename(file.filename)
    file_ext = original_filename.rsplit('.', 1)[1].lower()
    unique_id = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp() * 1000)}"
    unique_filename = f"{unique_id}.{file_ext}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

    file.save(filepath)
    
    try:
        # Parsuj fakturę w zależności od typu pliku
        invoice_data = None

        if file_ext == 'pdf':
            # Parsuj PDF używając zaawansowanego parsera
            try:
                invoice_data = parse_invoice(filepath)
            except Exception as e:
                return jsonify({
                    'error': 'Nie udało się sparsować faktury PDF',
                    'details': str(e)
                }), 500
        else:
            # Dla obrazów użyj OCR
            text = extract_text_from_image(filepath)
            if not text:
                return jsonify({'error': 'Nie udało się wyekstraktować tekstu z obrazu'}), 500

            # TODO: Dodać parser dla obrazów
            return jsonify({
                'error': 'Parsowanie obrazów nie jest jeszcze zaimplementowane',
                'text_preview': text[:500]
            }), 501

        if not invoice_data:
            return jsonify({'error': 'Nie udało się sparsować faktury'}), 500

        # Oblicz oszczędności
        result = calculate_savings(invoice_data)

        # Dodaj informację o metodzie parsowania
        result['_parser_method'] = 'pdfplumber+regex'

        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': f'Błąd przetwarzania: {str(e)}'}), 500
    
    finally:
        # Usuń plik tymczasowy
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"⚠️  Nie udało się usunąć pliku {filepath}: {e}")

        # Wyczyść stare pliki co jakiś czas
        import random
        if random.random() < 0.1:  # 10% szans przy każdym requeście
            cleanup_old_files(UPLOAD_FOLDER)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'tani-prad-api'}), 200


if __name__ == '__main__':
    print("🔌 Tani Prąd Backend - uruchamianie...")
    print("📋 Endpoint: POST /api/analyze-invoice")
    print("💚 Health: GET /api/health")
    app.run(host='0.0.0.0', port=8080, debug=True)
