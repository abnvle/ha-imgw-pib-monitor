# IMGW-PIB Monitor - Architecture

[Wersja polska](ARCHITECTURE.md)

## Overview

Home Assistant integration for the IMGW-PIB public API (Polish Institute of Meteorology and Water Management). Supports 5 API endpoints, 24 sensors, multi-step config flow with powiat-level filtering for meteo warnings.

## API Endpoints

| Module | Endpoint | Data | Default interval |
|--------|----------|------|------------------|
| Synoptic | `/api/data/synop` | Temperature, wind, humidity, pressure, precipitation | 30 min |
| Hydrological | `/api/data/hydro` | Water level, flow, water temp, ice phenomena | 30 min |
| Meteorological | `/api/data/meteo` | Ground/air temp, wind, gusts, 10min precipitation | 30 min |
| Meteo warnings | `/api/data/warningsmeteo` | Warnings by TERYT code (voivodeship or powiat) | 15 min |
| Hydro warnings | `/api/data/warningshydro` | Hydrological warnings by voivodeship | 15 min |

## Config Flow

```
Step 1: Data type
  |- Synoptic / Hydrological / Meteorological -> Step 2a
  |- Meteo warnings -> Step 2b
  |- Hydro warnings -> Step 2c

Step 2a: Station selection (fetched from API, sorted alphabetically)
Step 2b: Voivodeship -> Powiat (or "Entire voivodeship")
Step 2c: Voivodeship

Step 3: Update interval (5-120 min)
```

## Options Flow

Allows changing after setup:
- Measurement station (synop/hydro/meteo)
- Voivodeship and powiat (meteo warnings)
- Voivodeship (hydro warnings)
- Update interval

## Sensors

### Synoptic (6)

| Sensor | Device class | Unit |
|--------|-------------|------|
| Temperature | temperature | °C |
| Wind speed | wind_speed | m/s |
| Wind direction | - | ° |
| Humidity | humidity | % |
| Precipitation | precipitation | mm |
| Pressure | atmospheric_pressure | hPa |

### Hydrological (4)

| Sensor | Device class | Unit |
|--------|-------------|------|
| Water level | - | cm |
| Water flow | - | m³/s |
| Water temperature | temperature | °C |
| Ice phenomenon | - | - |

### Meteorological (8)

| Sensor | Device class | Unit |
|--------|-------------|------|
| Air temperature | temperature | °C |
| Ground temperature | temperature | °C |
| Average wind speed | wind_speed | m/s |
| Maximum wind speed | wind_speed | m/s |
| Wind gust (10min) | wind_speed | m/s |
| Wind direction | - | ° |
| Humidity | humidity | % |
| Precipitation (10min) | precipitation | mm |

### Meteo warnings (3)

| Sensor | Description |
|--------|------------|
| Active count | number of current warnings |
| Max level | 1-3 |
| Latest warning | content, level, validity in attributes |

### Hydro warnings (3)

| Sensor | Description |
|--------|------------|
| Active count | number of current warnings |
| Max level | numeric value |
| Latest warning | event, description in attributes |

## Meteo warning filtering

The warningsmeteo API returns warnings with 4-digit TERYT codes (powiat level). The integration filters using `startswith`:
- 2-digit code (e.g. `12`) - entire malopolskie voivodeship
- 4-digit code (e.g. `1210`) - nowosadecki powiat only

Hydro warnings don't have powiat-level TERYT codes - filtering by voivodeship only.

## File structure

```
custom_components/imgw_pib_monitor/
├── __init__.py          # Setup, platform loading
├── manifest.json        # HA manifest
├── config_flow.py       # Config Flow + Options Flow
├── const.py             # Constants, voivodeship codes
├── coordinator.py       # DataUpdateCoordinator
├── sensor.py            # Sensor definitions
├── api.py               # IMGW API client
├── teryt.py             # TERYT powiat codes (380 counties)
├── strings.json         # Base strings (required by HA)
└── translations/
    ├── en.json
    └── pl.json
```

## Requirements

- Home Assistant 2024.6+
- Python 3.12+
- aiohttp (built into HA)
- No API key needed