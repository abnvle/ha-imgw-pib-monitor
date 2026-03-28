# IMGW-PIB Monitor - Architecture

*[Wersja polska](ARCHITECTURE.md)*

## Overview

Home Assistant integration for the IMGW-PIB public API (Institute of Meteorology and Water Management - National Research Institute). Uses multi-tier coordinator architecture for efficient data fetching from 7 API endpoints, supports up to ~90 entities (sensors, binary sensors, weather entity) and an optional weather entity with daily and hourly forecasts. Offers two configuration modes with advanced geocoding and county-level warning filtering.

## Architecture

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
        │  (shared across all)        │
        │  - interval = min(entries)  │
        │  - rate limiting (2 req)    │
        └──────────────┬──────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                              │
┌───────▼────────┐          ┌─────────▼────────┐
│ Instance       │          │ Instance         │
│ Coordinator 1  │   ...    │ Coordinator N    │
│ (filters)      │          │ (filters)        │
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
        │  (optional, per instance)    │
        │  - data from IMGW API Proxy  │
        │  - interval = entry interval │
        └──────────────┬───────────────┘
                       │
                ┌──────▼──────┐
                │  Weather    │
                │  Entity     │
                │  (forecast) │
                └─────────────┘
```

## File Structure

```
custom_components/imgw_pib_monitor/
├── __init__.py              # Entry point, setup/unload, version migration
├── manifest.json            # Integration metadata
├── const.py                 # Constants, endpoints, voivodeship codes, SYNOP coords, icon mapping
├── api.py                   # HTTP client for IMGW-PIB API (+ hydro-back + proxy)
├── coordinator.py           # Global + Instance + Forecast + Radar coordinators
├── config_flow.py           # Config Flow (auto/manual) + Options Flow
├── sensor.py                # ~50 sensor definitions
├── binary_sensor.py         # 38 binary sensors (enhanced warnings)
├── weather.py               # Weather entity with daily and hourly forecasts
├── camera.py                # Radar and satellite camera entities
├── utils.py                 # Geocoding, Haversine
├── strings.json             # Base strings (required by HA)
└── translations/
    ├── pl.json              # Polish translations (Config/Options Flow)
    └── en.json              # English translations
```

## Components

### 1. Config Flow (`config_flow.py`)

Handles two configuration modes:

#### Automatic mode (Auto-Discovery)
```
┌─────────────────────────────────────────────┐
│ 1. Get GPS from Home Assistant config      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 2. Fetch all stations from API              │
│    - synop (64 stations)                    │
│    - hydro (variable)                       │
│    - meteo (variable)                       │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 3. Calculate distances (Haversine)          │
│    - synop: use hardcoded coordinates       │
│    - hydro/meteo: use lat/lon from API      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 4. Select nearest (< 50 km)                 │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 5. Reverse geocoding (IMGW API Proxy)       │
│    - detect voivodeship from API            │
│    - get TERYT county code                  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 6. User selects data types                  │
│    ☐ Synop  ☐ Meteo  ☐ Hydro               │
│    ☐ Meteo warnings ☐ Hydro warnings       │
│    ☐ Enhanced warnings (meteo.imgw)        │
│    ☐ Filter by county (optional)           │
└─────────────────────────────────────────────┘
```

#### Manual mode
```
┌─────────────────────────────────────────────┐
│ 1. User enters location                     │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 2. Location search (IMGW API Proxy)         │
│    - returns up to 50 suggestions           │
│    - TERYT code, municipality, county, etc. │
│    - sorted by rank (importance)            │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 3. User selects from list                   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 4. Detect voivodeship and county from addr  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 5. Find nearest stations (like auto)        │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ 6. User selects data types                  │
└─────────────────────────────────────────────┘
```

### 2. Coordinators (`coordinator.py`)

#### Global Coordinator (`ImgwGlobalDataCoordinator`)
- **Purpose**: Centralized data fetching for all instances
- **Interval**: Synced to the shortest interval across all instances (default 30 minutes)
- **Rate limiting**: Semaphore with limit of 2 concurrent requests + 200ms delay
- **Endpoints**: Fetches 5-7 endpoints in parallel via `asyncio.gather` (enhanced warnings conditionally)
- **Cache**: Stores data in `self.data`, accessible to all instance coordinators
- **Singleton**: Created once in `hass.data[DOMAIN]["global_coordinator"]`

#### Instance Coordinator (`ImgwDataUpdateCoordinator`)
- **Purpose**: Filtering and preparing data for specific instance
- **Interval**: Configurable (5-120 minutes, default 30)
- **Data source**: Fetches from `global_coordinator.data`
- **Logic**:
  1. Check if global coordinator has data
  2. In auto mode - update selected stations if HA coordinates changed
  3. Filter data for selected stations/regions
  4. Parse and validate values (`_safe_float`, `_safe_int`)
  5. Calculate distances to stations
  6. Prepare data for sensors

#### Forecast Coordinator (`ImgwForecastCoordinator`)
- **Purpose**: Fetching weather forecast from IMGW API Proxy
- **Interval**: Same as entry interval (default 30 minutes)
- **Endpoint**: `https://imgw-api-proxy.evtlab.pl/forecast?lat=...&lon=...`
- **Created**: Only when weather forecast is enabled (`CONF_ENABLE_WEATHER_FORECAST`)
- **Timeout**: 15 seconds
- **Data**: Current conditions, daily and hourly forecasts

### 3. API Client (`api.py`)

```python
class ImgwApiClient:
    """HTTP client for IMGW-PIB API"""

    def __init__(self, session: aiohttp.ClientSession)
        # Uses HTTP session from Home Assistant
        # Manages additional session for hydro-back API

    async def _fetch(self, url: str) -> list | dict
        # Timeout: 30 seconds
        # Error handling: ImgwApiError, ImgwApiConnectionError

    # Public methods (danepubliczne.imgw.pl):
    async def get_all_synop_data() -> list[dict]
    async def get_all_meteo_data() -> list[dict]
    async def get_warnings_meteo() -> list[dict]
    async def get_warnings_hydro() -> list[dict]

    # Hydrological data (hydro-back.imgw.pl):
    async def get_all_hydro_data() -> list[dict]
        # Fetches from /list/hydro — 924 stations with current water level
        # Dedicated session with User-Agent (hydro-back requires it)
    async def get_hydro_discharge(station_id) -> dict | None
        # Current discharge from /station/hydro/discharge
    async def get_hydro_water_temperature(station_id) -> dict | None
        # Water temperature from /station/hydro/water-temperature
    async def get_hydro_station_details(station_id) -> dict
        # Station details from /station/hydro/status

    # Enhanced warnings (meteo.imgw.pl):
    async def get_enhanced_warnings_meteo() -> dict  # TERYT → warnings

    # Session management:
    def _get_hydro_session() -> aiohttp.ClientSession  # reusable session
    async def close()  # closes internal sessions

    # Helper methods:
    async def get_synop_stations() -> dict[str, str]  # id: name
    async def get_hydro_stations() -> dict[str, str]  # code: "name (river)"
    async def get_meteo_stations() -> dict[str, str]  # code: name
```

### 4. Sensors (`sensor.py`)

#### Class hierarchy
```
SensorEntity (Home Assistant)
    └── CoordinatorEntity[ImgwDataUpdateCoordinator]
        └── ImgwSensorEntity
            ├── uses: ImgwSensorEntityDescription
            └── implements:
                - native_value (from value_fn)
                - extra_state_attributes (from extra_attrs_fn)
                - device_info (device grouping)
```

#### Sensor types

**Measurement** (19 sensors):
- State class: MEASUREMENT
- Device class: temperature, wind_speed, humidity, atmospheric_pressure, precipitation, distance
- Updated according to instance interval

**Diagnostic** (6 sensors):
- Entity category: DIAGNOSTIC
- Contains: station ID, distance
- Not displayed in main view

**Informational** (13 sensors):
- Warnings: max_level, latest_event, latest_level, latest_probability, latest_valid_from, latest_valid_to, latest_content/description

**Hydro** (5 sensors, from hydro-back API):
- Water level status (enum: low/medium/high/warning/alarm/below/unknown/...)
- Water level trend (enum: strongly_falling → strongly_rising)
- Distance to warning level (cm)
- Distance to alarm level (cm)
- Water alarm status (enum: none/warning/alarm)
- Attributes: alarm and warning levels

**Enhanced warnings** (6 sensors):
- Warning count (current/active)
- Highest warning level
- Phenomenon code list (current/active)

#### Device grouping

- **Measurement stations**: Separate devices per station (station name + river for hydro)
- **Meteo warnings**: Separate device per type + region (voivodeship or county)
- **Hydro warnings**: Separate device per type + region
- **Weather forecast**: Separate device "IMGW Prognoza — {location}"

### 4a. Weather Entity (`weather.py`)

Optional `weather` platform providing a weather entity with forecasts:

#### Class hierarchy
```
WeatherEntity (Home Assistant)
    └── CoordinatorEntity[ImgwForecastCoordinator]
        └── ImgwWeatherEntity
            └── implements:
                - condition (from parse_imgw_icon)
                - native_temperature, humidity, pressure, wind
                - async_forecast_daily (day/night merging)
                - async_forecast_hourly
                - extra_state_attributes (precip, sunrise/sunset, hourly_count, daily_count)
```

#### Current data
- Weather condition (based on IMGW icon)
- Temperature, apparent temperature
- Humidity, pressure
- Wind speed, gusts, bearing
- Cloud coverage

#### Daily forecast
- Merges day/night entries into single forecast per day
- Max/min temperature, max wind, total precipitation
- Icon from day entry (priority) or night entry

#### Hourly forecast
- Full weather data for each hour
- Temperature, feels-like, humidity, pressure, wind, cloud coverage, precipitation

### 4b. Binary Sensors (`binary_sensor.py`)

`binary_sensor` platform for enhanced warnings from meteo.imgw.pl:

#### Class hierarchy
```
BinarySensorEntity (Home Assistant)
    └── CoordinatorEntity[ImgwDataUpdateCoordinator]
        └── ImgwEnhancedBinarySensor
            ├── uses: ImgwEnhancedBinarySensorDescription
            └── implements:
                - is_on (from value_fn)
                - extra_state_attributes (level, probability, SMS, dates)
                - device_info (enhanced warnings device)
```

#### Binary sensor structure (38 entities)
- **Per level × status** (6): level 1/2/3 × current/active
- **Per phenomenon × status** (32): 16 phenomenon codes × current/active

#### 16 meteorological phenomenon codes
`W`, `Z`, `R`, `S`, `M`, `O`, `MR`, `PR`, `RT`, `SW`, `GR`, `IO`, `SO`, `NU`, `UP`, `IN`
(thunderstorms, blizzards, rain, snow, fog, icing, freezing rain, ground frost, thaw, strong wind, hail, intense rainfall, heavy snowfall, dangerous phenomena, heat wave, other)

#### Entity creation
- Entities always created, even when API is temporarily unavailable
- State `off` when no data (not `unavailable`)

### 4c. Radar & Satellite Cameras (`camera.py`)

`camera` platform for radar and satellite maps from IMGW API Proxy:

#### Class hierarchy
```
Camera (Home Assistant)
    └── CoordinatorEntity[ImgwRadarCoordinator]
        └── ImgwRadarCamera
            └── implements:
                - async_camera_image (PNG from proxy)
                - extra_state_attributes (lat/lon, product, timestamp)
                - device_info (radar device)
```

#### Products

**Radar** (5 min):

| Product | Description |
|---------|-------------|
| `cmax` | Radar reflectivity (dBZ) |
| `sri` | Surface rainfall intensity (mm/h) |
| `pac` | 1h precipitation accumulation (mm) |

**Satellite** (15 min):

| Product | Description |
|---------|-------------|
| `natural_color` | Natural color satellite image |
| `infrared` | IR cloud cover (24/7) |
| `water_vapor` | Water vapor 6.2µm |
| `cloud_type` | NWC SAF cloud classification |

#### Coordinator (`ImgwRadarCoordinator`)
- Separate per product (e.g., CMAX and SRI = 2 coordinators)
- Fetches ready-made 800×800 PNG from `imgw-api-proxy.evtlab.pl/radar`
- Proxy composites: OSM basemap + IMGW data + marker + legend + timestamp
- Fault tolerant — one product failure doesn't block others

#### Entity creation
- Created based on user selection (dropdown in config flow)
- Options: single product, all radar (3), all satellite (4), everything (7)
- On option change — unused entities automatically removed from registry

### 5. Location Search (`utils.py` and `config_flow.py`)

#### Forward Geocoding (name -> coordinates)
```python
async def geocode_location(session, location_name, limit=50):
    """
    Uses: IMGW API Proxy
    Endpoint: https://imgw-api-proxy.evtlab.pl/search?name=...
    Returns: [(lat, lon, location_details, display_name), ...]

    location_details contains:
    - teryt: TERYT county code (e.g., "1465")
    - province: voivodeship name (e.g., "mazowieckie")
    - district: county name (e.g., "St. Warszawa")
    - commune: municipality name (e.g., "Srodmiescie")
    - name: place name (e.g., "Warszawa")
    - rank: place importance (higher = more important)
    - synoptic: has synoptic station
    """
```

#### Reverse Geocoding (coordinates -> location)
```python
async def reverse_geocode(session, lat, lon, voivodeship_capitals=None):
    """
    Uses: IMGW API Proxy
    Endpoint: https://imgw-api-proxy.evtlab.pl/search?name=...
    Method: searches locations and selects nearest (< 50km)
    Returns: {teryt, province, district, commune, name, synoptic}
    """
```

### 6. TERYT Codes and Warning Filtering

TERYT county code and name are fetched directly from IMGW API Proxy
during configuration and stored in config entry (`CONF_POWIAT` and `CONF_POWIAT_NAME`).
There is no local TERYT database - the integration relies on API data.

#### TERYT code format
- **2 digits**: Voivodeship (02-32)
- **4 digits**: County (AABB)
  - AA: voivodeship
  - BB: county (01-60) or city (61-99)

#### Warning filtering
```python
# Meteo warnings (API returns TERYT codes):
warnings = [w for w in all_warnings
            if any(t.startswith(teryt_code) for t in w.get("teryt", []))]

# Hydro warnings (no TERYT codes, text search):
# powiat_name comes from config_data[CONF_POWIAT_NAME]
warnings = [w for w in all_warnings
            if any(powiat_name in area.get("opis", "").lower()
                   for area in w.get("obszary", []))]
```

### 7. Station Coordinates (`const.py`)

#### SYNOP stations (64 stations)
```python
SYNOP_STATIONS: dict[str, tuple[float, float]] = {
    "12001": (54.85, 18.67),  # Platforma
    "12375": (52.23, 21.01),  # Warsaw
    ...
}
```
**Reason**: API doesn't return coordinates for synoptic stations

#### HYDRO and METEO stations
Coordinates fetched directly from API (`latitude` / `longitude` for hydro-back, `lat` / `lon` for meteo).

#### Voivodeship capitals
```python
VOIVODESHIP_CAPITALS: dict[str, tuple[float, float]] = {
    "12": (50.0647, 19.9450),  # Krakow
    "14": (52.2297, 21.0122),  # Warsaw
    ...
}
```
**Usage**: Detecting voivodeship based on distance (fallback)

### 8. Distance Calculation (`utils.py`)

```python
def haversine(lat1, lon1, lat2, lon2) -> float:
    """
    Haversine formula for calculating distance on Earth's sphere

    Parameters:
        lat1, lon1: coordinates of point 1 (degrees)
        lat2, lon2: coordinates of point 2 (degrees)

    Returns:
        distance in kilometers

    Accuracy: +/-0.5% for distances < 500 km
    """
```

## Data Flow

### Initialization (`async_setup_entry`)
```
1. Check if global_coordinator exists
   ├─ NO -> create new ImgwGlobalDataCoordinator
   └─ YES -> sync interval to min(all instances)

2. Create ImgwDataUpdateCoordinator for this entry
   ├─ pass global_coordinator
   ├─ set update_interval from config
   └─ save in hass.data[DOMAIN][entry_id]

3. Call first_refresh()
   ├─ global_coordinator fetches data from API
   └─ instance_coordinator filters for its sensors

4. If CONF_ENABLE_WEATHER_FORECAST:
   ├─ create ImgwForecastCoordinator
   ├─ call first_refresh() for forecast
   └─ save in hass.data[DOMAIN][entry_id + "_forecast"]
   IF NOT:
   └─ cleanup any leftover forecast entity/device from registry

5. Forward setup to platforms (sensor, binary_sensor, optionally weather)
   ├─ sensor.async_setup_entry() creates sensors
   ├─ binary_sensor.async_setup_entry() creates binary sensors
   └─ weather.async_setup_entry() creates weather entity

6. Register update listener for Options Flow
```

### Data Update
```
┌─────────────────────────────────────────────┐
│ Timer (interval = min(entries))             │
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
│    ├─ ... (5 base endpoints)               │
│    ├─ if enhanced: fetch meteo.imgw.pl     │
│    └─ (5-7 endpoints, conditionally)       │
│                                             │
│ 2. Save in self.data                        │
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
│ 1. Get global_coordinator.data     │
│ 2. If auto -> check location        │
│ 3. Filter for own stations         │
│ 4. Parse and validate               │
│ 5. Enrich hydro (hydro-back API)   │
│ 6. Parse enhanced warnings          │
│ 7. Calculate distances              │
│ 8. Return prepared data             │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼────────┐   ┌──────▼────────┐
│ Sensors 1      │   │ Sensors N     │
│ Update state   │   │ Update state  │
└────────────────┘   └───────────────┘
```

### Dynamic station update (auto mode)
```python
def _update_auto_config(global_data, lat, lon):
    """
    Called on every instance coordinator update

    1. Get current HA coordinates
    2. If changed:
       ├─ Find new nearest stations (each type)
       ├─ Update config_data (in memory)
       ├─ Log: "Auto-selected SYNOP station X at Y km"
       └─ Update voivodeship (for warnings)

    3. Sensors automatically get data from new stations
    """
```

## Error Handling

### API Level
```python
try:
    data = await api.get_all_synop_data()
except ImgwApiConnectionError:
    # No internet connection
    _LOGGER.warning("Connection error: %s", err)
    return []
except ImgwApiError:
    # API error (status != 200, timeout, etc.)
    _LOGGER.error("API error: %s", err)
    return []
```

### Coordinator Level
```python
async def _async_update_data():
    if not global_data:
        raise UpdateFailed("Global IMGW data is unavailable")

    # Continue with empty values instead of fail
    # Sensors will show "unavailable" or "None"
```

### Sensor Level
```python
@property
def native_value(self):
    val = self.entity_description.value_fn(self._station_data)
    if val is None:
        return None  # Sensor will be "unavailable"
    return val

def _safe_float(v):
    """Safe conversion - returns None instead of exception"""
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
```

## Performance and Optimization

### Rate Limiting
```python
class ImgwGlobalDataCoordinator:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(2)

    async def _fetch_with_limit(self, coro):
        async with self._semaphore:
            result = await coro
            await asyncio.sleep(0.2)  # 200ms between requests
            return result
```

### Data Sharing
- **Before**: N instances x 5-7 endpoints = 5-7N requests
- **After**: 1 global x 5-7 endpoints = 5-7 requests (enhanced conditionally)
- **Savings**: N instances use the same data

### Lazy Loading
```python
# Config flow - loads stations only when needed
if not self._found_stations:
    api = ImgwApiClient(session)
    stations = await api.get_synop_stations()
```

### Truncation (preventing database bloat)
```python
for k, v in raw_attrs.items():
    if isinstance(v, str):
        attrs[k] = v[:500]  # Maximum 500 characters
```

## API Endpoints

| Module | Endpoint | Format | Data |
|--------|----------|--------|------|
| Synop | `https://danepubliczne.imgw.pl/api/data/synop` | JSON | List of stations with measurements |
| Hydro (list) | `https://hydro-back.imgw.pl/list/hydro` | JSON | 924 stations with current water level, thresholds, trend |
| Hydro (discharge) | `https://hydro-back.imgw.pl/station/hydro/discharge?id=...` | JSON | Current discharge/flow (per station) |
| Hydro (water temp) | `https://hydro-back.imgw.pl/station/hydro/water-temperature?id=...` | JSON | Water temperature (per station) |
| Meteo | `https://danepubliczne.imgw.pl/api/data/meteo` | JSON | List of meteorological stations |
| Warnings Meteo | `https://danepubliczne.imgw.pl/api/data/warningsmeteo` | JSON | Warnings with TERYT codes |
| Warnings Hydro | `https://danepubliczne.imgw.pl/api/data/warningshydro` | JSON | Warnings with area list |
| Enhanced Warnings | `https://meteo.imgw.pl/api/meteo/messages/v1/osmet/latest/osmet-teryt` | JSON | Enhanced warnings (16 phenomena, 3 levels) |
| Hydro (details) | `https://hydro-back.imgw.pl/station/hydro/status?id=...` | JSON | Station details (per station) |
| Forecast | `https://imgw-api-proxy.evtlab.pl/forecast` | JSON | Weather forecast (current, daily, hourly) |

## Technical Requirements

- **Home Assistant**: 2024.1.0+
- **Python**: 3.12+
- **Dependencies**: aiohttp (built into HA), voluptuous (built into HA)
- **API**: No authentication required
- **Platforms**: `sensor`, `binary_sensor`, `weather` (optional), `camera` (optional)
- **Config version**: 11 (with automatic migration from older versions 1-10)
- **Network**: Access to:
  - `danepubliczne.imgw.pl` (synoptic, meteo data and warnings)
  - `hydro-back.imgw.pl` (hydrological data — water level, discharge, temperature, alarm thresholds, trend)
  - `meteo.imgw.pl` (enhanced warnings — conditionally)
  - `imgw-api-proxy.evtlab.pl` (location search, TERYT codes, weather forecast, radar maps, station coordinates)
  - `nominatim.openstreetmap.org` (reverse geocoding in auto-discovery mode)

## Limits and Restrictions

### IMGW-PIB API Limits
- No official limits
- Integration uses rate limiting (2 req + 200ms) as best practice
- Global coordinator: 5-7 requests per update cycle (enhanced warnings conditionally)
- Instance coordinator: 2 requests to hydro-back per hydro station per cycle (discharge + water temperature)

### IMGW API Proxy Limits
- No official limits for location search
- Location search: used only during configuration (not during runtime)
- Weather forecast: fetched at runtime (separate coordinator, timeout 15 seconds)
- Search timeout: 10 seconds

### Functional Limitations
- SYNOP stations: no coordinates from API (using hardcoded)
- Hydro warnings: county filtering via text search
- Auto-discovery: 50 km radius (configurable in code)
- Maximum interval: 120 minutes (can be increased in code)

## External Documentation

- [IMGW-PIB API](https://danepubliczne.imgw.pl/)
- [IMGW API Proxy](https://imgw-api-proxy.evtlab.pl/)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [TERYT Codes (GUS)](https://eteryt.stat.gov.pl/)
