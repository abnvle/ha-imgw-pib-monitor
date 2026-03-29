# IMGW-PIB Monitor - Architektura

*[English version](ARCHITECTURE_EN.md)*

## Przegląd

Integracja Home Assistant dla publicznego API IMGW-PIB (Instytut Meteorologii i Gospodarki Wodnej - Państwowy Instytut Badawczy). Wykorzystuje wielostopniową architekturę koordynatorów do efektywnego pobierania danych z 7 endpointów API, obsługuje do ~90+ encji (sensory, sensory binarne, encja pogodowa, kamery radarowe/satelitarne/OZE) oraz opcjonalną prognozę pogody z danymi dziennymi i godzinowymi. Oferuje dwa tryby konfiguracji z zaawansowanym geokodowaniem i filtrowaniem ostrzeżeń na poziomie powiatów.

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
        │  - interwał = min(instancje)│
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
│  Sensors 1     │          │  Sensors N       │
│  (8-40)        │          │  (8-40)          │
├────────────────┤          ├──────────────────┤
│ Binary Sensors │          │ Binary Sensors   │
│  (0-38)        │          │  (0-38)          │
└────────────────┘          └──────────────────┘

        ┌──────────────────────────────┐
        │  Forecast Coordinator        │
        │  (opcjonalny, per instancja) │
        │  - dane z IMGW API Proxy     │
        │  - interwał = entry interval │
        └──────────────┬───────────────┘
                       │
                ┌──────▼──────┐
                │  Weather    │
                │  Entity     │
                │  (prognoza) │
                └─────────────┘
```

## Struktura plików

```
custom_components/imgw_pib_monitor/
├── __init__.py              # Entry point, setup/unload, migracja wersji
├── manifest.json            # Metadata integracji
├── const.py                 # Stałe, endpointy, kody województw, współrzędne SYNOP, mapowanie ikon
├── api.py                   # HTTP client dla IMGW-PIB API (+ hydro-back + proxy)
├── coordinator.py           # Global + Instance + Forecast + Radar coordinators
├── config_flow.py           # Config Flow (auto/manual) + Options Flow
├── sensor.py                # Definicje ~50 sensorów
├── binary_sensor.py         # 38 sensorów binarnych (ostrzeżenia rozszerzone)
├── weather.py               # Encja pogodowa z prognozą dzienną i godzinową
├── camera.py                # Encje kamer radarowych i satelitarnych
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
│    ☐ Ostrzeżenia rozszerzone (meteo.imgw)  │
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
- **Interwał**: Synchronizowany z najkrótszym interwałem spośród instancji (domyślnie 30 minut)
- **Rate limiting**: Semafora z limitem 2 równoczesnych zapytań + 200ms opóźnienie
- **Endpoints**: Pobiera 5-7 endpointów równolegle przez `asyncio.gather` (enhanced warnings warunkowo)
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

#### Forecast Coordinator (`ImgwForecastCoordinator`)
- **Cel**: Pobieranie prognozy pogody z IMGW API Proxy
- **Interwał**: Taki sam jak interwał instancji (domyślnie 30 minut)
- **Endpoint**: `https://imgw-api-proxy.evtlab.pl/forecast?lat=...&lon=...`
- **Tworzony**: Tylko gdy włączono prognozę pogody (`CONF_ENABLE_WEATHER_FORECAST`)
- **Timeout**: 15 sekund
- **Dane**: Aktualne warunki, prognoza dzienna i godzinowa

### 3. API Client (`api.py`)

```python
class ImgwApiClient:
    """Klient HTTP dla IMGW-PIB API"""

    def __init__(self, session: aiohttp.ClientSession)
        # Używa sesji HTTP z Home Assistant
        # Zarządza dodatkową sesją dla hydro-back API

    async def _fetch(self, url: str) -> list | dict
        # Timeout: 30 sekund
        # Obsługa błędów: ImgwApiError, ImgwApiConnectionError

    # Publiczne metody (danepubliczne.imgw.pl):
    async def get_all_synop_data() -> list[dict]
    async def get_all_meteo_data() -> list[dict]
    async def get_warnings_meteo() -> list[dict]
    async def get_warnings_hydro() -> list[dict]

    # Dane hydrologiczne (hydro-back.imgw.pl):
    async def get_all_hydro_data() -> list[dict]
        # Pobiera z /list/hydro — 924 stacji z aktualnym stanem wody
        # Dedykowana sesja z User-Agent (hydro-back wymaga)
    async def get_hydro_discharge(station_id) -> dict | None
        # Aktualny przepływ z /station/hydro/discharge
    async def get_hydro_water_temperature(station_id) -> dict | None
        # Temperatura wody z /station/hydro/water-temperature
    async def get_hydro_station_details(station_id) -> dict
        # Szczegóły stacji z /station/hydro/status

    # Ostrzeżenia rozszerzone (meteo.imgw.pl):
    async def get_enhanced_warnings_meteo() -> dict  # TERYT → ostrzeżenia

    # Zarządzanie sesjami:
    def _get_hydro_session() -> aiohttp.ClientSession  # reużywalna sesja
    async def close()  # zamyka wewnętrzne sesje

    # Pomocnicze metody:
    async def get_synop_stations() -> dict[str, str]  # id: nazwa
    async def get_hydro_stations() -> dict[str, str]  # code: "nazwa (rzeka)"
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

**Pomiarowe** (19 sensorów):
- State class: MEASUREMENT
- Device class: temperature, wind_speed, humidity, atmospheric_pressure, precipitation, distance
- Aktualizowane zgodnie z interwałem instancji

**Diagnostyczne** (6 sensorów):
- Entity category: DIAGNOSTIC
- Zawierają: ID stacji, odległość
- Nie są wyświetlane w głównym widoku

**Informacyjne** (13 sensorów):
- Ostrzeżenia: max_level, latest_event, latest_level, latest_probability, latest_valid_from, latest_valid_to, latest_content/description

**Hydro** (5 sensorów, z hydro-back API):
- Stan poziomu wody (enum: low/medium/high/warning/alarm/below/unknown/...)
- Trend poziomu wody (enum: strongly_falling → strongly_rising)
- Odległość do poziomu ostrzegawczego (cm)
- Odległość do poziomu alarmowego (cm)
- Status alarmu wodnego (enum: none/warning/alarm)
- Atrybuty: poziom alarmowy i ostrzegawczy

**Ostrzeżenia rozszerzone** (6 sensorów):
- Liczba ostrzeżeń (obecne/aktywne)
- Najwyższy stopień ostrzeżenia
- Lista kodów zjawisk (obecne/aktywne)

#### Grupowanie urządzeń

- **Stacje pomiarowe**: Oddzielne urządzenia per stacja (nazwa stacji + rzeka dla hydro)
- **Ostrzeżenia meteo**: Osobne urządzenie per typ + region (województwo lub powiat)
- **Ostrzeżenia hydro**: Osobne urządzenie per typ + region
- **Prognoza pogody**: Osobne urządzenie "IMGW Prognoza — {lokalizacja}"

### 4a. Encja pogodowa (`weather.py`)

Opcjonalna platforma `weather` dostarczająca encję pogodową z prognozą:

#### Hierarchia klas
```
WeatherEntity (Home Assistant)
    └── CoordinatorEntity[ImgwForecastCoordinator]
        └── ImgwWeatherEntity
            └── implements:
                - condition (z parse_imgw_icon)
                - native_temperature, humidity, pressure, wind
                - async_forecast_daily (grupowanie dzień/noc)
                - async_forecast_hourly
                - extra_state_attributes (opady, wschód/zachód, hourly_count, daily_count)
```

#### Dane bieżące
- Warunki pogodowe (na podstawie ikony IMGW)
- Temperatura, temperatura odczuwalna
- Wilgotność, ciśnienie
- Prędkość wiatru, porywy, kierunek
- Zachmurzenie

#### Prognoza dzienna
- Grupowanie wpisów dzień/noc w jedną prognozę per dzień
- Temperatura max/min, wiatr max, suma opadów
- Ikona z wpisu dziennego (priorytet) lub nocnego

#### Prognoza godzinowa
- Pełne dane pogodowe na każdą godzinę
- Temperatura, odczuwalna, wilgotność, ciśnienie, wiatr, zachmurzenie, opady

### 4b. Sensory binarne (`binary_sensor.py`)

Platforma `binary_sensor` dla ostrzeżeń rozszerzonych z meteo.imgw.pl:

#### Hierarchia klas
```
BinarySensorEntity (Home Assistant)
    └── CoordinatorEntity[ImgwDataUpdateCoordinator]
        └── ImgwEnhancedBinarySensor
            ├── uses: ImgwEnhancedBinarySensorDescription
            └── implements:
                - is_on (z value_fn)
                - extra_state_attributes (poziom, prawdopodobieństwo, SMS, daty)
                - device_info (urządzenie ostrzeżeń rozszerzonych)
```

#### Struktura sensorów binarnych (38 encji)
- **Per poziom × stan** (6): poziom 1/2/3 × obecne/aktywne
- **Per zjawisko × stan** (32): 16 kodów zjawisk × obecne/aktywne

#### 16 kodów zjawisk meteorologicznych
`W`, `Z`, `R`, `S`, `M`, `O`, `MR`, `PR`, `RT`, `SW`, `GR`, `IO`, `SO`, `NU`, `UP`, `IN`
(burze, zawieje, deszcz, śnieg, mgła, oblodzenie, opady marznące, przymrozki, roztopy, silny wiatr, grad, intensywne opady, silne opady śniegu, niebezpieczne zjawiska, upał, inne)

#### Tworzenie encji
- Encje tworzone zawsze, nawet gdy API chwilowo niedostępne
- Stan `off` gdy brak danych (nie `unavailable`)

### 4c. Kamery radarowe, satelitarne i OZE (`camera.py`)

Platforma `camera` dla map radarowych, satelitarnych i prognoz OZE z IMGW API Proxy:

#### Hierarchia klas
```
Camera (Home Assistant)
    ├── CoordinatorEntity[ImgwRadarCoordinator]
    │   └── ImgwRadarCamera (PNG — radar, satelita, OZE statyczne)
    │       └── implements:
    │           - async_camera_image (PNG z proxy)
    │           - extra_state_attributes (lat/lon, produkt, timestamp)
    │           - device_info (urządzenie radarowe)
    └── CoordinatorEntity[ImgwRadarAnimCoordinator]
        └── ImgwRadarAnimCamera (GIF — animacje OZE)
            └── implements:
                - async_camera_image (animowany GIF z proxy)
                - content_type = "image/gif"
                - frame_interval = 300 (5 min)
```

#### Produkty

**Radar** (odświeżanie co 5 min):

| Produkt | Opis |
|---------|------|
| `cmax` | Odbiciowość radarowa (dBZ) |
| `sri` | Intensywność opadu (mm/h) |
| `pac` | Suma opadu 1h (mm) |

**Satelita** (odświeżanie co 5 min):

| Produkt | Opis |
|---------|------|
| `natural_color` | Zdjęcie w kolorach naturalnych |
| `infrared` | Zachmurzenie IR (24/7) |
| `water_vapor` | Para wodna 6.2µm |
| `cloud_type` | Typy chmur NWC SAF |

**OZE — Odnawialne Źródła Energii** (odświeżanie co pełną godzinę):

| Produkt | Opis | Typ |
|---------|------|-----|
| `oze_pv` | Prognoza generacji fotowoltaicznej (% mocy) | PNG |
| `oze_wind` | Prognoza generacji wiatrowej (% mocy) | PNG |
| `oze_pv_anim` | Animacja prognozy PV na 24h do przodu | GIF |
| `oze_wind_anim` | Animacja prognozy wiatru na 24h do przodu | GIF |

Dane OZE pochodzą z modelu ECMWF IFS 9km (rozdzielczość źródłowa 113×132 px). Proxy upscaluje obraz z nearest-neighbor (zachowanie kolorów legendy), nakłada podkład OSM i marker lokalizacji. Timestampy przypisane do pełnych godzin UTC — identycznie jak na meteo.imgw.pl.

#### Koordynatory

**`ImgwRadarCoordinator`** (radar, satelita, OZE statyczne):
- Osobny per produkt (np. CMAX i SRI = 2 koordynatory)
- Pobiera gotowy PNG 800×800 z `imgw-api-proxy.evtlab.pl/radar`
- Proxy komponuje: podkład OSM + dane IMGW + marker + legenda + timestamp
- Odporny na awarie — błąd jednego produktu nie blokuje innych
- Interwał: 5 min (radar/satelita), 30 min (OZE)

**`ImgwRadarAnimCoordinator`** (animacje OZE):
- Pobiera animowany GIF z proxy (`?animate=24`)
- GIF zawiera 25 klatek (bieżąca godzina + 24h do przodu)
- Timeout 60 sek (GIF-y generowane server-side z gifenc)
- Interwał: 30 min
- Przy błędzie zachowuje poprzedni GIF (nie `UpdateFailed`)

#### Tworzenie encji
- Multi-select w config flow — dowolna kombinacja z 11 produktów
- Przy zmianie opcji — nadmiarowe encje automatycznie usuwane z rejestru

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
Współrzędne pobierane bezpośrednio z API (`latitude` / `longitude` dla hydro-back, `lat` / `lon` dla meteo).

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
   └─ TAK -> zsynchronizuj interwał do min(wszystkie instancje)

2. Utwórz ImgwDataUpdateCoordinator dla tego entry
   ├─ przekaż global_coordinator
   ├─ ustaw update_interval z konfiguracji
   └─ zapisz w hass.data[DOMAIN][entry_id]

3. Wywołaj first_refresh()
   ├─ global_coordinator pobiera dane z API
   └─ instance_coordinator filtruje dla swoich sensorów

4. Jeśli CONF_ENABLE_WEATHER_FORECAST:
   ├─ utwórz ImgwForecastCoordinator
   ├─ wywołaj first_refresh() dla prognozy
   └─ zapisz w hass.data[DOMAIN][entry_id + "_forecast"]
   JEŚLI NIE:
   └─ wyczyść ewentualną encję/urządzenie prognozy z rejestru

5. Forward setup do platform (sensor, binary_sensor, opcjonalnie weather)
   ├─ sensor.async_setup_entry() tworzy sensory
   ├─ binary_sensor.async_setup_entry() tworzy sensory binarne
   └─ weather.async_setup_entry() tworzy encję pogodową

6. Zarejestruj update listener dla Options Flow
```

### Aktualizacja danych
```
┌─────────────────────────────────────────────┐
│ Timer (interwał = min(instancje))           │
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
│    ├─ ... (5 bazowych endpointów)           │
│    ├─ if enhanced: fetch meteo.imgw.pl     │
│    └─ (5-7 endpointów, warunkowo)          │
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
│ 5. Wzbogać hydro (hydro-back API)  │
│ 6. Parsuj ostrzeżenia rozszerzone  │
│ 7. Oblicz odległości                │
│ 8. Zwróć przygotowane dane          │
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
- **Przed**: N instancji x 5-7 endpointów = 5-7N zapytań
- **Po**: 1 globalny x 5-7 endpointów = 5-7 zapytań (enhanced warunkowo)
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
| Hydro (lista) | `https://hydro-back.imgw.pl/list/hydro` | JSON | 924 stacji z aktualnym stanem wody, progami, trendem |
| Hydro (przepływ) | `https://hydro-back.imgw.pl/station/hydro/discharge?id=...` | JSON | Aktualny przepływ (per stacja) |
| Hydro (temp. wody) | `https://hydro-back.imgw.pl/station/hydro/water-temperature?id=...` | JSON | Temperatura wody (per stacja) |
| Meteo | `https://danepubliczne.imgw.pl/api/data/meteo` | JSON | Lista stacji meteorologicznych |
| Warnings Meteo | `https://danepubliczne.imgw.pl/api/data/warningsmeteo` | JSON | Ostrzeżenia z kodami TERYT |
| Warnings Hydro | `https://danepubliczne.imgw.pl/api/data/warningshydro` | JSON | Ostrzeżenia z listą obszarów |
| Enhanced Warnings | `https://meteo.imgw.pl/api/meteo/messages/v1/osmet/latest/osmet-teryt` | JSON | Ostrzeżenia rozszerzone (16 zjawisk, 3 stopnie) |
| Hydro (szczegóły) | `https://hydro-back.imgw.pl/station/hydro/status?id=...` | JSON | Szczegóły stacji (per stacja) |
| Forecast | `https://imgw-api-proxy.evtlab.pl/forecast` | JSON | Prognoza pogody (aktualna, dzienna, godzinowa) |
| Radar/Sat/OZE | `https://imgw-api-proxy.evtlab.pl/radar?lat=...&lon=...&product=...` | PNG | Kompozytowe mapy 800×800 (OSM + dane + marker + legenda) |
| OZE animacja | `https://imgw-api-proxy.evtlab.pl/radar?...&animate=24` | GIF | Animowany GIF prognozy OZE (24h, 25 klatek) |
| OZE źródło | `https://tilesources-c.imgw.pl/vector/oze/epsg3857/latest/` | PNG | Surowe dane ECMWF IFS 9km (113×132 px) |
| Sat tiles | `https://tilesources-a.imgw.pl/tileserver.php?/index.json` | JSON/PNG | Indeks warstw + kafelki satelitarne (zoom 6) |
| Radar list | `https://meteo.imgw.pl/api/radars/v1/list/{product}` | JSON | Lista dostępnych obrazów radarowych |
| Stations | `https://imgw-api-proxy.evtlab.pl/stations/synop` | JSON | Współrzędne stacji synoptycznych |

## Wymagania techniczne

- **Home Assistant**: 2024.1.0+
- **Python**: 3.12+
- **Dependencies**: aiohttp (wbudowane w HA), voluptuous (wbudowane w HA)
- **API**: Brak wymagań autentykacji
- **Platformy**: `sensor`, `binary_sensor`, `weather` (opcjonalna), `camera` (opcjonalna)
- **Wersja konfiguracji**: 11 (z automatyczną migracją starszych wersji 1-10)
- **Network**: Dostęp do:
  - `danepubliczne.imgw.pl` (dane synoptyczne, meteo i ostrzeżenia)
  - `hydro-back.imgw.pl` (dane hydrologiczne — stan wody, przepływ, temperatura, progi alarmowe, trend)
  - `meteo.imgw.pl` (ostrzeżenia rozszerzone — warunkowo)
  - `imgw-api-proxy.evtlab.pl` (wyszukiwanie lokalizacji, kody TERYT, prognoza pogody, mapy radarowe, koordynaty stacji)
  - `nominatim.openstreetmap.org` (reverse geocoding w trybie auto-discovery)

## Limity i ograniczenia

### Limity API IMGW-PIB
- Brak oficjalnych limitów
- Integracja używa rate limiting (2 req + 200ms) jako dobre praktyki
- Globalny coordinator: 5-7 zapytań per cykl aktualizacji (enhanced warnings warunkowo)
- Instance coordinator: 2 zapytania do hydro-back per stacja hydro per cykl (przepływ + temperatura wody)

### Limity IMGW API Proxy
- Brak oficjalnych limitów dla wyszukiwania lokalizacji
- Wyszukiwanie lokalizacji: używane tylko podczas konfiguracji (nie podczas runtime)
- Prognoza pogody: pobierana w runtime (osobny koordynator, timeout 15 sekund)
- Timeout wyszukiwania: 10 sekund

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
