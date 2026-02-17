"""
Zaawansowany parser faktur za energię elektryczną
Wykorzystuje pdfplumber do ekstrakcji tabel i strukturyzowanych danych
Obsługuje dostawców: E.ON, PGE, TAURON, Lumi PGE (i podobne formaty)
Rozróżnia typ dokumentu: faktura rozliczeniowa vs prognoza
"""
import re
import pdfplumber
from typing import Dict, List, Optional
from decimal import Decimal


class InvoiceParser:
    """Parser faktur za energię elektryczną"""

    # Typy dokumentów
    DOC_TYPE_INVOICE = 'faktura_rozliczeniowa'
    DOC_TYPE_FORECAST = 'prognoza'
    DOC_TYPE_UNKNOWN = 'nieznany'

    def __init__(self):
        self.categories_mapping = {
            'sprzedaz': [
                'energia czynna',
                'sprzedaż energii',
                'sprzedaży energii',
                'opłata handlowa',
                'energia elektryczna',
                'opł.za energię',
            ],
            'dystrybucja': [
                'dystrybucja',
                'świadczonych usług dystrybucji',
                'sieciowa',
                'jakościowa',
                'mocowa',
                'oze',
                'kogeneracja',
                'kogeneracyjna',
                'przejściowa',
                'abonamentowa',
                'opłata stała',
                'opł.stała',
                'składnik stały',
                'składnik zmienny',
                'stawka jakościowa',
                'stawka opłaty',
                'opł.sieciowa',
                'opł.jakościowa',
                'opł. moc',
            ]
        }

    def parse_pdf(self, filepath: str) -> Dict:
        """Główna metoda parsowania PDF"""
        with pdfplumber.open(filepath) as pdf:
            # Ekstraktuj tekst
            text = self._extract_text(pdf)

            # Ekstraktuj tabele
            tables = self._extract_tables(pdf)

            # Sprawdź czy tekst ma podwojone znaki (TAURON)
            needs_dedup = self._is_text_duplicated(text)
            if needs_dedup:
                text = self._dedup_text(text)
                tables = self._dedup_tables(tables)

            # Wykryj dostawcę
            provider = self._detect_provider(text)

            # Wykryj typ dokumentu (faktura vs prognoza)
            doc_type = self._detect_document_type(text, provider)

            if doc_type == self.DOC_TYPE_FORECAST:
                # Prognoza: wyciągnij podstawowe dane i zwróć informację
                result = self._parse_forecast(text, tables, provider)
                result['typ_dokumentu'] = self.DOC_TYPE_FORECAST
                return result
            else:
                # Faktura rozliczeniowa: pełne parsowanie
                result = self._parse_invoice_data(text, tables, provider)
                result['typ_dokumentu'] = self.DOC_TYPE_INVOICE
                return result

    def _detect_document_type(self, text: str, provider: str) -> str:
        """Rozpoznaje typ dokumentu: faktura rozliczeniowa vs prognoza"""
        text_lower = text.lower()

        # Wzorce jednoznacznie wskazujące na PROGNOZĘ
        forecast_indicators = [
            'prognoza zużycia',
            'szczegóły prognozy',
            'dokument prognozowy',
            'numer dokumentu prognozowego',
            'prognoza/ee/',
            'przewidywana należność',
            'prognoza zużycia za okres',
        ]

        # Wzorce jednoznacznie wskazujące na FAKTURĘ ROZLICZENIOWĄ
        invoice_indicators = [
            'faktura vat',
            'szczegółowe rozliczenie zużycia',
            'rozliczenie za okres',
            'nr licznika',
            'wskazanie',
            'data odczytu',
            'typ odczytu',
            'odczyt rzeczywisty',
        ]

        # Lumi PGE: "Podsumowanie" + "Prognoza zużycia energii" = prognoza
        if provider == 'lumi_pge':
            if any(kw in text_lower for kw in ['prognoza zużycia energii', 'prognoza/ee/']):
                return self.DOC_TYPE_FORECAST

        forecast_score = sum(1 for kw in forecast_indicators if kw in text_lower)
        invoice_score = sum(1 for kw in invoice_indicators if kw in text_lower)

        if forecast_score > invoice_score:
            return self.DOC_TYPE_FORECAST
        elif invoice_score > 0:
            return self.DOC_TYPE_INVOICE
        else:
            return self.DOC_TYPE_UNKNOWN

    def _parse_forecast(self, text: str, tables: List, provider: str) -> Dict:
        """Parsuje prognozę — wyciąga podstawowe dane, ale NIE próbuje rozbijać na składniki"""
        result = {
            "sprzedawca": provider,
            "numer_faktury": "",
            "numer_dokumentu_prognozowego": "",
            "data_faktury": "",
            "okres_rozliczeniowy": "",
            "zuzycie_kwh": 0,
            "pozycje": [],
            "suma_netto": 0,
            "vat_procent": 23,
            "vat_kwota": 0,
            "suma_brutto": 0,
            "numer_klienta": "",
            "uwaga": "To jest prognoza, nie faktura rozliczeniowa. "
                      "Prognoza nie zawiera szczegółowego rozbicia na składniki. "
                      "Aby uzyskać pełną analizę oszczędności, prześlij fakturę rozliczeniową z pełnym rozbiciem."
        }

        text_lower = text.lower()

        # Numer dokumentu prognozowego (Lumi PGE: "Prognoza/EE/15539487/26/01/1")
        match = re.search(r'(Prognoza/EE/[\d/]+)', text, re.IGNORECASE)
        if match:
            result['numer_dokumentu_prognozowego'] = match.group(1)

        # Numer klienta
        match = re.search(r'(?:Tw[oó]j\s+numer\s+Klienta|nr\s+Klienta|IDENTYFIKATOR\s+KLIENTA):?\s*(\d+)', text, re.IGNORECASE)
        if match:
            result['numer_klienta'] = match.group(1)

        # Okres prognozy (Lumi: "Prognoza zużycia za okres:\n...\n01.01.2026 - 31.01.2026")
        # Data może być na innej linii niż nagłówek
        date_pattern = r'\d{2}[./]\d{2}[./]\d{4}'
        match = re.search(rf'Prognoza\s+zużycia\s+za\s+okres:?\s*\n.*?\n?\s*({date_pattern})\s*[-–]\s*({date_pattern})', text, re.IGNORECASE)
        if match:
            result['okres_rozliczeniowy'] = f"{match.group(1)} - {match.group(2)}"
        else:
            # Generyczny fallback
            patterns = [
                rf'za\s+okres\s+od\s+({date_pattern})\s+do\s+({date_pattern})',
                rf'okres:?\s*({date_pattern})\s*[-–]\s*({date_pattern})',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result['okres_rozliczeniowy'] = f"{match.group(1)} - {match.group(2)}"
                    break

        # Kwoty z prognozy (Lumi: tabela ze Sprzedaż/Dystrybucja)
        # Szukaj "Sprzedaż energii elektrycznej" + kwoty
        sprzedaz_match = re.search(r'Sprzedaż\s+energii\s+elektrycznej\s+(\d+)\s+([\d,]+)\s+\d+%?\s+([\d,]+)', text)
        dystrybucja_match = re.search(r'Dystrybucja\s+energii\s+elektrycznej\s+(\d+)\s+([\d,]+)\s+\d+%?\s+([\d,]+)', text)

        if sprzedaz_match:
            zuzycie = self._clean_number(sprzedaz_match.group(1))
            netto = self._clean_number(sprzedaz_match.group(2))
            brutto = self._clean_number(sprzedaz_match.group(3))
            result['pozycje'].append({
                'nazwa': 'Sprzedaż energii elektrycznej (prognoza)',
                'wartosc_netto': round(netto, 2),
                'kategoria': 'sprzedaz'
            })
            if zuzycie > 0:
                result['zuzycie_kwh'] = zuzycie

        if dystrybucja_match:
            netto = self._clean_number(dystrybucja_match.group(2))
            brutto = self._clean_number(dystrybucja_match.group(3))
            result['pozycje'].append({
                'nazwa': 'Dystrybucja energii elektrycznej (prognoza)',
                'wartosc_netto': round(netto, 2),
                'kategoria': 'dystrybucja'
            })

        # Suma — "Razem" lub "Do zapłaty"
        match = re.search(r'Razem\s+([\d,]+)\s+([\d,]+)', text)
        if match:
            result['suma_netto'] = self._clean_number(match.group(1))
            result['suma_brutto'] = self._clean_number(match.group(2))
            result['vat_kwota'] = round(result['suma_brutto'] - result['suma_netto'], 2)

        # Fallback: "Do zapłaty" / "Ile powinieneś zapłacić"
        if result['suma_brutto'] == 0:
            match = re.search(r'(?:Do\s+zapłaty|Ile\s+powinieneś\s+zapłacić\??)\s*([\d.,]+)\s*zł', text, re.IGNORECASE)
            if match:
                result['suma_brutto'] = self._clean_number(match.group(1))

        # Numer faktury rozliczeniowej, na którą powołuje się prognoza
        match = re.search(r'poprzedniej\s+faktury\s+(\w+)', text, re.IGNORECASE)
        if match:
            result['numer_faktury_rozliczeniowej'] = match.group(1)

        return result

    def _dedup_tables(self, tables: List) -> List:
        """Deduplikuje podwojone znaki we wszystkich tabelach"""
        deduped = []
        for table in tables:
            new_table = []
            for row in table:
                if row is None:
                    new_table.append(row)
                    continue
                new_row = []
                for cell in row:
                    if cell is None:
                        new_row.append(cell)
                    else:
                        new_row.append(self._dedup_text(str(cell)))
                new_table.append(new_row)
            deduped.append(new_table)
        return deduped

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

    def _detect_provider(self, text: str) -> str:
        """Wykrywa dostawcę energii na podstawie tekstu faktury"""
        text_lower = text.lower()
        # Lumi PGE musi być sprawdzane PRZED PGE (bo zawiera "PGE Obrót" w danych)
        if 'lumi' in text_lower and ('lumipge' in text_lower or 'lumi' in text_lower):
            return 'lumi_pge'
        elif 'pge obrót' in text_lower or 'gkpge.pl' in text_lower or 'pge-obrot' in text_lower:
            return 'pge'
        elif 'tauron' in text_lower or 'ttaauurroonn' in text_lower:
            return 'tauron'
        elif 'e.on' in text_lower or 'eon energie' in text_lower:
            return 'eon'
        elif 'enea' in text_lower:
            return 'enea'
        elif 'energa' in text_lower:
            return 'energa'
        return 'unknown'

    def _dedup_text(self, text: str) -> str:
        """Deduplikuje podwojone znaki (specyfika niektórych PDF TAURON).
        Np. 'TTaauurroonn' → 'Tauron', '110088,,5577' → '108,57'
        """
        if not text:
            return text
        result = []
        i = 0
        while i < len(text):
            ch = text[i]
            # Sprawdź czy następny znak jest taki sam (podwojenie)
            if i + 1 < len(text) and text[i + 1] == ch:
                result.append(ch)
                i += 2  # Przeskocz podwojony
            else:
                result.append(ch)
                i += 1
        return ''.join(result)

    def _is_text_duplicated(self, text: str) -> bool:
        """Sprawdza czy tekst ma podwojone znaki (heurystyka)"""
        # Szukaj charakterystycznych podwojonych wzorców
        test_patterns = ['TTaauurroonn', 'ffaakkttuurraa', 'eenneerrgg', 'DDoo zzaappłłaattyy',
                         'SSpprrzzee', 'DDyyssttrryy']
        text_lower = text.lower()
        matches = sum(1 for p in test_patterns if p.lower() in text_lower)
        return matches >= 2

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

    def _clean_consumption_number(self, value: str) -> float:
        """Czyści liczbę zużycia kWh — obsługuje separator tysięcy z kropką (np. 2.359 = 2359)"""
        if not value:
            return 0.0
        value = str(value).strip().replace(' ', '')
        # Jeśli ma format X.XXX (separator tysięcy), usuń kropkę
        if re.match(r'^\d{1,3}\.\d{3}$', value):
            value = value.replace('.', '')
        else:
            value = value.replace(',', '.')
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

    def _parse_invoice_data(self, text: str, tables: List, provider: str) -> Dict:
        """Parsuje dane z faktury"""
        result = {
            "sprzedawca": provider,
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
        result.update(self._parse_metadata(text, provider))
        # Zachowaj sprzedawcę
        result['sprzedawca'] = provider

        # Parsuj pozycje
        pozycje = self._parse_items(tables, text, provider)
        if pozycje:
            result['pozycje'] = pozycje

        # Parsuj sumy
        result.update(self._parse_totals(text, tables, provider))
        result['sprzedawca'] = provider

        # Parsuj zużycie
        zuzycie = self._parse_consumption(text, tables, provider)
        if zuzycie > 0:
            result['zuzycie_kwh'] = zuzycie

        return result

    def _parse_metadata(self, text: str, provider: str) -> Dict:
        """Parsuje metadane faktury"""
        metadata = {}

        # TAURON: specjalny format — nagłówki i wartości w sąsiednich liniach
        # "Data wystawienia Numer faktury Okres rozliczeniowy"
        # "14/01/2026 E/TM2/UG541227/0002/26 04/12/2025 - 07/01/2026"
        if provider == 'tauron':
            tauron_meta = self._parse_metadata_tauron(text)
            if tauron_meta:
                return tauron_meta

        # ENEA: "FAKTURA VAT NR P/24281058/0001/26 - ORYGINAŁ"
        if provider == 'enea':
            enea_meta = self._parse_metadata_enea(text)
            if enea_meta:
                return enea_meta

        # Numer faktury
        patterns = [
            # PGE: FAKTURA VAT NR  81304134/97R/2025
            r'FAKTURA\s+VAT\s+NR\s+([\w/]+)',
            # Generyczny: Numer faktury\nXXX
            r'Numer\s+faktury\s*\n\s*([\w/.-]+)',
            # E.ON / generyczne
            r'Faktura\s+VAT\s+nr\s+([\w/.-]+)',
            r'Faktura\s+nr\s+([\w/.-]+)',
            r'Nr\s+faktury:?\s*([\w/.-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['numer_faktury'] = match.group(1).strip()
                break

        # Data faktury — obsługa DD.MM.YYYY i DD/MM/YYYY
        date_pattern = r'\d{2}[./]\d{2}[./]\d{4}'
        patterns = [
            rf'[Zz]\s+dnia\s+({date_pattern})',
            rf'Data\s+wystawienia\s*\n?\s*({date_pattern})',
            rf'Data\s+faktury:?\s*({date_pattern})',
            rf'Data\s+wystawienia:?\s*({date_pattern})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                metadata['data_faktury'] = match.group(1)
                break

        # Okres rozliczeniowy — obsługa DD.MM.YYYY i DD/MM/YYYY
        patterns = [
            rf'w\s+okresie\s+od\s+({date_pattern})\s+do\s+({date_pattern})',
            rf'za\s+okres\s+od\s+({date_pattern})\s+do\s+({date_pattern})',
            rf'Okres\s+rozliczeniowy\s*\n?\s*({date_pattern})\s*[-–]\s*({date_pattern})',
            rf'okres:?\s*({date_pattern})\s*[-–]\s*({date_pattern})',
            rf'Rozliczenie\s+za\s+okres\s+od\s+({date_pattern})\s+do\s+({date_pattern})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['okres_rozliczeniowy'] = f"{match.group(1)} - {match.group(2)}"
                break

        return metadata

    def _parse_metadata_tauron(self, text: str) -> Optional[Dict]:
        """Parsuje metadane z faktury TAURON — specjalny format."""
        metadata = {}
        lines = text.split('\n')

        for i, line in enumerate(lines):
            # Szukaj linii z nagłówkami TAURON
            if 'Data wystawienia' in line and 'Numer faktury' in line:
                # Następna linia powinna zawierać wartości
                if i + 1 < len(lines):
                    values_line = lines[i + 1].strip()
                    # Format: "14/01/2026 E/TM2/UG541227/0002/26 04/12/2025 - 07/01/2026"
                    date_pattern = r'\d{2}/\d{2}/\d{4}'
                    # Data wystawienia — pierwsza data
                    match = re.match(rf'({date_pattern})\s+', values_line)
                    if match:
                        metadata['data_faktury'] = match.group(1)

                    # Numer faktury — po dacie, przed okresem
                    match = re.search(rf'{date_pattern}\s+([\w/.-]+)\s+{date_pattern}', values_line)
                    if match:
                        metadata['numer_faktury'] = match.group(1)

                    # Okres rozliczeniowy — dwie ostatnie daty
                    match = re.search(rf'({date_pattern})\s*[-–]\s*({date_pattern})', values_line)
                    if match:
                        metadata['okres_rozliczeniowy'] = f"{match.group(1)} - {match.group(2)}"

                    if metadata:
                        return metadata

        # Fallback: szukaj numeru faktury TAURON w osobnych liniach
        for i, line in enumerate(lines):
            if line.strip().startswith('E/') and '/' in line and len(line.strip()) < 40:
                metadata.setdefault('numer_faktury', line.strip())
                break

        return metadata if metadata else None

    def _parse_metadata_enea(self, text: str) -> Optional[Dict]:
        """Parsuje metadane z faktury ENEA.
        Format: 'FAKTURA VAT NR P/24281058/0001/26 - ORYGINAŁ'
        Data sprzedaży: 24/01/2026
        Data wystawienia: 26/01/2026
        Za okres od 24/12/2025 do 24/01/2026 (na str. 2)
        """
        metadata = {}
        date_pattern = r'\d{2}/\d{2}/\d{4}'

        # Numer faktury ENEA: P/XXXXXXXX/XXXX/XX
        match = re.search(r'FAKTURA\s+VAT\s+NR\s+(P/[\w/]+)\s*[-–]', text, re.IGNORECASE)
        if match:
            metadata['numer_faktury'] = match.group(1).strip()

        # Data wystawienia
        match = re.search(rf'Data\s+wystawienia:?\s*({date_pattern})', text, re.IGNORECASE)
        if match:
            metadata['data_faktury'] = match.group(1)

        # Okres rozliczeniowy — na str. 2: "Za okres od 24/12/2025 do 24/01/2026"
        match = re.search(rf'[Zz]a\s+okres\s+od\s+({date_pattern})\s+do\s+({date_pattern})', text)
        if match:
            metadata['okres_rozliczeniowy'] = f"{match.group(1)} - {match.group(2)}"

        return metadata if metadata else None

    def _parse_items(self, tables: List, text: str, provider: str) -> List[Dict]:
        """Parsuje pozycje faktury — dispatcher wg dostawcy"""
        if provider == 'pge':
            return self._parse_items_pge(tables, text)
        elif provider == 'lumi_pge':
            # Lumi PGE faktury rozliczeniowe mają format zbliżony do PGE
            return self._parse_items_pge(tables, text)
        elif provider == 'tauron':
            return self._parse_items_tauron(tables, text)
        elif provider == 'enea':
            return self._parse_items_enea(tables, text)
        else:
            return self._parse_items_generic(tables, text)

    def _parse_items_pge(self, tables: List, text: str) -> List[Dict]:
        """Parsuje pozycje z faktury PGE — szczegółowe tabele z wieloma strefami/licznikami.
        PGE pakuje wszystkie pozycje w jedną wieloliniową komórkę — trzeba je rozdzielić po \\n."""
        aggregated = {}  # nazwa -> {'netto': float, 'kategoria': str}

        for table in tables:
            if not table:
                continue

            # Szukaj tabeli ze szczegółami (kolumny: Strefa, Opis, ..., Wartość netto, Stawka VAT)
            header_idx = None
            for idx, row in enumerate(table):
                if not row:
                    continue
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if 'opis' in row_text and ('wartość' in row_text or 'netto' in row_text):
                    header_idx = idx
                    break

            if header_idx is None:
                continue

            header = table[header_idx]
            col_opis = self._find_column_index(header, ['opis'])
            col_netto = self._find_column_index(header, ['wartość\nnetto', 'wartość netto'])

            if col_opis is None or col_netto is None:
                continue

            # PGE: dane są w wieloliniowych komórkach — rozdziel po \n
            for row in table[header_idx + 1:]:
                if not row or len(row) <= max(col_opis, col_netto):
                    continue

                # Pomiń wiersze podnagłówkowe (bieżące/poprzednie)
                opis_raw = str(row[col_opis] or "")
                if not opis_raw or opis_raw.startswith('bieżące'):
                    continue

                netto_raw = str(row[col_netto] or "")

                # Rozdziel wieloliniowe dane
                opisy = opis_raw.split('\n')
                netto_vals = netto_raw.split('\n')

                for i, opis in enumerate(opisy):
                    opis = opis.strip()
                    if not opis:
                        continue

                    # Pobierz odpowiadającą wartość netto
                    netto_val = 0.0
                    if i < len(netto_vals):
                        netto_val = self._clean_number(netto_vals[i])

                    if netto_val <= 0:
                        continue

                    # Pomiń sumy
                    opis_lower = opis.lower()
                    if any(kw in opis_lower for kw in ['razem', 'suma', 'należność', 'wartość ogółem']):
                        continue

                    norm_name = self._normalize_item_name(opis)
                    kategoria = self._categorize_item(opis)

                    if norm_name in aggregated:
                        aggregated[norm_name]['netto'] += netto_val
                    else:
                        aggregated[norm_name] = {
                            'netto': netto_val,
                            'kategoria': kategoria
                        }

        # Konwertuj do listy
        items = []
        for nazwa, data in aggregated.items():
            items.append({
                'nazwa': nazwa,
                'wartosc_netto': round(data['netto'], 2),
                'kategoria': data['kategoria']
            })

        return items

    def _parse_items_tauron(self, tables: List, text: str) -> List[Dict]:
        """Parsuje pozycje z faktury TAURON.
        TAURON pakuje dane pozycji w wieloliniowe komórki w tabeli, np.:
        Row[0] = nagłówek "Nazwa"
        Row[1] = "Energia elektryczna czynna\\ncałodobowa 70 kWh 0,50500 35,35 23 8,13 43,48\\n..."
        Row[2] = "Razem za sprzedaż energii"
        """
        aggregated = {}  # nazwa -> {'netto': float, 'kategoria': str}
        current_section = None

        for table in tables:
            if not table:
                continue

            for row in table:
                if not row:
                    continue

                row_text = ' '.join([str(cell) for cell in row if cell])
                row_lower = row_text.lower()

                # Pomiń nagłówki
                if 'nazwa' in row_lower and ('netto' in row_lower or 'wartość' in row_lower or 'jednostka' in row_lower):
                    continue

                # Wykryj sumy sekcji — wskazują na sekcję
                if 'razem za sprzedaż' in row_lower:
                    current_section = 'sprzedaz'
                    continue
                elif 'razem za dystrybucję' in row_lower:
                    current_section = 'dystrybucja'
                    continue

                # Sprawdź pierwszą komórkę — zawiera dane wieloliniowe
                cell0 = str(row[0] or "").strip()
                if not cell0 or len(cell0) < 5:
                    continue

                # Heurystyka: jeśli zawiera kilka \n i liczby — to komórka z danymi pozycji
                lines = cell0.split('\n')
                if len(lines) < 2:
                    continue

                # Określ sekcję na podstawie kontekstu tabel
                cell_lower = cell0.lower()

                # Odfiltruj tabelę odczytów licznika (zawiera "nr Z..." lub "Licznik energii")
                if any(kw in cell_lower for kw in ['licznik energii', 'nr z1', 'nr z2', 'typ odczytu']):
                    continue

                # Sprawdź zawartość — czy zawiera nazwy z kategorii sprzedaż?
                if 'energia' in cell_lower and ('czynna' in cell_lower or 'elektryczna' in cell_lower):
                    section = 'sprzedaz'
                elif any(kw in cell_lower for kw in ['składnik', 'stawka', 'opłata oze', 'kogeneracyjna',
                                                      'abonamentow', 'mocowa']):
                    section = 'dystrybucja'
                elif current_section:
                    section = current_section
                else:
                    section = 'dystrybucja'

                # Parsuj wieloliniowe dane
                # Format linii: "nazwa ilość jednostka cena wartość_netto vat% kwota_vat wartość_brutto"
                # lub: "całodobowa 70 kWh 0,50500 35,35 23 8,13 43,48"
                # Albo linia z samą nazwą: "Energia elektryczna czynna" (nagłówek podgrupy)
                current_subname = None
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Wyciągnij liczby z linii
                    numbers = re.findall(r'[\d]+[,.][\d]+', line)

                    if len(numbers) >= 3:
                        # Linia z danymi — wyciągnij wartość netto
                        # Format: "całodobowa 70 kWh 0,50500 35,35 23 8,13 43,48"
                        # lub: "Składnik stały stawki sieciowej 1 mc 7,38000 7,38 23 1,70 9,08"
                        # Wartość netto to typowo 2. liczba zmiennoprzecinkowa (po cenie)
                        # Najlepiej: szukaj po wzorcu cena→netto→vat%→vat_kwota→brutto

                        # Wyciągnij nazwę (tekst przed pierwszą liczbą)
                        name_match = re.match(r'^([A-Za-zęóąśłżźćńĘÓĄŚŁŻŹĆŃ\s./]+)', line)
                        line_name = name_match.group(1).strip() if name_match else ""

                        # Użyj bieżącej podgrupy jeśli linia zaczyna się od "całodobowa", "dzienna", "nocna"
                        if line_name.lower() in ('całodobowa', 'dzienna', 'nocna', ''):
                            display_name = current_subname or line_name
                        else:
                            display_name = line_name
                            current_subname = line_name

                        if not display_name:
                            continue

                        # Wartość netto: 2. liczba zmiennoprzecinkowa (indeks 1 w numbers)
                        netto_val = self._clean_number(numbers[1])
                        if netto_val <= 0:
                            continue

                        norm_name = self._normalize_item_name(display_name)
                        kategoria = self._categorize_item(display_name)
                        # Override sekcji jeśli znamy ją z tabeli
                        if section:
                            kategoria = section

                        if norm_name in aggregated:
                            aggregated[norm_name]['netto'] += netto_val
                        else:
                            aggregated[norm_name] = {
                                'netto': netto_val,
                                'kategoria': kategoria
                            }
                    else:
                        # Linia z samą nazwą — nagłówek podgrupy
                        if line and not any(c.isdigit() for c in line):
                            current_subname = line.strip()

        # Konwertuj do listy
        items = [
            {'nazwa': n, 'wartosc_netto': round(d['netto'], 2), 'kategoria': d['kategoria']}
            for n, d in aggregated.items()
        ]

        # Fallback do tekstu jeśli nie znaleziono pozycji
        if not items:
            items = self._parse_items_tauron_text(text)

        return items

    def _parse_items_tauron_text(self, text: str) -> List[Dict]:
        """Parsuje pozycje TAURON z tekstu (fallback gdy tabele nie działają)"""
        items = []
        lines = text.split('\n')
        current_section = None

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Detekcja sekcji
            if 'sprzedaż energii elektrycznej' in line_lower:
                current_section = 'sprzedaz'
                continue
            elif 'dystrybucja energii elektrycznej' in line_lower:
                current_section = 'dystrybucja'
                continue
            elif any(kw in line_lower for kw in ['razem za sprzedaż', 'razem za dystrybucję']):
                # Wyciągnij sumę sekcji z linii "Razem za sprzedaż energii XX,XX YY,YY ZZ,ZZ"
                numbers = re.findall(r'[\d]+[,.][\d]+', line_stripped)
                if numbers and current_section:
                    netto_val = self._clean_number(numbers[0])
                    if netto_val > 0:
                        label = "Sprzedaż energii" if current_section == 'sprzedaz' else "Dystrybucja energii"
                        items.append({
                            'nazwa': label,
                            'wartosc_netto': round(netto_val, 2),
                            'kategoria': current_section
                        })
                current_section = None
                continue

            if not current_section:
                continue

            # Szukaj linii z pozycjami zawierającymi kwoty
            # TAURON format tekstu: "Nazwa kWh cena wartość_netto VAT% kwota_VAT wartość_brutto"
            # lub: "całodobowa 70 kWh 0,50500 35,35 23 8,13 43,48"
            numbers = re.findall(r'[\d]+[,.][\d]+', line_stripped)
            if len(numbers) >= 3:
                # Wyciągnij nazwę (tekst na początku linii)
                match = re.match(r'^([A-Za-zęóąśłżźćńĘÓĄŚŁŻŹĆŃ\s.]+)', line_stripped)
                if match:
                    nazwa = match.group(1).strip()
                    if len(nazwa) >= 3 and not any(kw in nazwa.lower() for kw in ['razem', 'suma', 'do zapłaty']):
                        # Wartość netto — typowo 2. lub 3. liczba zmiennoprzecinkowa
                        netto_val = self._clean_number(numbers[1]) if len(numbers) >= 4 else self._clean_number(numbers[0])
                        if netto_val > 0:
                            items.append({
                                'nazwa': nazwa,
                                'wartosc_netto': round(netto_val, 2),
                                'kategoria': current_section
                            })

        return items

    def _parse_items_enea(self, tables: List, text: str) -> List[Dict]:
        """Parsuje pozycje z faktury ENEA.

        ENEA na str. 2 zawiera dwie sekcje w tekście płaskim:
        - "ROZLICZENIE - SPRZEDAŻ ENERGII"
        - "ROZLICZENIE - USŁUGA DYSTRYBUCJI ENERGII"

        pdfplumber nie tworzy tu użytecznych tabel — parsujemy z tekstu.
        """
        return self._parse_items_enea_text(text)

    def _parse_items_enea_text(self, text: str) -> List[Dict]:
        """Parsuje pozycje ENEA bezpośrednio z tekstu (główna ścieżka).

        ENEA format tekstu (str. 2) — tekst jest płaski, linia po linii:
          ROZLICZENIE - SPRZEDAŻ ENERGII
          Energia elektryczna czynna          <- nazwa pozycji (nagłówek podgrupy)
          całodobowa kWh 115 0,5050 58,08 23  <- dane: strefa j.m. ilość cena netto VAT%
          całodobowa kWh 344 0,5030 173,03 23
          Ogółem wartość - sprzedaż energii: 231,11

          ROZLICZENIE - USŁUGA DYSTRYBUCJI ENERGII
          Opłata stała sieciowa - układ 3-fazowy  <- nazwa pozycji
          zł/mc 31/12/2025 0 10,1400 0,00 23       <- dane: j.m. data ilość cena netto VAT%
          zł/mc 24/01/2026 1 10,4100 10,41 23
          Opłata zmienna sieciowa
          całodobowa kWh 31/12/2025 115 0,2456 28,24 23
          ...

        Reguła ekstrakcji wartości netto:
          Linia danych kończy się: ... <cena_jedn(4 miejsca)> <netto> <VAT%>
          VAT% = liczba całkowita (23). Netto = przedostatnia liczba w linii.
          Wartości 0,00 pomijamy (pozycje bez naliczenia).
        """
        aggregated = {}
        lines = text.split('\n')
        current_section = None
        current_subname = None

        # Słowa kluczowe nagłówków tabel do pominięcia
        header_skip = {
            'opis', 'strefa', 'j. m', 'j.m', 'cena jedn', 'należność', 'stawka vat',
            'tg fi', 'współczynniki', 'ilość m-cy', 'mnożna', 'wskazanie', 'sposób',
            'licznik', 'odczyty', 'ilość\nm-cy',
        }

        # Wzorzec linii danych ENEA:
        # "całodobowa kWh 115 0,5050 58,08 23"
        # "zł/mc 31/12/2025 0 10,1400 0,00 23"
        # "zł/mc 24/01/2026 1 10,4100 10,41 23"
        # "dzienna kWh 12 0,6865 8,24 23"
        data_line_re = re.compile(
            r'^(?:całodobowa|dzienna|nocna|zł/mc)\s',
            re.IGNORECASE
        )

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            if not line_stripped:
                continue

            # Detekcja sekcji
            if 'rozliczenie - sprzedaż energii' in line_lower:
                current_section = 'sprzedaz'
                current_subname = None
                continue
            elif 'rozliczenie - usługa dystrybucji' in line_lower:
                current_section = 'dystrybucja'
                current_subname = None
                continue

            # Koniec sekcji
            if 'ogółem wartość' in line_lower or 'zużycie:' in line_lower:
                current_subname = None
                continue

            if not current_section:
                continue

            # Pomiń nagłówki kolumn
            if any(kw in line_lower for kw in header_skip):
                continue

            # Linia danych (zaczyna się od strefy lub jednostki)
            if data_line_re.match(line_stripped):
                if not current_subname:
                    continue

                # Wyciągnij wszystkie liczby zmiennoprzecinkowe (z przecinkiem)
                numbers_float = re.findall(r'\d+,\d+', line_stripped)
                if not numbers_float:
                    continue

                # Przedostatnia liczba z przecinkiem = należność netto
                # Ostatnia = cena jednostkowa (ma 4 miejsca po przecinku) LUB netto jeśli tylko 1
                # Format: ... <cena_jedn>,<4 cyfry> <netto>,<2 cyfry> <VAT_int>
                # Lub gdy cena jednostkowa i netto są blisko siebie:
                # Sprawdź czy ostatnia liczba wygląda jak cena jednostkowa (>= 4 cyfry po przecinku)
                if len(numbers_float) >= 2:
                    last = numbers_float[-1]
                    second_last = numbers_float[-2]
                    # Cena jedn. ma 4 miejsc po przecinku
                    if re.search(r',\d{4}$', last):
                        # last = cena_jedn, second_last = netto (ale to niemożliwe — cena jest przed netto)
                        netto_val = self._clean_number(second_last)
                    elif re.search(r',\d{4}$', second_last):
                        # second_last = cena_jedn, last = netto
                        netto_val = self._clean_number(last)
                    else:
                        # Standardowo: ostatnia = netto
                        netto_val = self._clean_number(last)
                else:
                    netto_val = self._clean_number(numbers_float[-1])

                if netto_val <= 0:
                    continue

                norm_name = self._normalize_item_name(current_subname)
                if norm_name in aggregated:
                    aggregated[norm_name]['netto'] += netto_val
                else:
                    aggregated[norm_name] = {'netto': netto_val, 'kategoria': current_section}

            elif len(line_stripped) >= 3:
                # Linia nagłówkowa — nazwa pozycji (np. "Energia elektryczna czynna",
                # "Opłata stała sieciowa - układ 3-fazowy", "Opłata mocowa > 2800 kWh")
                # Wyklucz akcyzę i inne informacyjne linie
                if any(kw in line_lower for kw in ['akcyz', 'naliczon', 'informuj', 'wynika', 'str.', 'kod ppe',
                                                    'nr kontrahenta', 'energia zużyta', 'analogiczn', 'licznik',
                                                    'fizyczny', 'wskazanie', 'mnożna']):
                    continue
                # Pomiń linie zaczynające się od daty (DD/MM/YYYY)
                if re.match(r'^\d{2}/\d{2}/\d{4}', line_stripped):
                    continue
                current_subname = line_stripped

        return [
            {'nazwa': n, 'wartosc_netto': round(d['netto'], 2), 'kategoria': d['kategoria']}
            for n, d in aggregated.items()
            if d['netto'] > 0
        ]

    def _parse_items_generic(self, tables: List, text: str) -> List[Dict]:
        """Parsuje pozycje z generycznej faktury (E.ON i inne)"""
        items = []

        # Parsuj pozycje z tekstu (E.ON format)
        items_from_text = self._parse_items_from_text_eon(text)
        if items_from_text:
            return items_from_text

        # Fallback: parsuj z tabel
        for table in tables:
            if not table:
                continue

            # Znajdź nagłówek tabeli
            header_idx = None
            for idx, row in enumerate(table):
                if not row:
                    continue
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if any(kw in row_text for kw in ['pozycja', 'opis', 'nazwa']):
                    if any(kw in row_text for kw in ['netto', 'wartość', 'brutto']):
                        header_idx = idx
                        break

            if header_idx is None:
                continue

            # Znajdź indeksy kolumn
            header = table[header_idx]
            col_pozycja = self._find_column_index(header, ['pozycja', 'opis', 'nazwa', 'rozliczenie z tytułu'])
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
                    brutto_val = self._clean_number(row[col_brutto])
                    netto_val = brutto_val / 1.23

                if netto_val > 0:
                    items.append({
                        'nazwa': nazwa,
                        'wartosc_netto': round(netto_val, 2),
                        'kategoria': self._categorize_item(nazwa)
                    })

        return items

    def _parse_items_from_text_eon(self, text: str) -> List[Dict]:
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
                if any(keyword in line for keyword in ['Energia czynna', 'Opłata']):
                    numbers = re.findall(r'\d+[,.]?\d*', line)
                    if len(numbers) >= 4:
                        match = re.match(r'^([A-Za-zęóąśłżźćńĘÓĄŚŁŻŹĆŃ\s]+)', line)
                        if match:
                            nazwa = match.group(1).strip()
                            try:
                                clean_numbers = [self._clean_number(n) for n in numbers]
                                if len(clean_numbers) >= 6:
                                    netto_val = clean_numbers[-4]
                                elif len(clean_numbers) >= 3:
                                    netto_val = clean_numbers[-3]
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

    def _normalize_item_name(self, name: str) -> str:
        """Normalizuje nazwy pozycji (łączy skróty PGE z pełnymi nazwami)"""
        name = name.strip()
        name_lower = name.lower()

        # Mapowanie skrótów PGE/ENEA na standardowe nazwy
        mappings = [
            (['opł.za energię czynną', 'opł. za energię czynną'], 'Energia czynna'),
            (['opłata kogeneracyjna'], 'Opłata kogeneracyjna'),
            (['opłata oze'], 'Opłata OZE'),
            (['opł.jakościowa', 'opł. jakościowa', 'stawka jakościowa', 'opłata jakościowa'], 'Opłata jakościowa'),
            (['opł.sieciowa zmienna', 'opł. sieciowa zmienna', 'składnik zmienny', 'opłata zmienna sieciowa'], 'Opłata sieciowa zmienna'),
            (['opł.stała staw. sieciowej', 'opł. stała staw. sieciowej', 'składnik stały stawki sieciowej',
              'składnik stały', 'opłata stała sieciowa'], 'Opłata stała sieciowa'),
            (['opłata abonamentowa', 'stawka opłaty abonamentowej'], 'Opłata abonamentowa'),
            (['opłata przejściowa', 'stawka opłaty przejściowej'], 'Opłata przejściowa'),
            (['opł. moc. stała', 'opł.moc. stała', 'opłata mocowa'], 'Opłata mocowa'),
            (['energia elektryczna czynna', 'energia czynna'], 'Energia czynna'),
            (['opłata handlowa'], 'Opłata handlowa'),
        ]

        for variants, canonical in mappings:
            for variant in variants:
                if variant in name_lower:
                    return canonical

        # Jeśli nie znaleziono mapowania, zwróć oryginał z dużej litery
        return name[0].upper() + name[1:] if name else name

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

    def _parse_totals(self, text: str, tables: List, provider: str) -> Dict:
        """Parsuje sumy z faktury"""
        totals = {}

        # E.ON: "Należność za faktyczne zużycie NETTO VAT% VAT BRUTTO"
        match = re.search(r'Należność za faktyczne zużycie\s+([\d,]+)\s+\d+\s+([\d,]+)\s+([\d,]+)', text)
        if match:
            totals['suma_netto'] = self._clean_number(match.group(1))
            totals['vat_kwota'] = self._clean_number(match.group(2))
            totals['suma_brutto'] = self._clean_number(match.group(3))
            totals['vat_procent'] = 23
            return totals

        if provider in ('pge', 'lumi_pge'):
            return self._parse_totals_pge(text, tables)
        elif provider == 'tauron':
            return self._parse_totals_tauron(text, tables)
        elif provider == 'enea':
            return self._parse_totals_enea(text, tables)

        # Generyczny fallback — szukaj w tabelach
        return self._parse_totals_generic(text, tables)

    def _parse_totals_pge(self, text: str, tables: List) -> Dict:
        """Parsuje sumy z faktury PGE"""
        totals = {}

        # Szukaj tabeli "Wartość ogółem w rozbiciu na stawki VAT"
        # Format: [opis, stawka_vat, netto, kwota_vat, brutto]
        for table in tables:
            if not table:
                continue
            for row in table:
                if not row:
                    continue
                row_text = ' '.join([str(cell) for cell in row if cell])
                if 'wartość ogółem' in row_text.lower() and 'rozbiciu' in row_text.lower():
                    # Wyciągnij wartości z komórek
                    numbers = []
                    for cell in row:
                        if cell:
                            val = self._clean_number(str(cell))
                            if val > 0:
                                numbers.append(val)
                    # Format: [23, netto, vat, brutto] lub [netto, vat, brutto]
                    if len(numbers) >= 3:
                        # Ostatnie 3 to netto, vat, brutto
                        totals['suma_netto'] = numbers[-3]
                        totals['vat_kwota'] = numbers[-2]
                        totals['suma_brutto'] = numbers[-1]
                        totals['vat_procent'] = 23
                        return totals

        # Szukaj "Należność za okres" w wieloliniowej komórce tabeli
        for table in tables:
            if not table:
                continue
            for row in table:
                if not row:
                    continue
                # Sprawdź kolumnę "Rozliczenie finansowe ogółem"
                for ci, cell in enumerate(row):
                    if cell and 'należność za okres' in str(cell).lower():
                        # Wartość netto jest w kolumnie z indeksem 2 (wieloliniowa)
                        # Weź pierwszą wartość z kolumny netto
                        netto_col = None
                        vat_col = None
                        brutto_col = None
                        for ci2, cell2 in enumerate(row):
                            if cell2:
                                vals = str(cell2).split('\n')
                                first_val = self._clean_number(vals[0])
                                if first_val > 100:
                                    if netto_col is None:
                                        netto_col = first_val
                                    elif brutto_col is None:
                                        brutto_col = first_val
                        # Szukamy kolumn z VAT
                        for ci2, cell2 in enumerate(row):
                            if cell2:
                                vals = str(cell2).split('\n')
                                first_val = self._clean_number(vals[0])
                                if 0 < first_val < netto_col if netto_col else 0:
                                    if vat_col is None:
                                        vat_col = first_val

        # Fallback: szukaj w tekście "Ogółem: NETTO VAT BRUTTO"
        match = re.search(r'Ogółem:\s*([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', text)
        if match:
            n = self._clean_number(match.group(1))
            v = self._clean_number(match.group(2))
            b = self._clean_number(match.group(3))
            if abs((n + v) - b) < 1.0 and b > 100:
                totals['suma_netto'] = n
                totals['vat_kwota'] = v
                totals['suma_brutto'] = b
                totals['vat_procent'] = 23
                return totals

        # Fallback: zsumuj "Razem wartość netto" z tekstu
        netto_total = 0
        vat_total = 0
        brutto_total = 0
        for match in re.finditer(r'Razem\s+wartość\s+netto\s+([\d.,]+)\s*zł\s*\n\s*plus\s+kwota\s+VAT\s+([\d.,]+)\s*zł\s*\n\s*Razem\s+wartość\s+brutto\s+([\d.,]+)', text):
            netto_total += self._clean_number(match.group(1))
            vat_total += self._clean_number(match.group(2))
            brutto_total += self._clean_number(match.group(3))

        if netto_total > 0:
            totals['suma_netto'] = round(netto_total, 2)
            totals['vat_kwota'] = round(vat_total, 2)
            totals['suma_brutto'] = round(brutto_total, 2)
            totals['vat_procent'] = 23
            return totals

        return self._parse_totals_generic(text, tables)

    def _parse_totals_tauron(self, text: str, tables: List) -> Dict:
        """Parsuje sumy z faktury TAURON"""
        totals = {}

        # TAURON tabela: "Wynik rozliczenia ( 1 + 2 )" lub "Do zapłaty" z kolumnami netto/vat/brutto
        for table in tables:
            if not table:
                continue
            for row in table:
                if not row:
                    continue
                row_text = ' '.join([str(cell) for cell in row if cell])
                row_lower = row_text.lower()

                if 'do zapłaty' in row_lower or 'wynik rozliczenia' in row_lower:
                    numbers = [self._clean_number(str(cell)) for cell in row if cell and self._clean_number(str(cell)) > 0]
                    # Filtruj — szukaj zestawu netto, vat, brutto
                    if len(numbers) >= 3:
                        # Sprawdź czy to netto + vat = brutto (z tolerancją)
                        for i in range(len(numbers) - 2):
                            n, v, b = numbers[i], numbers[i+1], numbers[i+2]
                            if abs((n + v) - b) < 1.0:
                                totals['suma_netto'] = n
                                totals['vat_kwota'] = v
                                totals['suma_brutto'] = b
                                totals['vat_procent'] = 23
                                return totals

        # Fallback: szukaj w tekście
        # TAURON: "Do zapłaty 108,57 24,97 133,54"
        match = re.search(r'Do\s+zapłaty\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', text)
        if match:
            n = self._clean_number(match.group(1))
            v = self._clean_number(match.group(2))
            b = self._clean_number(match.group(3))
            if abs((n + v) - b) < 1.0:
                totals['suma_netto'] = n
                totals['vat_kwota'] = v
                totals['suma_brutto'] = b
                totals['vat_procent'] = 23
                return totals

        return self._parse_totals_generic(text, tables)

    def _parse_totals_enea(self, text: str, tables: List) -> Dict:
        """Parsuje sumy z faktury ENEA.

        ENEA format:
        'Wynik rozliczenia w rozbiciu na stawki VAT:'
        'Wartość netto  Stawka VAT  Kwota VAT  Wartość brutto'
        '401,51         23          92,35       493,86'
        'PODSUMOWANIE: 401,51  92,35  493,86'
        'Do zapłaty: 493,86 zł'
        """
        totals = {}
        date_pattern = r'\d{2}/\d{2}/\d{4}'

        # Metoda 1: szukaj wiersza "PODSUMOWANIE:" w tekście
        match = re.search(
            r'PODSUMOWANIE:\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)',
            text, re.IGNORECASE
        )
        if match:
            n = self._clean_number(match.group(1))
            v = self._clean_number(match.group(2))
            b = self._clean_number(match.group(3))
            if b > 0 and abs((n + v) - b) < 1.0:
                totals['suma_netto'] = n
                totals['vat_kwota'] = v
                totals['suma_brutto'] = b
                totals['vat_procent'] = 23
                return totals

        # Metoda 2: szukaj tabeli "Wynik rozliczenia w rozbiciu na stawki VAT"
        for table in tables:
            if not table:
                continue
            for row in table:
                if not row:
                    continue
                row_text = ' '.join([str(cell) for cell in row if cell])
                row_lower = row_text.lower()
                if 'podsumowanie' in row_lower or 'wynik rozliczenia' in row_lower:
                    numbers = [self._clean_number(str(c)) for c in row if c and self._clean_number(str(c)) > 0]
                    # Szukaj trójki netto+vat=brutto
                    for i in range(len(numbers) - 2):
                        n, v, b = numbers[i], numbers[i + 1], numbers[i + 2]
                        if abs((n + v) - b) < 1.0 and b > 10:
                            totals['suma_netto'] = n
                            totals['vat_kwota'] = v
                            totals['suma_brutto'] = b
                            totals['vat_procent'] = 23
                            return totals

        # Metoda 3: "Do zapłaty: 493,86 zł"
        match = re.search(r'Do\s+zapłaty:\s*([\d,]+)\s*zł', text, re.IGNORECASE)
        if match:
            brutto = self._clean_number(match.group(1))
            if brutto > 0:
                totals['suma_brutto'] = brutto
                totals['suma_netto'] = round(brutto / 1.23, 2)
                totals['vat_kwota'] = round(brutto - totals['suma_netto'], 2)
                totals['vat_procent'] = 23
                return totals

        return self._parse_totals_generic(text, tables)

    def _parse_totals_generic(self, text: str, tables: List) -> Dict:
        """Generyczny parser sum z tabel"""
        totals = {}

        for table in tables:
            if not table:
                continue

            for row in table:
                if not row:
                    continue

                row_text = ' '.join([str(cell) for cell in row if cell])

                if any(keyword in row_text.lower() for keyword in ['razem', 'suma', 'do zapłaty']):
                    numbers = re.findall(r'[\d,]+[.,]?\d*', row_text)
                    numbers = [self._clean_number(n) for n in numbers if self._clean_number(n) > 0]

                    if len(numbers) >= 3:
                        totals['suma_netto'] = numbers[-3]
                        totals['vat_kwota'] = numbers[-2]
                        totals['suma_brutto'] = numbers[-1]
                        totals['vat_procent'] = 23
                        break

        return totals

    def _parse_consumption(self, text: str, tables: List, provider: str) -> float:
        """Parsuje zużycie energii w kWh"""

        # Wzorce specyficzne dla dostawców
        specific_patterns = []

        if provider == 'tauron':
            specific_patterns = [
                r'Łączne\s+zużycie\s+energii\s+(\d+)\s*kWh',
                r'Twoje\s+zużycie.*?(\d+)\s*kWh',
            ]
        elif provider in ('pge', 'lumi_pge'):
            specific_patterns = [
                # PGE: "Zużycie energii elektrycznej za 2024 rok 2.359 kWh" (separator tysięcy!)
                r'Zużycie\s+energii\s+elektrycznej.*?([\d.]+)\s*kWh',
            ]
        elif provider == 'enea':
            specific_patterns = [
                # ENEA: "Ogółem zużycie: 459 kWh"
                r'Ogółem\s+zużycie:\s*(\d+)\s*kWh',
                # ENEA str.2: "Zużycie: 459 kWh"
                r'Zużycie:\s*(\d+)\s*kWh',
            ]

        for pattern in specific_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                consumption = self._clean_consumption_number(match.group(1))
                if 50 <= consumption <= 100000:
                    return consumption

        # Generyczne wzorce
        patterns = [
            r'Zużycie:?\s*(\d+)\s*kWh',
            r'Energia\s+czynna.*?(\d+)\s*kWh',
            r'Razem\s+energia.*?(\d+)\s*kWh',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                consumption = self._clean_number(match.group(1))
                if 50 <= consumption <= 100000:
                    return consumption

        # PGE / Lumi PGE: sumuj zużycie z tabel (kolumna "Ilość" z jednostką "kWh")
        if provider in ('pge', 'lumi_pge'):
            total_kwh = self._sum_consumption_from_tables_pge(tables)
            if total_kwh >= 50:
                return total_kwh

        # Generyczny fallback: (\d+) kWh — ale ostrożnie, tylko sensowne wartości
        match = re.search(r'(\d+)\s*kWh', text, re.IGNORECASE)
        if match:
            consumption = self._clean_number(match.group(1))
            if 50 <= consumption <= 100000:
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

    def _sum_consumption_from_tables_pge(self, tables: List) -> float:
        """PGE: sumuje zużycie energii czynnej z tabel szczegółowych"""
        total_kwh = 0.0

        for table in tables:
            if not table:
                continue

            header_idx = None
            for idx, row in enumerate(table):
                if not row:
                    continue
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if 'opis' in row_text and 'ilość' in row_text:
                    header_idx = idx
                    break

            if header_idx is None:
                continue

            header = table[header_idx]
            col_opis = self._find_column_index(header, ['opis'])
            col_ilosc = self._find_column_index(header, ['ilość'])
            col_jm = self._find_column_index(header, ['j. m', 'j.m', 'jednostka'])

            if col_opis is None or col_ilosc is None:
                continue

            for row in table[header_idx + 1:]:
                if not row or len(row) < max(col_opis, col_ilosc) + 1:
                    continue

                opis = str(row[col_opis] or "").lower()
                jm = str(row[col_jm] or "").lower() if col_jm is not None and col_jm < len(row) else ""

                # Sumuj tylko pozycje energii czynnej w kWh
                if 'energię czynną' in opis or 'energia czynna' in opis:
                    if 'kwh' in jm or col_jm is None:
                        ilosc = self._clean_number(row[col_ilosc])
                        if ilosc > 0:
                            total_kwh += ilosc

        return total_kwh


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
