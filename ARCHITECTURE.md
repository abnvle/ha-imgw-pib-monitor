# IMGW-PIB Monitor - Architektura

[English version](ARCHITECTURE_EN.md)

## Przegląd

Integracja Home Assistant dla publicznego API IMGW-PIB (Instytut Meteorologii i Gospodarki Wodnej - Państwowy Instytut Badawczy). Wykorzystuje dwustopniową architekturę koordynatorów do efektywnego pobierania danych z 5 endpointów API, obsługuje 32 sensory oraz oferuje dwa tryby konfiguracji z zaawansowanym geokodowaniem i filtrowaniem ostrzeżeń na poziomie powiatów.

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                       │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
┌───────▼────────┐              ┌─────────▼────────┐
│  Config Flow   │              │   Options Flow   │
│  (setup)       │              │   (reconfigure)  │
└───────┬────────┘              └─────────┬────────┘
        │                                  │
        └──────────────┬───────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  Global Coordinator         │
        │  (wspólny dla wszystkich)   │
        │  - pobiera z API co 15 min  │
        │  - rate limiting (2 req)    │
        └──────────────┬──────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                              │
┌───────▼────────┐          ┌─────────▼────────┐
│ Instance       │          │ Instance         │
│ Coordinator 1  │   ...    │ Coordinator N    │
│ (filtruje)     │          │ (filtruje)       │
└───────┬────────┘          └─────────┬────────┘
        │                              │
┌───────▼────────┐          ┌─────────▼────────┐
│   Sensors 1    │          │   Sensors N      │
│   (8-32)       │          │   (8-32)         │
└────────────────┘          └──────────────────┘
```

## Struktura plików

```
custom_components/imgw_pib_monitor/
├── __init__.py              # Entry point, setup/unload
├── manifest.json            # Metadata integracji
├── const.py                 # Stałe, endpointy, kody województw, współrzędne SYNOP
├── api.py                   # HTTP client dla IMGW-PIB API
├── coordinator.py           # Global + Instance coordinators
├── config_flow.py           # Config Flow (auto/manual) + Options Flow
├── sensor.py                # Definicje 32 sensorów
├── utils.py                 # Geocoding, Haversine
├── strings.json             # Stringi bazowe (wymagane przez HA)
└── translations/
    ├── pl.json              # Tłumaczenia polskie (Config/Options Flow)
    └── en.json              # Tłumaczenia angielskie
```

## Komponenty

### 1. Config Flow (`config_flow.py`)

Obsługuje dwa tryby konfiguracji:

#### Tryb automatyczny (Auto-Discovery)
```
┌─────────────────────────────────────────────┐
│ 1. Pobierz GPS z Home Assistant config     │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 2. Pobierz wszystkie stacje z API           │
│    - synop (64 stacje)                      │
│    - hydro (zmienne)                        │
│    - meteo (zmienne)                        │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 3. Oblicz odległości (Haversine)            │
│    - synop: użyj zakodowanych współrzędnych │
│    - hydro/meteo: użyj lat/lon z API        │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 4. Wybierz najbliższe (< 50 km)             │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 5. Reverse geocoding (IMGW API Proxy)       │
│    - wykryj województwo z API               │
│    - pobierz kod TERYT powiatu              │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 6. Użytkownik wybiera typy danych           │
│    ☐ Synop  ☐ Meteo  ☐ Hydro               │
│    ☐ Ostrzeżenia meteo ☐ Ostrzeżenia hydro │
│    ☐ Filtruj po powiecie (opcjonalne)      │
└─────────────────────────────────────────────┘
```

#### Tryb manualny
```
┌─────────────────────────────────────────────┐
│ 1. Użytkownik wpisuje lokalizację          │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 2. Wyszukiwanie (IMGW API Proxy)            │
│    - zwraca do 50 propozycji                │
│    - kod TERYT, gmina, powiat, województwo  │
│    - sortowanie po randze (rank)            │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 3. Użytkownik wybiera z listy               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 4. Wykryj województwo i powiat z adresu     │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 5. Znajdź najbliższe stacje (jak auto)      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 6. Użytkownik wybiera typy danych           │
└─────────────────────────────────────────────┘
```

### 2. Koordynatory (`coordinator.py`)

#### Global Coordinator (`ImgwGlobalDataCoordinator`)
- **Cel**: Centralne pobieranie danych dla wszystkich instancji
- **Interwał**: 15 minut (stały)
- **Rate limiting**: Semafora z limitem 2 równoczesnych zapytań + 200ms opóźnienie
- **Endpoints**: Pobiera wszystkie 5 endpointów równolegle przez `asyncio.gather`
- **Cache**: Przechowuje dane w `self.data`, dostępne dla wszystkich instance coordinators
- **Singleton**: Tworzony raz w `hass.data[DOMAIN]["global_coordinator"]`

#### Instance Coordinator (`ImgwDataUpdateCoordinator`)
- **Cel**: Filtrowanie i przygotowanie danych dla konkretnej instancji
- **Interwał**: Konfigurowalny (5-120 minut, domyślnie 30)
- **Źródło danych**: Pobiera z `global_coordinator.data`
- **Logika**:
  1. Sprawdza czy globalny koordynator ma dane
  2. W trybie auto - aktualizuje wybrane stacje jeśli zmieniły się współrzędne HA
  3. Filtruje dane dla wybranych stacji/regionów
  4. Parsuje i waliduje wartości (`_safe_float`, `_safe_int`)
  5. Oblicza odległości do stacji
  6. Przygotowuje dane dla sensorów

### 3. API Client (`api.py`)

```python
class ImgwApiClient:
    """Klient HTTP dla IMGW-PIB API"""

    def __init__(self, session: aiohttp.ClientSession)
        # Używa sesji HTTP z Home Assistant

    async def _fetch(self, url: str) -> list | dict
        # Timeout: 30 sekund
        # Obsługa błędów: ImgwApiError, ImgwApiConnectionError

    # Publiczne metody:
    async def get_all_synop_data() -> list[dict]
    async def get_all_hydro_data() -> list[dict]
    async def get_all_meteo_data() -> list[dict]
    async def get_warnings_meteo() -> list[dict]
    async def get_warnings_hydro() -> list[dict]

    # Pomocnicze metody:
    async def get_synop_stations() -> dict[str, str]  # id: nazwa
    async def get_hydro_stations() -> dict[str, str]  # id: "nazwa (rzeka)"
    async def get_meteo_stations() -> dict[str, str]  # kod: nazwa
```

### 4. Sensory (`sensor.py`)

#### Hierarchia klas
```
SensorEntity (Home Assistant)
    └── CoordinatorEntity[ImgwDataUpdateCoordinator]
        └── ImgwSensorEntity
            ├── uses: ImgwSensorEntityDescription
            └── implements:
                - native_value (z value_fn)
                - extra_state_attributes (z extra_attrs_fn)
                - device_info (grupowanie urządzeń)
```

#### Typy sensorów

**Pomiarowe** (24 sensory):
- State class: MEASUREMENT
- Device class: temperature, wind_speed, humidity, atmospheric_pressure, precipitation
- Aktualizowane co 15-120 minut

**Diagnostyczne** (8 sensorów):
- Entity category: DIAGNOSTIC
- Zawierają: ID stacji, odległość, szczegóły ostrzeżeń
- Nie są wyświetlane w głównym widoku

#### Grupowanie urządzeń

- **Tryb auto**: Wszystkie sensory zgrupowane pod jednym urządzeniem "IMGW-PIB Monitor"
- **Tryb manualny**: Oddzielne urządzenia per stacja (nazwa stacji) lub per region ostrzeżeń

### 5. Wyszukiwanie lokalizacji (`utils.py` i `config_flow.py`)

#### Forward Geocoding (nazwa -> współrzędne)
```python
async def geocode_location(session, location_name, limit=50):
    """
    Używa: IMGW API Proxy
    Endpoint: https://imgw-api-proxy.evtlab.pl/search?name=...
    Zwraca: [(lat, lon, location_details, display_name), ...]

    location_details zawiera:
    - teryt: kod TERYT powiatu (np. "1465")
    - province: nazwa województwa (np. "mazowieckie")
    - district: nazwa powiatu (np. "St. Warszawa")
    - commune: nazwa gminy (np. "Śródmieście")
    - name: nazwa miejscowości (np. "Warszawa")
    - rank: ranking miejscowości (wyższy = ważniejsza)
    - synoptic: czy ma stację synoptyczną
    """
```

#### Reverse Geocoding (współrzędne -> lokalizacja)
```python
async def reverse_geocode(session, lat, lon, voivodeship_capitals=None):
    """
    Używa: IMGW API Proxy
    Endpoint: https://imgw-api-proxy.evtlab.pl/search?name=...
    Metoda: wyszukuje lokalizacje i wybiera najbliższą (< 50km)
    Zwraca: {teryt, province, district, commune, name, synoptic}
    """
```

### 6. Kody TERYT i filtrowanie ostrzeżeń

Kod TERYT powiatu i jego nazwa są pobierane bezpośrednio z IMGW API Proxy
podczas konfiguracji i zapisywane w config entry (`CONF_POWIAT` i `CONF_POWIAT_NAME`).
Nie ma lokalnej bazy kodów TERYT - integracja polega na danych z API.

#### Format kodu TERYT
- **2 cyfry**: Województwo (02-32)
- **4 cyfry**: Powiat (AABB)
  - AA: województwo
  - BB: powiat (01-60) lub miasto (61-99)

#### Filtrowanie ostrzeżeń
```python
# Ostrzeżenia meteo (API zwraca kody TERYT):
warnings = [w for w in all_warnings
            if any(t.startswith(teryt_code) for t in w.get("teryt", []))]

# Ostrzeżenia hydro (brak kodów TERYT, wyszukiwanie w tekście):
# powiat_name pochodzi z config_data[CONF_POWIAT_NAME]
warnings = [w for w in all_warnings
            if any(powiat_name in area.get("opis", "").lower()
                   for area in w.get("obszary", []))]
```

### 7. Współrzędne stacji (`const.py`)

#### Stacje SYNOP (64 stacje)
```python
SYNOP_STATIONS: dict[str, tuple[float, float]] = {
    "12001": (54.85, 18.67),  # Platforma
    "12375": (52.23, 21.01),  # Warszawa
    ...
}
```
**Powód**: API nie zwraca współrzędnych dla stacji synoptycznych

#### Stacje HYDRO i METEO
Współrzędne pobierane bezpośrednio z API (`lat` / `lon`).

#### Stolice województw
```python
VOIVODESHIP_CAPITALS: dict[str, tuple[float, float]] = {
    "12": (50.0647, 19.9450),  # Kraków
    "14": (52.2297, 21.0122),  # Warszawa
    ...
}
```
**Użycie**: Wykrywanie województwa na podstawie odległości (fallback)

### 8. Obliczanie odległości (`utils.py`)

```python
def haversine(lat1, lon1, lat2, lon2) -> float:
    """
    Wzór Haversine do obliczania odległości na kuli ziemskiej

    Parametry:
        lat1, lon1: współrzędne punktu 1 (stopnie)
        lat2, lon2: współrzędne punktu 2 (stopnie)

    Zwraca:
        odległość w kilometrach

    Dokładność: ±0.5% dla odległości < 500 km
    """
```

## Przepływ danych

### Inicjalizacja (`async_setup_entry`)
```
1. Sprawdź czy global_coordinator istnieje
   ├─ NIE -> utwórz nowy ImgwGlobalDataCoordinator
   └─ TAK -> użyj istniejącego

2. Utwórz ImgwDataUpdateCoordinator dla tego entry
   ├─ przekaż global_coordinator
   ├─ ustaw update_interval z konfiguracji
   └─ zapisz w hass.data[DOMAIN][entry_id]

3. Wywołaj first_refresh()
   ├─ global_coordinator pobiera dane z API
   └─ instance_coordinator filtruje dla swoich sensorów

4. Forward setup do platform (sensor)
   └─ sensor.async_setup_entry() tworzy sensory

5. Zarejestruj update listener dla Options Flow
```

### Aktualizacja danych
```
┌─────────────────────────────────────────────┐
│ Timer (co 15 min)                           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ Global Coordinator._async_update_data()     │
│                                             │
│ 1. async with semaphore (limit 2):         │
│    ├─ fetch synop                           │
│    ├─ await asyncio.sleep(0.2)             │
│    ├─ fetch hydro                           │
│    ├─ await asyncio.sleep(0.2)             │
│    └─ ... (5 endpointów)                    │
│                                             │
│ 2. Zapisz w self.data                       │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼────────┐   ┌──────▼────────┐
│ Instance 1     │   │ Instance N    │
│ Timer (30 min) │   │ Timer (30 min)│
└───────┬────────┘   └──────┬────────┘
        │                   │
┌───────▼────────────────────▼────────┐
│ Instance._async_update_data()       │
│                                     │
│ 1. Pobierz global_coordinator.data │
│ 2. Jeśli auto -> sprawdź lokalizację│
│ 3. Filtruj dla swoich stacji       │
│ 4. Parsuj i waliduj                 │
│ 5. Oblicz odległości                │
│ 6. Zwróć przygotowane dane          │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼────────┐   ┌──────▼────────┐
│ Sensors 1      │   │ Sensors N     │
│ Update state   │   │ Update state  │
└────────────────┘   └───────────────┘
```

### Dynamiczna aktualizacja stacji (tryb auto)
```python
def _update_auto_config(global_data, lat, lon):
    """
    Wywoływane przy każdej aktualizacji instance coordinator

    1. Pobierz obecne współrzędne HA
    2. Jeśli się zmieniły:
       ├─ Znajdź nowe najbliższe stacje (każdego typu)
       ├─ Zaktualizuj config_data (w pamięci)
       ├─ Log: "Auto-selected SYNOP station X at Y km"
       └─ Zaktualizuj województwo (dla ostrzeżeń)

    3. Sensory automatycznie dostaną dane z nowych stacji
    """
```

## Obsługa błędów

### Poziom API
```python
try:
    data = await api.get_all_synop_data()
except ImgwApiConnectionError:
    # Brak połączenia internetowego
    _LOGGER.warning("Connection error: %s", err)
    return []
except ImgwApiError:
    # Błąd API (status != 200, timeout, etc.)
    _LOGGER.error("API error: %s", err)
    return []
```

### Poziom Coordinator
```python
async def _async_update_data():
    if not global_data:
        raise UpdateFailed("Global IMGW data is unavailable")

    # Kontynuuj z pustymi wartościami zamiast fail
    # Sensory pokażą "unavailable" lub "None"
```

### Poziom Sensor
```python
@property
def native_value(self):
    val = self.entity_description.value_fn(self._station_data)
    if val is None:
        return None  # Sensor będzie "unavailable"
    return val

def _safe_float(v):
    """Bezpieczna konwersja - zwraca None zamiast exception"""
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
```

## Wydajność i optymalizacja

### Rate Limiting
```python
class ImgwGlobalDataCoordinator:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(2)

    async def _fetch_with_limit(self, coro):
        async with self._semaphore:
            result = await coro
            await asyncio.sleep(0.2)  # 200ms między zapytaniami
            return result
```

### Współdzielenie danych
- **Przed**: N instancji x 5 endpointów = 5N zapytań
- **Po**: 1 globalny x 5 endpointów = 5 zapytań
- **Oszczędność**: N instancji używa tych samych danych

### Lazy loading
```python
# Config flow - ładuje stacje tylko gdy potrzebne
if not self._found_stations:
    api = ImgwApiClient(session)
    stations = await api.get_synop_stations()
```

### Truncation (zapobieganie bloatowi bazy danych)
```python
for k, v in raw_attrs.items():
    if isinstance(v, str):
        attrs[k] = v[:500]  # Maksymalnie 500 znaków
```

## Endpointy API

| Moduł | Endpoint | Format | Dane |
|-------|----------|--------|------|
| Synop | `https://danepubliczne.imgw.pl/api/data/synop` | JSON | Lista stacji z pomiarami |
| Hydro | `https://danepubliczne.imgw.pl/api/data/hydro` | JSON | Lista stacji z danymi hydrologicznymi |
| Meteo | `https://danepubliczne.imgw.pl/api/data/meteo` | JSON | Lista stacji meteorologicznych |
| Warnings Meteo | `https://danepubliczne.imgw.pl/api/data/warningsmeteo` | JSON | Ostrzeżenia z kodami TERYT |
| Warnings Hydro | `https://danepubliczne.imgw.pl/api/data/warningshydro` | JSON | Ostrzeżenia z listą obszarów |

## Wymagania techniczne

- **Home Assistant**: 2024.6+
- **Python**: 3.12+
- **Dependencies**: aiohttp (wbudowane w HA), voluptuous (wbudowane w HA)
- **API**: Brak wymagań autentykacji
- **Network**: Dostęp do:
  - `danepubliczne.imgw.pl` (dane pomiarowe)
  - `imgw-api-proxy.evtlab.pl` (wyszukiwanie lokalizacji, kody TERYT)

## Limity i ograniczenia

### Limity API IMGW-PIB
- Brak oficjalnych limitów
- Integracja używa rate limiting (2 req + 200ms) jako dobre praktyki
- Globalny coordinator: 5 zapytań co 15 minut

### Limity IMGW API Proxy
- Brak oficjalnych limitów dla wyszukiwania lokalizacji
- Używane tylko podczas konfiguracji (nie podczas runtime)
- Timeout: 10 sekund

### Ograniczenia funkcjonalne
- Stacje SYNOP: brak współrzędnych z API (używamy zakodowanych)
- Ostrzeżenia hydro: filtrowanie po powiecie przez wyszukiwanie tekstowe
- Auto-discovery: promień 50 km (konfigurowalny w kodzie)
- Maksymalny interwał: 120 minut (można zwiększyć w kodzie)

## Dokumentacja zewnętrzna

- [IMGW-PIB API](https://danepubliczne.imgw.pl/)
- [IMGW API Proxy](https://imgw-api-proxy.evtlab.pl/)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Kody TERYT (GUS)](https://eteryt.stat.gov.pl/)
