"""
Prosty parser faktury bez użycia Claude API
Używa wyrażeń regularnych do ekstrakcji danych
Obsługuje formaty: E.ON, PGE, TAURON
"""
import re


def parse_invoice_simple(text):
    """
    Parsuje fakturę za energię używając regex
    """
    result = {
        "numer_faktury": "",
        "data_faktury": "",
        "okres_rozliczeniowy": "",
        "zuzycie_kwh": 0,
        "pozycje": [],
        "suma_netto": 0,
        "vat_procent": 23,
        "vat_kwota": 0,
        "suma_brutto": 0
    }

    date_pattern = r'\d{2}[./]\d{2}[./]\d{4}'

    # Numer faktury — różne formaty
    patterns = [
        r'FAKTURA\s+VAT\s+NR\s+([\w/]+)',
        r'Numer\s+faktury\s*\n\s*([\w/.-]+)',
        r'Faktura\s+VAT\s+nr\s+([\w/.-]+)',
        r'Nr\s+faktury:?\s*([\w/.-]+)',
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            result["numer_faktury"] = match.group(1).strip()
            break

    # Data faktury
    patterns = [
        rf'[Zz]\s+dnia\s+({date_pattern})',
        rf'Data\s+wystawienia\s*\n?\s*({date_pattern})',
        rf'Data\s+faktury:?\s*({date_pattern})',
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            result["data_faktury"] = match.group(1)
            break

    # Okres rozliczeniowy
    patterns = [
        rf'w\s+okresie\s+od\s+({date_pattern})\s+do\s+({date_pattern})',
        rf'za\s+okres\s+od\s+({date_pattern})\s+do\s+({date_pattern})',
        rf'Rozliczenie\s+za\s+okres\s+od\s+({date_pattern})\s+do\s+({date_pattern})',
        rf'Okres\s+rozliczeniowy\s*\n?\s*({date_pattern})\s*[-–]\s*({date_pattern})',
        rf'okres:?\s*({date_pattern})\s*[-–]\s*({date_pattern})',
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            result["okres_rozliczeniowy"] = f"{match.group(1)} - {match.group(2)}"
            break

    # Sumy — różne formaty
    # E.ON: "Należność za faktyczne zużycie NETTO VAT% VAT BRUTTO"
    match = re.search(r'Należność za faktyczne zużycie\s+([\d,]+)\s+\d+\s+([\d,]+)\s+([\d,]+)', text)
    if match:
        result["suma_netto"] = float(match.group(1).replace(',', '.'))
        result["vat_kwota"] = float(match.group(2).replace(',', '.'))
        result["suma_brutto"] = float(match.group(3).replace(',', '.'))

    # PGE: "Wartość ogółem w rozbiciu na stawki VAT 23 NETTO VAT BRUTTO"
    if result["suma_netto"] == 0:
        match = re.search(r'Wartość\s+ogółem.*?23\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', text)
        if match:
            result["suma_netto"] = float(match.group(1).replace(',', '.'))
            result["vat_kwota"] = float(match.group(2).replace(',', '.'))
            result["suma_brutto"] = float(match.group(3).replace(',', '.'))

    # TAURON/generyczny: "Do zapłaty NETTO VAT BRUTTO"
    if result["suma_netto"] == 0:
        match = re.search(r'Do\s+zapłaty\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', text)
        if match:
            n = float(match.group(1).replace(',', '.'))
            v = float(match.group(2).replace(',', '.'))
            b = float(match.group(3).replace(',', '.'))
            if abs((n + v) - b) < 1.0:
                result["suma_netto"] = n
                result["vat_kwota"] = v
                result["suma_brutto"] = b

    # Zużycie kWh
    consumption_patterns = [
        r'Łączne\s+zużycie\s+energii\s+(\d+)\s*kWh',
        r'Zużycie:?\s*(\d+)\s*kWh',
        r'Zużycie\s+energii\s+elektrycznej.*?([\d.]+)\s*kWh',
        r'(\d+)\s*kWh',
    ]
    for p in consumption_patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            val_str = match.group(1).replace(' ', '')
            # Obsługa separatora tysięcy (2.359 = 2359)
            if re.match(r'^\d{1,3}\.\d{3}$', val_str):
                val_str = val_str.replace('.', '')
            val = float(val_str)
            if 50 <= val <= 100000:
                result["zuzycie_kwh"] = val
                break

    return result


def test_parser():
    """Test parsera na przykładowym tekście"""
    test_text = """Faktura VAT nr 229250916302 z dnia 01.12.2025
ORYGINAŁ
Typ faktury: Rozliczenie
Konto umowy: 80500178393

Rozliczenie sprzedaży i dystrybucji energii elektrycznej w okresie od 06.05.2025 do 30.11.2025

Lp. Pozycja Netto Stawka Podatek Brutto
[zł] VAT [%] VAT [zł] [zł]
1. Wartość prognozowana 382,71 23 88,02 470,73
2. Należność za faktyczne zużycie 496,10 23 114,10 610,20
3. Należność za faktyczne zużycie minus wartość prognozowana 113,39 26,08 139,47

Zużycie: 850 kWh
"""

    result = parse_invoice_simple(test_text)
    print("Wynik parsowania:")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_parser()
