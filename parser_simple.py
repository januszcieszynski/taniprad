"""
Prosty parser faktury bez użycia Claude API
Używa wyrażeń regularnych do ekstrakcji danych
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

    # Numer faktury
    match = re.search(r'Faktura VAT nr\s+(\d+)', text)
    if match:
        result["numer_faktury"] = match.group(1)

    # Data faktury
    match = re.search(r'z dnia\s+(\d{2}\.\d{2}\.\d{4})', text)
    if match:
        result["data_faktury"] = match.group(1)

    # Okres rozliczeniowy
    match = re.search(r'w okresie od\s+(\d{2}\.\d{2}\.\d{4})\s+do\s+(\d{2}\.\d{2}\.\d{4})', text)
    if match:
        result["okres_rozliczeniowy"] = f"{match.group(1)} - {match.group(2)}"

    # Szukamy sekcji ze szczegółami zużycia
    # Format: "Lp. Pozycja Netto ... Brutto"
    lines = text.split('\n')

    in_items_section = False
    for i, line in enumerate(lines):
        # Sprawdź czy to nagłówek tabeli
        if 'Pozycja' in line and 'Netto' in line and 'Brutto' in line:
            in_items_section = True
            continue

        if in_items_section:
            # Koniec sekcji pozycji
            if 'Razem' in line or 'Suma' in line or 'należność' in line.lower():
                in_items_section = False

    # Próbujemy znaleźć wartości netto i brutto z głównej sekcji rozliczenia
    # "Należność za faktyczne zużycie" + wartości
    match = re.search(r'Należność za faktyczne zużycie\s+([\d,]+)\s+\d+\s+([\d,]+)\s+([\d,]+)', text)
    if match:
        netto = float(match.group(1).replace(',', '.'))
        vat = float(match.group(2).replace(',', '.'))
        brutto = float(match.group(3).replace(',', '.'))

        result["suma_netto"] = netto
        result["vat_kwota"] = vat
        result["suma_brutto"] = brutto

        # Dodaj główną pozycję
        result["pozycje"].append({
            "nazwa": "Energia elektryczna - faktyczne zużycie",
            "wartosc_netto": netto,
            "kategoria": "sprzedaz"
        })

    # Szukamy zużycia w kWh
    # Może być w różnych formatach
    match = re.search(r'(\d+)\s*kWh', text, re.IGNORECASE)
    if match:
        result["zuzycie_kwh"] = float(match.group(1))

    # Alternatywnie szukamy w tabeli zużycia
    match = re.search(r'Energia elektryczna.*?(\d+)\s+kWh', text, re.IGNORECASE | re.DOTALL)
    if match and result["zuzycie_kwh"] == 0:
        result["zuzycie_kwh"] = float(match.group(1))

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
