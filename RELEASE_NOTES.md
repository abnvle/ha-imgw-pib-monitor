# IMGW-PIB Monitor v2.1.0

Ostrzeżenia rozszerzone z meteo.imgw.pl, wzbogacone dane hydrologiczne z hydro-back API oraz poprawki bezpieczeństwa i stabilności.

---

## Nowe funkcje

### Ostrzeżenia rozszerzone (meteo.imgw.pl)
- **Nowe API** — ostrzeżenia z `meteo.imgw.pl/api/meteo/messages/v1/osmet/latest/osmet-teryt` (niezależne od standardowego API ostrzeżeń).
- **6 nowych sensorów** — liczba ostrzeżeń (obecne / aktywne), najwyższy stopień, lista kodów zjawisk.
- **38 binary sensorów** — per poziom (1/2/3) x stan (obecne/aktywne) + per zjawisko (16 kodów) x stan.
- **16 zjawisk meteorologicznych** — burze, grad, intensywne opady śniegu/deszczu, mgła, oblodzenie, opady marznące, przymrozki, roztopy, silny wiatr, upał i inne.
- **Atrybuty** — poziom, prawdopodobieństwo, treść SMS, daty ważności.
- **Nowa platforma** — `binary_sensor` (dodana obok `sensor` i `weather`).

### Wzbogacone dane hydrologiczne (hydro-back API)
- **Nowe API** — dane z `hydro-back.imgw.pl/station/hydro/status` (poziomy alarmowe, trendy).
- **6 nowych sensorów hydro**:
  - Stan poziomu wody (enum: low, medium, high, warning, alarm)
  - Trend poziomu wody (enum: strongly_falling, falling, slightly_falling, stable, rising, strongly_rising)
  - Ile cm do poziomu ostrzegawczego
  - Ile cm do poziomu alarmowego
  - Status alarmu wodnego (enum: none, warning, alarm)
  - Zjawisko zarastania
- **Atrybuty sensora stanu wody** — poziom alarmowy i ostrzegawczy jako dodatkowe atrybuty.

### Filtrowanie po powiecie
- **Przełącznik w Options Flow** — możliwość włączenia/wyłączenia filtrowania ostrzeżeń na poziomie powiatu bez rekonfiguracji.
- **Automatyczne wykrywanie powiatu** — podczas migracji z v2.0.0 system sam wykrywa powiat na podstawie lokalizacji.

---

## Poprawki bezpieczeństwa i stabilności

- **Bezpieczne parsowanie ostrzeżeń meteo** — `int()` w `_parse_warnings_meteo` zabezpieczone `try/except` (wcześniej crash przy nietypowych danych z API).
- **Poprawny typ domyślny** — `_fetch_with_limit` zwraca `{}` zamiast `[]` dla enhanced warnings przy błędzie API.
- **Warunkowe pobieranie** — globalny koordynator pobiera ostrzeżenia rozszerzone tylko gdy jakakolwiek instancja ich potrzebuje.
- **Tworzenie encji bez danych** — binary sensory i sensory `always_create` tworzą się nawet gdy API jest chwilowo niedostępne przy starcie.
- **Reużywalna sesja HTTP** — hydro-back API używa jednej sesji zamiast tworzenia nowej przy każdym zapytaniu.
- **Poprawny cleanup** — przy usunięciu ostatniej instancji sesje API są zamykane, globalny koordynator usuwany.
- **Korekta interwału** — interwał globalnego koordynatora jest korygowany w górę po usunięciu instancji z najkrótszym interwałem.
- **Zmniejszony bloat bazy** — atrybuty `hourly`/`daily` encji pogodowej zastąpione `hourly_count`/`daily_count` (dane dostępne przez serwis forecast).
- **Zaktualizowane User-Agent** — nagłówki HTTP zaktualizowane do wersji 2.1.0.
- **Poprawne URL konfiguracji** — `configuration_url` urządzeń wskazuje teraz na repozytorium GitHub.

---

## Migracja

- **Wersja konfiguracji**: 8 → 10 (automatyczna migracja, brak ręcznej interwencji).
- **v8 → v9**: dodanie flagi `enable_enhanced_warnings_meteo`.
- **v9 → v10**: dodanie flagi `use_powiat_for_warnings` + automatyczne wykrycie powiatu.

---

## Wymagania

- Home Assistant 2024.1.0 lub nowszy
- HACS (do instalacji)

---

*Źródłem danych jest Instytut Meteorologii i Gospodarki Wodnej — Państwowy Instytut Badawczy (IMGW-PIB).*
