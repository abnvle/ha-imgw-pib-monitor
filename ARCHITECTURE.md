# IMGW-PIB Monitor - Architektura

[English version](ARCHITECTURE_EN.md)

## Przegląd

Integracja Home Assistant dla publicznego API IMGW-PIB. Obsługuje 5 endpointów API, 24 sensory, wielokrokowy config flow z wyborem powiatu dla ostrzeżeń meteo.

## Endpointy API

| Moduł | Endpoint | Dane | Domyślny interwał |
|-------|----------|------|--------------------|
| Synoptyczne | `/api/data/synop` | Temperatura, wiatr, wilgotność, ciśnienie, opady | 30 min |
| Hydrologiczne | `/api/data/hydro` | Stan wody, przepływ, temp. wody, zjawiska lodowe | 30 min |
| Meteorologiczne | `/api/data/meteo` | Temp. gruntu/powietrza, wiatr, porywy, opady 10min | 30 min |
| Ostrzeżenia meteo | `/api/data/warningsmeteo` | Ostrzeżenia wg kodu TERYT (województwo lub powiat) | 15 min |
| Ostrzeżenia hydro | `/api/data/warningshydro` | Ostrzeżenia hydrologiczne wg województwa | 15 min |

## Config Flow

```
Krok 1: Typ danych
  |- Synoptyczne / Hydrologiczne / Meteorologiczne -> Krok 2a
  |- Ostrzeżenia meteo -> Krok 2b
  |- Ostrzeżenia hydro -> Krok 2c

Krok 2a: Wybór stacji (lista z API, sortowana alfabetycznie)
Krok 2b: Województwo -> Powiat (lub "Całe województwo")
Krok 2c: Województwo

Krok 3: Interwał aktualizacji (5-120 min)
```

## Options Flow

Pozwala zmienić po konfiguracji:
- Stację pomiarową (synop/hydro/meteo)
- Województwo i powiat (ostrzeżenia meteo)
- Województwo (ostrzeżenia hydro)
- Interwał aktualizacji

## Sensory

### Synoptyczne (6)

| Sensor | Device class | Jednostka |
|--------|-------------|-----------|
| Temperatura | temperature | °C |
| Prędkość wiatru | wind_speed | m/s |
| Kierunek wiatru | - | ° |
| Wilgotność | humidity | % |
| Suma opadu | precipitation | mm |
| Ciśnienie | atmospheric_pressure | hPa |

### Hydrologiczne (4)

| Sensor | Device class | Jednostka |
|--------|-------------|-----------|
| Stan wody | - | cm |
| Przepływ | - | m³/s |
| Temperatura wody | temperature | °C |
| Zjawisko lodowe | - | - |

### Meteorologiczne (8)

| Sensor | Device class | Jednostka |
|--------|-------------|-----------|
| Temperatura powietrza | temperature | °C |
| Temperatura gruntu | temperature | °C |
| Średnia prędkość wiatru | wind_speed | m/s |
| Maks. prędkość wiatru | wind_speed | m/s |
| Porywy wiatru (10min) | wind_speed | m/s |
| Kierunek wiatru | - | ° |
| Wilgotność | humidity | % |
| Opad (10min) | precipitation | mm |

### Ostrzeżenia meteo (3)

| Sensor | Opis |
|--------|------|
| Liczba aktywnych | count |
| Najwyższy stopień | 1-3 |
| Ostatnie ostrzeżenie | treść, stopień, ważność w atrybutach |

### Ostrzeżenia hydro (3)

| Sensor | Opis |
|--------|------|
| Liczba aktywnych | count |
| Najwyższy stopień | wartość liczbowa |
| Ostatnie ostrzeżenie | zdarzenie, przebieg w atrybutach |

## Filtrowanie ostrzeżeń meteo

API warningsmeteo zwraca ostrzeżenia z 4-cyfrowym kodem TERYT (powiat). Integracja filtruje po `startswith`:
- Kod 2-cyfrowy (np. `12`) - całe województwo małopolskie
- Kod 4-cyfrowy (np. `1210`) - powiat nowosądecki

Ostrzeżenia hydro nie mają kodów TERYT powiatów - filtrowanie tylko po województwie.

## Struktura plików

```
custom_components/imgw_pib_monitor/
├── __init__.py          # Setup, ładowanie platform
├── manifest.json        # Manifest HA
├── config_flow.py       # Config Flow + Options Flow
├── const.py             # Stałe, kody województw
├── coordinator.py       # DataUpdateCoordinator
├── sensor.py            # Definicje sensorów
├── api.py               # Klient API IMGW
├── teryt.py             # Kody TERYT powiatów (380 powiatów)
├── strings.json         # Bazowe stringi (wymagane przez HA)
└── translations/
    ├── en.json
    └── pl.json
```

## Wymagania

- Home Assistant 2024.6+
- Python 3.12+
- aiohttp (wbudowane w HA)
- Brak klucza API