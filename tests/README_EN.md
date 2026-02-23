# Tests — IMGW-PIB Monitor

*[Wersja polska](README.md)*

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/abnvle/ha-imgw-pib-monitor.git
cd ha-imgw-pib-monitor

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install test dependencies
pip install -r requirements_test.txt

# 4. Run unit tests
python -m pytest tests/ -v -m "not contract"

# 5. Run contract tests (requires internet)
python -m pytest tests/ -v -m contract
```

## Test structure

```
tests/
├── conftest.py          # Sample API data + pytest fixtures
├── test_api.py          # HTTP client (mocked)
├── test_config_flow.py  # Configuration flow (auto/manual)
├── test_const.py        # Constants, IMGW icon parsing
├── test_coordinator.py  # Synop/hydro/meteo/warnings data parsing
├── test_sensor.py       # Sensor descriptors, value extraction
├── test_utils.py        # Haversine, geocoding, reverse geocode
├── test_weather.py      # Weather entity, hourly/daily forecast
└── test_contract.py     # Contract tests (live API)
```

## Test types

### Unit tests (`-m "not contract"`)

Test business logic in isolation — no internet, no running Home Assistant
instance. API responses are mocked with sample data from `conftest.py`.

| File | What it tests |
|------|--------------|
| `test_api.py` | `ImgwApiClient` — `_fetch()`, HTTP error handling, synop/hydro/meteo/warnings methods, station mapping |
| `test_config_flow.py` | Configuration flow — auto mode (GPS), manual mode, voivodeship inference from coordinates, validation |
| `test_const.py` | `parse_imgw_icon()` — mapping IMGW icon codes to HA conditions; constant consistency (voivodeships, stations, coordinates) |
| `test_coordinator.py` | `_safe_float()`, `_safe_int()`, `_parse_synop()`, `_parse_hydro()`, `_parse_meteo()`, `_parse_warnings_meteo()`, `_parse_warnings_hydro()` — raw JSON to sensor data conversion |
| `test_sensor.py` | Sensor descriptors — unique keys, `value_fn` for each data type, value extraction from coordinator data |
| `test_utils.py` | `haversine()` — distance between points; `nominatim_reverse_geocode()`, `reverse_geocode()`, `geocode_location()` — geocoding with mocks |
| `test_weather.py` | Weather entity — current properties, condition (icon + fallback), extra attributes, daily forecast (date grouping, day+night merging), hourly forecast |

### Contract tests (`-m contract`)

Query the **live IMGW-PIB API** and verify that the JSON response format matches
what the integration code expects.

| Test | API | What it checks |
|------|-----|---------------|
| `test_synop_response_schema` | `danepubliczne.imgw.pl/api/data/synop` | Station list, keys: `id_stacji`, `stacja`, `temperatura`, `cisnienie` etc. |
| `test_hydro_response_schema` | `danepubliczne.imgw.pl/api/data/hydro` | Station list, keys: `id_stacji`, `rzeka`, `stan_wody`, `lat`, `lon` etc. |
| `test_meteo_response_schema` | `danepubliczne.imgw.pl/api/data/meteo` | Station list, keys: `kod_stacji`, `nazwa_stacji`, meteo parameters |
| `test_warnings_meteo_response_schema` | `danepubliczne.imgw.pl/api/data/warningsmeteo` | Meteorological warnings schema, `teryt` as a list |
| `test_warnings_hydro_response_schema` | `danepubliczne.imgw.pl/api/data/warningshydro` | Hydrological warnings schema, `obszary` as a list with `opis` |
| `test_search_response_schema` | `imgw-api-proxy.evtlab.pl/search` | Location search, keys: `name`, `lat`, `lon`, `teryt`, `province` |
| `test_forecast_response_schema` | `imgw-api-proxy.evtlab.pl/forecast` | Forecast: `current`, `hourly`, `daily`, `sun` |
| `test_reverse_geocode_response_schema` | `nominatim.openstreetmap.org/reverse` | Reverse geocode, `address` with `city`/`town`/`village` |

> Warning tests (meteo/hydro) use `pytest.skip()` when no active warnings
> exist — an empty list cannot be schema-validated.

## Useful commands

```bash
# All tests at once
python -m pytest tests/ -v

# Specific file only
python -m pytest tests/test_coordinator.py -v

# Specific class only
python -m pytest tests/test_weather.py::TestWeatherDailyForecast -v

# With code coverage (requires: pip install pytest-cov)
python -m pytest tests/ -m "not contract" --cov=custom_components/imgw_pib_monitor
```
