# Testy — IMGW-PIB Monitor

*[English version](README_EN.md)*

## Szybki start

```bash
# 1. Sklonuj repo i wejdź do katalogu
git clone https://github.com/abnvle/ha-imgw-pib-monitor.git
cd ha-imgw-pib-monitor

# 2. Utwórz i aktywuj wirtualne środowisko
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Zainstaluj zależności testowe
pip install -r requirements_test.txt

# 4. Uruchom testy jednostkowe
python -m pytest tests/ -v -m "not contract"

# 5. Uruchom testy kontraktowe
python -m pytest tests/ -v -m contract
```

## Struktura testów

```
tests/
├── conftest.py          # Przykładowe dane API + fixture'y pytest
├── test_api.py          # Klient HTTP (mockowany)
├── test_config_flow.py  # Przepływ konfiguracji (auto/manual)
├── test_const.py        # Stałe, parsowanie ikon IMGW
├── test_coordinator.py  # Parsowanie danych synop/hydro/meteo/ostrzeżeń
├── test_sensor.py       # Deskryptory sensorów, wyciąganie wartości
├── test_utils.py        # Haversine, geokodowanie, reverse geocode
├── test_weather.py      # Encja pogodowa, prognoza godzinowa/dzienna
└── test_contract.py     # Testy kontraktowe (prawdziwe API)
```

## Rodzaje testów

### Testy jednostkowe (`-m "not contract"`)

Testują logikę biznesową w izolacji — bez internetu, bez działającej instancji
Home Assistant. Odpowiedzi API są mockowane danymi z `conftest.py`.

| Plik | Co testuje |
|------|-----------|
| `test_api.py` | `ImgwApiClient` — `_fetch()`, obsługa błędów HTTP, metody synop/hydro/meteo/warnings, mapowanie stacji |
| `test_config_flow.py` | Przepływ konfiguracji — tryb auto (GPS), tryb manual, inferowanie województwa z koordynatów, walidacja |
| `test_const.py` | `parse_imgw_icon()` — mapowanie kodów ikon IMGW na warunki HA; spójność stałych (województwa, stacje, współrzędne) |
| `test_coordinator.py` | `_safe_float()`, `_safe_int()`, `_parse_synop()`, `_parse_hydro()`, `_parse_meteo()`, `_parse_warnings_meteo()`, `_parse_warnings_hydro()` — konwersja surowego JSON na dane sensorów |
| `test_sensor.py` | Deskryptory sensorów — unikalne klucze, `value_fn` dla każdego typu danych, ekstrakcja wartości z danych koordynatora |
| `test_utils.py` | `haversine()` — odległość między punktami; `nominatim_reverse_geocode()`, `reverse_geocode()`, `geocode_location()` — geokodowanie z mockiem |
| `test_weather.py` | Encja pogodowa — właściwości current, condition (ikona + fallback), extra attributes, prognoza dzienna (grupowanie po dacie, scalanie dzień+noc), prognoza godzinowa |

### Testy kontraktowe (`-m contract`)

Odpytują **API IMGW-PIB** i sprawdzają, czy format odpowiedzi JSON jest zgodny
z tym, czego oczekuje kod integracji.

| Test | API | Co sprawdza |
|------|-----|-----------|
| `test_synop_response_schema` | `danepubliczne.imgw.pl/api/data/synop` | Lista stacji, klucze: `id_stacji`, `stacja`, `temperatura`, `cisnienie` itp. |
| `test_hydro_response_schema` | `danepubliczne.imgw.pl/api/data/hydro` | Lista stacji, klucze: `id_stacji`, `rzeka`, `stan_wody`, `lat`, `lon` itp. |
| `test_meteo_response_schema` | `danepubliczne.imgw.pl/api/data/meteo` | Lista stacji, klucze: `kod_stacji`, `nazwa_stacji`, parametry meteo |
| `test_warnings_meteo_response_schema` | `danepubliczne.imgw.pl/api/data/warningsmeteo` | Schema ostrzeżeń meteorologicznych, `teryt` jako lista |
| `test_warnings_hydro_response_schema` | `danepubliczne.imgw.pl/api/data/warningshydro` | Schema ostrzeżeń hydrologicznych, `obszary` jako lista z `opis` |
| `test_search_response_schema` | `imgw-api-proxy.evtlab.pl/search` | Wyszukiwanie lokalizacji, klucze: `name`, `lat`, `lon`, `teryt`, `province` |
| `test_forecast_response_schema` | `imgw-api-proxy.evtlab.pl/forecast` | Prognoza: `current`, `hourly`, `daily`, `sun` |
| `test_reverse_geocode_response_schema` | `nominatim.openstreetmap.org/reverse` | Reverse geocode, `address` z `city`/`town`/`village` |

> Testy ostrzeżeń (meteo/hydro) używają `pytest.skip()` gdy brak aktywnych
> ostrzeżeń — nie da się zweryfikować schematu pustej listy.

## Przydatne komendy

```bash
# Wszystkie testy naraz
python -m pytest tests/ -v

# Tylko konkretny plik
python -m pytest tests/test_coordinator.py -v

# Tylko konkretna klasa
python -m pytest tests/test_weather.py::TestWeatherDailyForecast -v

# Z pokryciem kodu (wymaga: pip install pytest-cov)
python -m pytest tests/ -m "not contract" --cov=custom_components/imgw_pib_monitor
```
