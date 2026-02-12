"""
Zaawansowany parser faktur za energię elektryczną
Wykorzystuje pdfplumber do ekstrakcji tabel i strukturyzowanych danych
"""
import re
import pdfplumber
from typing import Dict, List, Optional
from decimal import Decimal


class InvoiceParser:
    """Parser faktur za energię elektryczną"""

    def __init__(self):
        self.categories_mapping = {
            'sprzedaz': [
                'energia czynna',
                'sprzedaż energii',
                'opłata handlowa',
                'energia elektryczna'
            ],
            'dystrybucja': [
                'dystrybucja',
                'sieciowa',
                'jakościowa',
                'mocowa',
                'oze',
                'kogeneracja',
                'przejściowa',
                'abonamentowa',
                'opłata stała'
            ]
        }

    def parse_pdf(self, filepath: str) -> Dict:
        """Główna metoda parsowania PDF"""
        with pdfplumber.open(filepath) as pdf:
            # Ekstraktuj tekst
            text = self._extract_text(pdf)

            # Ekstraktuj tabele
            tables = self._extract_tables(pdf)

            # Parsuj dane
            result = self._parse_invoice_data(text, tables)

            return result

    def _extract_text(self, pdf) -> str:
        """Ekstraktuje cały tekst z PDF"""
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text

    def _extract_tables(self, pdf) -> List[List[List[str]]]:
        """Ekstraktuje wszystkie tabele z PDF"""
        all_tables = []
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
        return all_tables

    def _clean_number(self, value: str) -> float:
        """Czyści i konwertuje string na liczbę"""
        if not value:
            return 0.0

        # Usuń spacje i zamień przecinek na kropkę
        value = str(value).strip().replace(' ', '').replace(',', '.')

        # Usuń znaki waluty i inne
        value = re.sub(r'[^\d.-]', '', value)

        try:
            return float(value)
        except (ValueError, AttributeError):
            return 0.0

    def _categorize_item(self, item_name: str) -> str:
        """Kategoryzuje pozycję faktury"""
        item_lower = item_name.lower()

        for category, keywords in self.categories_mapping.items():
            for keyword in keywords:
                if keyword in item_lower:
                    return category

        return 'dystrybucja'  # Domyślnie dystrybucja

    def _parse_invoice_data(self, text: str, tables: List) -> Dict:
        """Parsuje dane z faktury"""
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

        # Parsuj metadane
        result.update(self._parse_metadata(text))

        # Parsuj pozycje z tabel
        pozycje = self._parse_items_from_tables(tables, text)
        if pozycje:
            result['pozycje'] = pozycje

        # Parsuj sumy
        result.update(self._parse_totals(text, tables))

        # Parsuj zużycie
        zuzycie = self._parse_consumption(text, tables)
        if zuzycie > 0:
            result['zuzycie_kwh'] = zuzycie

        return result

    def _parse_metadata(self, text: str) -> Dict:
        """Parsuje metadane faktury"""
        metadata = {}

        # Numer faktury
        patterns = [
            r'Faktura\s+VAT\s+nr\s+(\d+)',
            r'Faktura\s+nr\s+(\d+)',
            r'Nr\s+faktury:?\s*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['numer_faktury'] = match.group(1)
                break

        # Data faktury
        patterns = [
            r'z\s+dnia\s+(\d{2}\.\d{2}\.\d{4})',
            r'Data\s+faktury:?\s*(\d{2}\.\d{2}\.\d{4})',
            r'Data\s+wystawienia:?\s*(\d{2}\.\d{2}\.\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                metadata['data_faktury'] = match.group(1)
                break

        # Okres rozliczeniowy
        patterns = [
            r'w\s+okresie\s+od\s+(\d{2}\.\d{2}\.\d{4})\s+do\s+(\d{2}\.\d{2}\.\d{4})',
            r'za\s+okres\s+od\s+(\d{2}\.\d{2}\.\d{4})\s+do\s+(\d{2}\.\d{2}\.\d{4})',
            r'okres:?\s*(\d{2}\.\d{2}\.\d{4})\s*[-–]\s*(\d{2}\.\d{2}\.\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['okres_rozliczeniowy'] = f"{match.group(1)} - {match.group(2)}"
                break

        return metadata

    def _parse_items_from_tables(self, tables: List, text: str) -> List[Dict]:
        """Parsuje pozycje z tabel i tekstu"""
        items = []

        # Parsuj pozycje z tekstu (E.ON format)
        items_from_text = self._parse_items_from_text(text)
        if items_from_text:
            return items_from_text

        # Fallback: parsuj z tabel
        for table in tables:
            if not table:
                continue

            # Znajdź nagłówek tabeli
            header_idx = None
            for idx, row in enumerate(table):
                if row and any('pozycja' in str(cell).lower() for cell in row if cell):
                    header_idx = idx
                    break

            if header_idx is None:
                continue

            # Znajdź indeksy kolumn
            header = table[header_idx]
            col_pozycja = self._find_column_index(header, ['pozycja', 'opis'])
            col_netto = self._find_column_index(header, ['netto', 'wartość netto'])
            col_brutto = self._find_column_index(header, ['brutto', 'wartość brutto'])

            # Parsuj wiersze
            for row in table[header_idx + 1:]:
                if not row or len(row) < 2:
                    continue

                nazwa = str(row[col_pozycja] if col_pozycja is not None else row[0] or "").strip()

                # Pomijaj puste wiersze i wiersze z sumami
                if not nazwa or any(keyword in nazwa.lower() for keyword in ['razem', 'suma', 'należność', 'wartość prognozowana']):
                    continue

                # Pobierz wartość netto
                netto_val = 0.0
                if col_netto is not None and col_netto < len(row):
                    netto_val = self._clean_number(row[col_netto])
                elif col_brutto is not None and col_brutto < len(row):
                    # Jeśli nie ma netto, użyj brutto i podziel przez 1.23
                    brutto_val = self._clean_number(row[col_brutto])
                    netto_val = brutto_val / 1.23

                if netto_val > 0:
                    items.append({
                        'nazwa': nazwa,
                        'wartosc_netto': round(netto_val, 2),
                        'kategoria': self._categorize_item(nazwa)
                    })

        return items

    def _parse_items_from_text(self, text: str) -> List[Dict]:
        """Parsuje pozycje szczegółowe z tekstu (format E.ON)"""
        items = []
        lines = text.split('\n')

        # Szukaj sekcji "Sprzedaż energii elektrycznej"
        in_sprzedaz = False
        in_dystrybucja = False

        for i, line in enumerate(lines):
            # Wykryj sekcje
            if 'Sprzedaż energii elektrycznej' in line:
                in_sprzedaz = True
                in_dystrybucja = False
                continue
            elif 'Dystrybucja energii elektrycznej' in line:
                in_sprzedaz = False
                in_dystrybucja = True
                continue
            elif 'Sprzedaż i dystrybucja energii elektrycznej' in line or 'Razem' in line:
                # Koniec sekcji szczegółowych
                in_sprzedaz = False
                in_dystrybucja = False
                continue

            # Parsuj linie w sekcjach
            if (in_sprzedaz or in_dystrybucja):
                # Szukaj pozycji z wartościami
                # Format: Nazwa okresu ilość cena netto stawka vat brutto

                # Wykryj linie z pozycjami (zawierają nazwę i wartości)
                if any(keyword in line for keyword in ['Energia czynna', 'Opłata']):
                    # Wyciągnij wartość netto (przedostatnia liczba przed VAT)
                    numbers = re.findall(r'\d+[,.]?\d*', line)
                    if len(numbers) >= 4:  # ilość, cena, wartość_netto, stawka_vat, vat, brutto
                        # Znajdź nazwę pozycji
                        match = re.match(r'^([A-Za-zęóąśłżźćńĘÓĄŚŁŻŹĆŃ\s]+)', line)
                        if match:
                            nazwa = match.group(1).strip()

                            # Wartość netto to trzecia liczba od końca (brutto, vat, netto)
                            # lub czwarta jeśli mamy stawkę VAT
                            try:
                                # Konwertuj liczby
                                clean_numbers = [self._clean_number(n) for n in numbers]

                                # Typowa struktura: ilość, cena, netto, vat_%, vat_kwota, brutto
                                if len(clean_numbers) >= 6:
                                    netto_val = clean_numbers[-4]  # Wartość netto
                                elif len(clean_numbers) >= 3:
                                    netto_val = clean_numbers[-3]  # Fallback
                                else:
                                    continue

                                if netto_val > 0:
                                    kategoria = 'sprzedaz' if in_sprzedaz else 'dystrybucja'
                                    items.append({
                                        'nazwa': nazwa,
                                        'wartosc_netto': round(netto_val, 2),
                                        'kategoria': kategoria
                                    })
                            except (IndexError, ValueError):
                                continue

        return items

    def _find_column_index(self, header: List, keywords: List[str]) -> Optional[int]:
        """Znajduje indeks kolumny po słowach kluczowych"""
        for idx, cell in enumerate(header):
            if not cell:
                continue
            cell_lower = str(cell).lower()
            for keyword in keywords:
                if keyword in cell_lower:
                    return idx
        return None

    def _parse_totals(self, text: str, tables: List) -> Dict:
        """Parsuje sumy z faktury"""
        totals = {}

        # Szukaj wartości netto
        patterns = [
            r'Należność za faktyczne zużycie\s+([\d,]+)\s+\d+\s+([\d,]+)\s+([\d,]+)',
            r'Suma\s+netto:?\s*([\d,]+)',
            r'Razem\s+netto:?\s*([\d,]+)',
        ]

        # Najpierw szukaj w szczegółowym wzorze (E.ON)
        match = re.search(r'Należność za faktyczne zużycie\s+([\d,]+)\s+\d+\s+([\d,]+)\s+([\d,]+)', text)
        if match:
            netto = self._clean_number(match.group(1))
            vat = self._clean_number(match.group(2))
            brutto = self._clean_number(match.group(3))

            totals['suma_netto'] = netto
            totals['vat_kwota'] = vat
            totals['suma_brutto'] = brutto
            totals['vat_procent'] = 23

            return totals

        # Alternatywnie szukaj w tabelach
        for table in tables:
            if not table:
                continue

            for row in table:
                if not row:
                    continue

                row_text = ' '.join([str(cell) for cell in row if cell])

                # Szukaj wiersza z sumami
                if any(keyword in row_text.lower() for keyword in ['razem', 'suma', 'do zapłaty']):
                    # Próbuj wyciągnąć liczby
                    numbers = re.findall(r'[\d,]+[.,]?\d*', row_text)
                    numbers = [self._clean_number(n) for n in numbers if self._clean_number(n) > 0]

                    if len(numbers) >= 3:
                        # Zakładamy: netto, vat, brutto
                        totals['suma_netto'] = numbers[-3]
                        totals['vat_kwota'] = numbers[-2]
                        totals['suma_brutto'] = numbers[-1]
                        totals['vat_procent'] = 23
                        break

        return totals

    def _parse_consumption(self, text: str, tables: List) -> float:
        """Parsuje zużycie energii w kWh"""

        # Szukaj w tekście
        patterns = [
            r'Zużycie:?\s*(\d+)\s*kWh',
            r'(\d+)\s*kWh',
            r'Energia\s+czynna.*?(\d+)\s*kWh',
            r'Razem\s+energia.*?(\d+)\s*kWh',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                consumption = self._clean_number(match.group(1))
                if 50 <= consumption <= 100000:  # Sensowny zakres
                    return consumption

        # Szukaj w tabelach
        for table in tables:
            if not table:
                continue

            for row in table:
                if not row:
                    continue

                for cell in row:
                    if cell and 'kWh' in str(cell):
                        match = re.search(r'(\d+)\s*kWh', str(cell))
                        if match:
                            consumption = self._clean_number(match.group(1))
                            if 50 <= consumption <= 100000:
                                return consumption

        return 0.0


def parse_invoice(filepath: str) -> Dict:
    """Funkcja pomocnicza do parsowania faktury"""
    parser = InvoiceParser()
    return parser.parse_pdf(filepath)


# Test
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        result = parse_invoice(filepath)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Użycie: python3 parser_advanced.py <ścieżka_do_faktury.pdf>")
