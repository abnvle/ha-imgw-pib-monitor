# IMGW-PIB Monitor - Architecture

[Wersja polska](ARCHITECTURE.md)

## Overview

Home Assistant integration for the IMGW-PIB public API (Institute of Meteorology and Water Management - National Research Institute). Uses two-tier coordinator architecture for efficient data fetching from 5 API endpoints, supports 32 sensors, and offers two configuration modes with advanced geocoding and county-level warning filtering.

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
        │  - fetches every 15 min     │
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
│   Sensors 1    │          │   Sensors N      │
│   (8-32)       │          │   (8-32)         │
└────────────────┘          └──────────────────┘
```

## File Structure

```
custom_components/imgw_pib_monitor/
├── __init__.py              # Entry point, setup/unload
├── manifest.json            # Integration metadata
├── const.py                 # Constants, endpoints, voivodeship codes, SYNOP coords
├── api.py                   # HTTP client for IMGW-PIB API
├── coordinator.py           # Global + Instance coordinators
├── config_flow.py           # Config Flow (auto/manual) + Options Flow
├── sensor.py                # 32 sensor definitions
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
- **Interval**: 15 minutes (fixed)
- **Rate limiting**: Semaphore with limit of 2 concurrent requests + 200ms delay
- **Endpoints**: Fetches all 5 endpoints in parallel via `asyncio.gather`
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

### 3. API Client (`api.py`)

```python
class ImgwApiClient:
    """HTTP client for IMGW-PIB API"""

    def __init__(self, session: aiohttp.ClientSession)
        # Uses HTTP session from Home Assistant

    async def _fetch(self, url: str) -> list | dict
        # Timeout: 30 seconds
        # Error handling: ImgwApiError, ImgwApiConnectionError

    # Public methods:
    async def get_all_synop_data() -> list[dict]
    async def get_all_hydro_data() -> list[dict]
    async def get_all_meteo_data() -> list[dict]
    async def get_warnings_meteo() -> list[dict]
    async def get_warnings_hydro() -> list[dict]

    # Helper methods:
    async def get_synop_stations() -> dict[str, str]  # id: name
    async def get_hydro_stations() -> dict[str, str]  # id: "name (river)"
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

**Measurement** (24 sensors):
- State class: MEASUREMENT
- Device class: temperature, wind_speed, humidity, atmospheric_pressure, precipitation
- Updated every 15-120 minutes

**Diagnostic** (8 sensors):
- Entity category: DIAGNOSTIC
- Contains: station ID, distance, warning details
- Not displayed in main view

#### Device grouping

- **Auto mode**: All sensors grouped under a single "IMGW-PIB Monitor" device
- **Manual mode**: Separate devices per station (station name) or per warning region

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
Coordinates fetched directly from API (`lat` / `lon`).

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
   └─ YES -> use existing

2. Create ImgwDataUpdateCoordinator for this entry
   ├─ pass global_coordinator
   ├─ set update_interval from config
   └─ save in hass.data[DOMAIN][entry_id]

3. Call first_refresh()
   ├─ global_coordinator fetches data from API
   └─ instance_coordinator filters for its sensors

4. Forward setup to platforms (sensor)
   └─ sensor.async_setup_entry() creates sensors

5. Register update listener for Options Flow
```

### Data Update
```
┌─────────────────────────────────────────────┐
│ Timer (every 15 min)                        │
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
│    └─ ... (5 endpoints)                     │
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
│ 5. Calculate distances              │
│ 6. Return prepared data             │
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
- **Before**: N instances x 5 endpoints = 5N requests
- **After**: 1 global x 5 endpoints = 5 requests
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
| Hydro | `https://danepubliczne.imgw.pl/api/data/hydro` | JSON | List of stations with hydrological data |
| Meteo | `https://danepubliczne.imgw.pl/api/data/meteo` | JSON | List of meteorological stations |
| Warnings Meteo | `https://danepubliczne.imgw.pl/api/data/warningsmeteo` | JSON | Warnings with TERYT codes |
| Warnings Hydro | `https://danepubliczne.imgw.pl/api/data/warningshydro` | JSON | Warnings with area list |

## Technical Requirements

- **Home Assistant**: 2024.6+
- **Python**: 3.12+
- **Dependencies**: aiohttp (built into HA), voluptuous (built into HA)
- **API**: No authentication required
- **Network**: Access to:
  - `danepubliczne.imgw.pl` (measurement data)
  - `imgw-api-proxy.evtlab.pl` (location search, TERYT codes)

## Limits and Restrictions

### IMGW-PIB API Limits
- No official limits
- Integration uses rate limiting (2 req + 200ms) as best practice
- Global coordinator: 5 requests every 15 minutes

### IMGW API Proxy Limits
- No official limits for location search
- Used only during configuration (not during runtime)
- Timeout: 10 seconds

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
