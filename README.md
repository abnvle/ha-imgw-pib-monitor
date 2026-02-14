# IMGW-PIB Monitor dla Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/abnvle/ha-imgw-pib-monitor)](https://github.com/abnvle/ha-imgw-pib-monitor/releases)
[![Downloads](https://img.shields.io/github/downloads/abnvle/ha-imgw-pib-monitor/total)](https://github.com/abnvle/ha-imgw-pib-monitor/releases)
[![License: MIT](https://img.shields.io/github/license/abnvle/ha-imgw-pib-monitor?v=2)](https://github.com/abnvle/ha-imgw-pib-monitor/blob/main/LICENSE)

[English version](README_EN.md)

Integracja Home Assistant dla danych publicznych [IMGW-PIB](https://danepubliczne.imgw.pl/) (Instytut Meteorologii i Gospodarki Wodnej — Państwowy Instytut Badawczy).

## Funkcje

- **Config Flow UI** — dodawanie przez Ustawienia → Integracje, bez YAML
- **5 źródeł danych** — synoptyczne, hydrologiczne, meteorologiczne, ostrzeżenia meteo, ostrzeżenia hydro
- **24 sensory** — temperatura, wiatr, wilgotność, ciśnienie, stan wody, przepływ i więcej
- **Ostrzeżenia meteo wg powiatu** — filtrowanie ostrzeżeń do poziomu powiatu (kody TERYT)
- **Options Flow** — zmiana stacji, regionu lub interwału w dowolnym momencie
- **Wiele instancji** — dodaj integrację wielokrotnie dla różnych stacji i typów danych
- **Tłumaczenia PL/EN**
- **Bez klucza API** — korzysta z publicznie dostępnych danych

## Zrzuty ekranu

| Wpisy integracji | Ostrzeżenia meteo | Dane meteorologiczne |
|:---:|:---:|:---:|
| ![Integracje](docs/integrations.png) | ![Ostrzeżenia](docs/warnings.png) | ![Meteo](docs/meteo.png) |

## Sensory

### Synoptyczne (6 sensorów)

| Sensor | Jednostka |
|---|---|
| Temperatura | °C |
| Prędkość wiatru | m/s |
| Kierunek wiatru | ° |
| Wilgotność | % |
| Suma opadu | mm |
| Ciśnienie atmosferyczne | hPa |

### Hydrologiczne (4 sensory)

| Sensor | Jednostka |
|---|---|
| Stan wody | cm |
| Przepływ wody | m³/s |
| Temperatura wody | °C |
| Zjawisko lodowe | kod |

### Meteorologiczne (8 sensorów)

| Sensor | Jednostka |
|---|---|
| Temperatura powietrza | °C |
| Temperatura gruntu | °C |
| Średnia prędkość wiatru | m/s |
| Maksymalna prędkość wiatru | m/s |
| Porywy wiatru (10 min) | m/s |
| Kierunek wiatru | ° |
| Wilgotność | % |
| Opad (10 min) | mm |

### Ostrzeżenia meteorologiczne (3 sensory)

| Sensor | Opis |
|---|---|
| Liczba aktywnych ostrzeżeń | Ilość bieżących ostrzeżeń |
| Najwyższy stopień ostrzeżenia | Najwyższy aktywny poziom (1–3) |
| Ostatnie ostrzeżenie | Najpoważniejsze ostrzeżenie ze szczegółami w atrybutach |

### Ostrzeżenia hydrologiczne (3 sensory)

| Sensor | Opis |
|---|---|
| Liczba aktywnych ostrzeżeń | Ilość bieżących ostrzeżeń |
| Najwyższy stopień ostrzeżenia | Najwyższy aktywny poziom |
| Ostatnie ostrzeżenie | Najpoważniejsze ostrzeżenie ze szczegółami w atrybutach |

## Instalacja

### HACS (zalecane)

1. Otwórz HACS w Home Assistant
2. Kliknij **⋮** → **Custom repositories**
3. Dodaj `https://github.com/abnvle/ha-imgw-pib-monitor` z kategorią **Integration**
4. Wyszukaj **IMGW-PIB Monitor** i zainstaluj
5. Uruchom ponownie Home Assistant

### Ręczna

1. Pobierz [najnowszą wersję](https://github.com/abnvle/ha-imgw-pib-monitor/releases)
2. Skopiuj `custom_components/imgw_pib_monitor` do katalogu `custom_components/`
3. Uruchom ponownie Home Assistant

## Konfiguracja

1. Przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację**
2. Wyszukaj **IMGW-PIB Monitor**
3. Wybierz typ danych
4. Wybierz stację lub region:
   - **Synoptyczne / Hydro / Meteo** → wybierz stację pomiarową
   - **Ostrzeżenia meteo** → wybierz województwo → wybierz powiat lub „Całe województwo"
   - **Ostrzeżenia hydro** → wybierz województwo
5. Ustaw interwał aktualizacji (5–120 minut)

Aby monitorować wiele stacji lub typów danych, dodaj integrację ponownie.

## Opcje

| Opcja | Domyślnie | Opis |
|---|---|---|
| Interwał aktualizacji | 30 min (dane) / 15 min (ostrzeżenia) | Częstotliwość odpytywania API |
| Stacja | — | Zmiana stacji pomiarowej |
| Województwo | — | Zmiana regionu ostrzeżeń |
| Powiat | Całe województwo | Zawężenie ostrzeżeń meteo do konkretnego powiatu |

## Przykłady automatyzacji

### Powiadomienie o ostrzeżeniu meteo
```yaml
automation:
  - alias: "Ostrzeżenie IMGW"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ostrzezenia_malopolskie_warnings_meteo_count
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Ostrzeżenie IMGW"
          message: >
            {{ state_attr('sensor.ostrzezenia_malopolskie_warnings_meteo_latest', 'content') }}
```

### Alert mrozowy
```yaml
automation:
  - alias: "Alert - mróz"
    trigger:
      - platform: numeric_state
        entity_id: sensor.imgw_synoptyczne_krakow_temperature
        below: -15
    action:
      - service: notify.mobile_app
        data:
          title: "🥶 Silny mróz!"
          message: "Temperatura spadła do {{ states('sensor.imgw_synoptyczne_krakow_temperature') }}°C"
```

## Źródło danych

Dane pochodzą z publicznego API IMGW-PIB:
- `https://danepubliczne.imgw.pl/api/data/synop`
- `https://danepubliczne.imgw.pl/api/data/hydro`
- `https://danepubliczne.imgw.pl/api/data/meteo`
- `https://danepubliczne.imgw.pl/api/data/warningsmeteo`
- `https://danepubliczne.imgw.pl/api/data/warningshydro`

> Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy.

## Autor

**Łukasz Kozik** — [lkozik@evilit.pl](mailto:lkozik@evilit.pl)

## Licencja

[MIT](https://github.com/abnvle/ha-imgw-pib-monitor/blob/main/LICENSE)