# IMGW-PIB Monitor dla Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/abnvle/ha-imgw-pib-monitor)](https://github.com/abnvle/ha-imgw-pib-monitor/releases)
[![Downloads](https://img.shields.io/github/downloads/abnvle/ha-imgw-pib-monitor/total)](https://github.com/abnvle/ha-imgw-pib-monitor/releases)
[![License: MIT](https://img.shields.io/github/license/abnvle/ha-imgw-pib-monitor)](https://github.com/abnvle/ha-imgw-pib-monitor/blob/main/LICENSE)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/abnvle/ha-imgw-pib-monitor/hacs-validation.yml?label=HACS%20Validation)](https://github.com/abnvle/ha-imgw-pib-monitor/actions/workflows/hacs-validation.yml)
[![Hassfest](https://img.shields.io/github/actions/workflow/status/abnvle/ha-imgw-pib-monitor/hassfest.yml?label=Hassfest)](https://github.com/abnvle/ha-imgw-pib-monitor/actions/workflows/hassfest.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/abnvle/ha-imgw-pib-monitor/tests.yml?label=Tests)](https://github.com/abnvle/ha-imgw-pib-monitor/actions/workflows/tests.yml)

[English version](README_EN.md)

Integracja Home Assistant wykorzystująca publiczne dane IMGW-PIB (Instytut Meteorologii i Gospodarki Wodnej - Państwowy Instytut Badawczy). Dostarcza dane pogodowe, hydrologiczne i ostrzeżenia dla dowolnej lokalizacji w Polsce.

[![Otwórz repozytorium w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=abnvle&repository=ha-imgw-pib-monitor&category=integration)

## Funkcje

### Podstawowe

- **Dwa tryby konfiguracji** - automatyczny (GPS) lub manualny (wpisanie lokalizacji)
- **Config Flow UI** - konfiguracja przez interfejs, zero YAML
- **5 źródeł danych** - synoptyczne, hydrologiczne, meteorologiczne, ostrzeżenia meteo, ostrzeżenia hydro
- **Do 40 sensorów** - temperatura, wiatr, wilgotność, ciśnienie, stan wody, przepływ, ostrzeżenia i inne
- **Encja pogodowa** - prognoza pogody (dzienna i godzinowa) z IMGW-PIB jako encja weather
- **Wiele instancji** - możliwość dodania integracji wielokrotnie dla różnych lokalizacji
- **Tłumaczenia PL/EN**
- **Bez klucza API** - dane z publicznego API IMGW-PIB

### Zaawansowane

- **Auto-Discovery** - automatyczne wykrywanie i aktualizacja najbliższych stacji na podstawie lokalizacji Home Assistant
- **Geokodowanie** - wyszukiwanie lokalizacji po nazwie z podpowiedziami (gmina, powiat, województwo)
- **Filtrowanie ostrzeżeń według powiatu** - precyzyjne filtrowanie ostrzeżeń meteorologicznych i hydrologicznych z kodami TERYT
- **Automatyczne wykrywanie województwa i powiatu** - system sam rozpoznaje region na podstawie współrzędnych
- **Obliczanie odległości** - każdy sensor pokazuje odległość do stacji pomiarowej
- **Globalny koordynator** - centralne pobieranie danych z rate limiting, oszczędność zapytań do API
- **Options Flow** - zmiana interwału aktualizacji i włączanie/wyłączanie prognozy pogody w dowolnym momencie (5-120 minut)
- **Współrzędne geograficzne** - wszystkie sensory zawierają współrzędne stacji w atrybutach
- **Prognoza pogody** - opcjonalna encja pogodowa z prognozą dzienną i godzinową (dane z IMGW API Proxy)

## Zrzuty ekranu

### Wpisy integracji
Każda lokalizacja tworzy osobne urządzenia — stacje pomiarowe, ostrzeżenia i prognozę pogody.

![Wpisy integracji](docs/integration_entries.png)

---

<table>
<tr>
<td width="50%">

### Prognoza pogody
Encja weather z aktualną pogodą, prognozą dzienną i godzinową.

![Prognoza pogody](docs/weather_forecast.png)

</td>
<td width="50%">

### Ostrzeżenia meteorologiczne
8 sensorów dla każdego typu ostrzeżeń — od liczby aktywnych po pełną treść.

![Ostrzeżenia meteo](docs/meteo_warnings.png)

</td>
</tr>
</table>

---

### Dane hydrologiczne
Sensory pomiarowe (poziom wody, przepływ, zjawisko lodowe) i diagnostyczne (ID stacji, odległość).

![Dane hydrologiczne](docs/hydro_data.png)

## Tryby konfiguracji

### Tryb automatyczny (Auto-Discovery)

System wykorzystuje współrzędne GPS z konfiguracji Home Assistant. Po wybraniu tego trybu integracja automatycznie wyszukuje najbliższe stacje pomiarowe wszystkich typów (synoptyczne, hydrologiczne, meteorologiczne) w promieniu 50 km. W kolejnym kroku możesz wybrać, które typy danych chcesz monitorować.

Funkcje trybu automatycznego:
- Automatyczne wykrywanie najbliższej stacji dla każdego typu danych
- Dynamiczna aktualizacja stacji jeśli zmieni się lokalizacja Home Assistant
- Automatyczne rozpoznanie województwa i powiatu dla ostrzeżeń
- Jeden wpis integracji obsługuje wszystkie wybrane typy danych

### Tryb manualny

System pyta o nazwę miejscowości lub adres. Po wpisaniu nazwa jest wyszukiwana przez IMGW API Proxy, które zwraca listę propozycji z pełnymi szczegółami (nazwa miejscowości, gmina, powiat, województwo, kod TERYT). Po wybraniu lokalizacji system wyszukuje najbliższe stacje pomiarowe.

Funkcje trybu manualnego:
- Wyszukiwanie lokalizacji po nazwie z danymi z IMGW API
- Automatyczne pobieranie kodu TERYT powiatu z API
- Automatyczne rozpoznanie województwa i powiatu
- Możliwość wybrania dowolnej lokalizacji w Polsce
- Sortowanie wyników według rangi (najważniejsze miejscowości na górze)
- Jeden wpis integracji obsługuje wszystkie wybrane typy danych

## Sensory

### Synoptyczne (8 sensorów)

| Sensor | Jednostka | Typ |
|---|---|---|
| Temperatura | °C | Pomiar |
| Prędkość wiatru | m/s | Pomiar |
| Kierunek wiatru | ° | Pomiar |
| Wilgotność | % | Pomiar |
| Suma opadu | mm | Pomiar |
| Ciśnienie atmosferyczne | hPa | Pomiar |
| ID stacji synop | - | Diagnostyczny |
| Odległość synop | km | Diagnostyczny |

Atrybuty: nazwa stacji, ID stacji, data pomiaru, godzina pomiaru, współrzędne geograficzne, odległość

### Hydrologiczne (6 sensorów)

| Sensor | Jednostka | Typ |
|---|---|---|
| Stan wody | cm | Pomiar |
| Przepływ wody | m³/s | Pomiar |
| Temperatura wody | °C | Pomiar |
| Zjawisko lodowe | kod | Pomiar |
| ID stacji hydro | - | Diagnostyczny |
| Odległość hydro | km | Diagnostyczny |

Atrybuty: nazwa stacji, ID stacji, nazwa rzeki, województwo, współrzędne geograficzne, odległość, daty pomiarów dla poszczególnych parametrów

### Meteorologiczne (10 sensorów)

| Sensor | Jednostka | Typ |
|---|---|---|
| Temperatura powietrza | °C | Pomiar |
| Temperatura gruntu | °C | Pomiar |
| Średnia prędkość wiatru | m/s | Pomiar |
| Maksymalna prędkość wiatru | m/s | Pomiar |
| Porywy wiatru (10 min) | m/s | Pomiar |
| Kierunek wiatru | ° | Pomiar |
| Wilgotność | % | Pomiar |
| Opad (10 min) | mm | Pomiar |
| ID stacji meteo | - | Diagnostyczny |
| Odległość meteo | km | Diagnostyczny |

Atrybuty: nazwa stacji, kod stacji, współrzędne geograficzne, odległość

### Ostrzeżenia meteorologiczne (8 sensorów)

| Sensor | Opis | Typ |
|---|---|---|
| Liczba aktywnych ostrzeżeń | Ilość bieżących ostrzeżeń | Pomiar |
| Najwyższy stopień ostrzeżenia | Najwyższy aktywny poziom (1-3) | - |
| Nazwa ostatniego zdarzenia | Nazwa najpoważniejszego ostrzeżenia | - |
| Stopień ostatniego ostrzeżenia | Poziom najpoważniejszego ostrzeżenia | - |
| Prawdopodobieństwo | Prawdopodobieństwo ostatniego ostrzeżenia (%) | - |
| Ważne od | Data początku ważności ostatniego ostrzeżenia | - |
| Ważne do | Data końca ważności ostatniego ostrzeżenia | - |
| Treść ostrzeżenia | Treść ostatniego ostrzeżenia (max 255 znaków) | - |

Sensor "Liczba aktywnych ostrzeżeń" zawiera w atrybucie `warnings` pełną listę wszystkich aktywnych ostrzeżeń.

Ostrzeżenia można filtrować według:
- Województwa (16 województw)
- Powiatu (dokładniejsze filtrowanie) - opcjonalne

### Ostrzeżenia hydrologiczne (8 sensorów)

| Sensor | Opis | Typ |
|---|---|---|
| Liczba aktywnych ostrzeżeń | Ilość bieżących ostrzeżeń hydro | Pomiar |
| Najwyższy stopień ostrzeżenia hydro | Najwyższy aktywny poziom | - |
| Nazwa ostatniego zdarzenia hydro | Nazwa/opis najpoważniejszego ostrzeżenia | - |
| Stopień ostatniego ostrzeżenia hydro | Poziom najpoważniejszego ostrzeżenia | - |
| Prawdopodobieństwo hydro | Prawdopodobieństwo ostatniego ostrzeżenia (%) | - |
| Ważne od hydro | Data początku ważności | - |
| Ważne do hydro | Data końca ważności | - |
| Opis ostrzeżenia hydro | Opis przebiegu ostrzeżenia (max 255 znaków) | - |

Sensor "Liczba aktywnych ostrzeżeń" zawiera w atrybucie `warnings` pełną listę wszystkich aktywnych ostrzeżeń hydrologicznych.

Ostrzeżenia można filtrować według:
- Województwa (16 województw)
- Powiatu (wyszukiwanie w opisie obszarów) - opcjonalne

### Prognoza pogody (encja weather)

Opcjonalna encja pogodowa `weather.*` z danymi z IMGW API Proxy. Obsługuje:

| Właściwość | Opis |
|---|---|
| Warunki pogodowe | Na podstawie ikony IMGW (słonecznie, pochmurno, deszcz itp.) |
| Temperatura | Bieżąca temperatura powietrza (°C) |
| Temperatura odczuwalna | Temperatura odczuwalna (°C) |
| Wilgotność | Wilgotność powietrza (%) |
| Ciśnienie | Ciśnienie atmosferyczne (hPa) |
| Prędkość wiatru | Prędkość wiatru (m/s) |
| Porywy wiatru | Prędkość porywów wiatru (m/s) |
| Kierunek wiatru | Kierunek wiatru (°) |
| Zachmurzenie | Stopień zachmurzenia (%) |

Dodatkowe atrybuty: opady, opady śniegu, wschód/zachód słońca, ikona IMGW, model prognozy.

Prognozy:
- **Dzienna** - temperatura max/min, wiatr, opady (grupowanie dzień/noc)
- **Godzinowa** - pełne dane pogodowe na każdą godzinę

## Instalacja

### HACS (zalecane)

1. Otwórz HACS w Home Assistant
2. Kliknij **⋮** - **Custom repositories**
3. Dodaj `https://github.com/abnvle/ha-imgw-pib-monitor` z kategorią **Integration**
4. Wyszukaj **IMGW-PIB Monitor** i zainstaluj
5. Uruchom ponownie Home Assistant

### Ręczna

1. Pobierz repozytorium
2. Skopiuj `custom_components/imgw_pib_monitor` do katalogu `custom_components/`
3. Uruchom ponownie Home Assistant

## Konfiguracja

### Tryb automatyczny

1. Przejdź do **Ustawienia - Urządzenia i usługi - Dodaj integrację**
2. Wyszukaj **IMGW-PIB Monitor**
3. Wybierz **Automatyczny (GPS)**
4. System znajdzie najbliższe stacje dla wszystkich typów danych
5. Zaznacz typy danych, które chcesz monitorować:
   - Dane synoptyczne (pogoda)
   - Dane meteorologiczne (szczegółowa meteorologia)
   - Dane hydrologiczne (rzeki)
   - Ostrzeżenia meteorologiczne
   - Ostrzeżenia hydrologiczne
6. Dla ostrzeżeń możesz opcjonalnie włączyć filtrowanie po powiecie
7. Opcjonalnie włącz prognozę pogody (encja weather)
8. Potwierdź konfigurację

### Tryb manualny

1. Przejdź do **Ustawienia - Urządzenia i usługi - Dodaj integrację**
2. Wyszukaj **IMGW-PIB Monitor**
3. Wybierz **Manualny (wpisanie lokalizacji)**
4. Wpisz nazwę miejscowości lub adres
5. Wybierz odpowiednią lokalizację z listy podpowiedzi
6. System znajdzie najbliższe stacje dla wszystkich typów danych
7. Zaznacz typy danych, które chcesz monitorować
8. Dla ostrzeżeń możesz opcjonalnie włączyć filtrowanie po powiecie
9. Opcjonalnie włącz prognozę pogody (encja weather)
10. Potwierdź konfigurację

### Wiele instancji

Możesz dodać integrację wielokrotnie dla różnych lokalizacji. Każda instancja działa niezależnie i może monitorować inne typy danych.

## Opcje

Po dodaniu integracji możesz zmienić ustawienia:

1. Przejdź do **Ustawienia - Urządzenia i usługi**
2. Znajdź wpis **IMGW-PIB Monitor**
3. Kliknij **KONFIGURUJ**
4. Ustaw nowy interwał aktualizacji (5-120 minut)
5. Włącz lub wyłącz prognozę pogody (encja weather)

Domyślny interwał aktualizacji: 30 minut. Globalny koordynator synchronizuje się z najkrótszym interwałem spośród wszystkich instancji.

## Jak działa globalny koordynator

Integracja wykorzystuje dwustopniową architekturę koordynatorów:

1. **Globalny koordynator** - pobiera wszystkie dane z API IMGW-PIB. Interwał jest synchronizowany z najkrótszym interwałem spośród wszystkich instancji integracji. Używa rate limiting (2 równoczesne zapytania z opóźnieniem 200ms) aby nie obciążać API.

2. **Koordynatory instancji** - każda instancja integracji ma własny koordynator, który filtruje dane z globalnego koordynatora i przygotowuje je dla swoich sensorów. Aktualizacje odbywają się zgodnie z ustawionym interwałem.

3. **Koordynator prognozy** (opcjonalny) - osobny koordynator pobierający prognozę pogody z IMGW API Proxy dla encji weather.

Korzyści:
- Jedno zapytanie do API obsługuje wszystkie instancje integracji
- Zmniejszone obciążenie API IMGW-PIB
- Lepsza wydajność Home Assistant
- Możliwość częstszych aktualizacji bez obawy o przeciążenie API

## Kody TERYT

Kody TERYT powiatów i ich nazwy są pobierane bezpośrednio z IMGW API Proxy podczas konfiguracji. Integracja nie zawiera lokalnej bazy kodów - dzięki temu zawsze korzysta z aktualnych danych, bez konieczności aktualizacji po zmianach administracyjnych.

Kody TERYT są używane do:
- Filtrowania ostrzeżeń meteorologicznych (API zwraca ostrzeżenia z kodami TERYT)
- Filtrowania ostrzeżeń hydrologicznych (wyszukiwanie nazwy powiatu w opisie obszarów)
- Automatycznego wykrywania powiatu na podstawie geokodowania

Format kodu TERYT: `AABB` gdzie:
- `AA` - kod województwa (02-32)
- `BB` - kod powiatu (01-99)

Przykłady:
- `1201` - powiat bocheński (woj. małopolskie)
- `1261` - m. Kraków (miasto na prawach powiatu)
- `1465` - m. Warszawa

## Współrzędne stacji

### Stacje synoptyczne (SYNOP)

API IMGW-PIB nie zwraca współrzędnych dla stacji synoptycznych. Integracja zawiera twardo zakodowaną bazę współrzędnych dla wszystkich 64 stacji synoptycznych w Polsce. Współrzędne są używane do:
- Obliczania odległości do stacji
- Automatycznego wyboru najbliższej stacji w trybie auto-discovery
- Wyświetlania lokalizacji stacji w atrybutach sensorów

### Stacje hydrologiczne i meteorologiczne

Dla tych stacji współrzędne są pobierane bezpośrednio z API IMGW-PIB.

## Automatyczne aktualizacje w trybie Auto-Discovery

W trybie automatycznym integracja na bieżąco sprawdza, czy nie zmieniła się lokalizacja Home Assistant. Jeśli wykryje zmianę współrzędnych GPS, automatycznie aktualizuje wybrane stacje na najbliższe dostępne. Dzięki temu:
- Integracja działa poprawnie po zmianie lokalizacji (np. przeniesienie instalacji)
- Zawsze korzystasz z danych z najbliższych stacji
- Nie musisz ręcznie rekonfigurować integracji

Aktualizacja dotyczy tylko typów danych, które były włączone podczas konfiguracji.

## Automatyczne wykrywanie regionu

System automatycznie wykrywa województwo i powiat na podstawie:

### W trybie automatycznym
- Danych z IMGW API Proxy (reverse geocoding - współrzędne GPS -> najbliższa lokalizacja)
- API zwraca nazwę województwa, powiatu i kod TERYT
- Fallback: odległość do stolic województw jeśli API nie zwróci danych

### W trybie manualnym
- Danych z IMGW API Proxy (nazwa lokalizacji zawiera województwo, powiat, kod TERYT)
- Kod TERYT powiatu i nazwa są pobierane bezpośrednio z API

Wykryty region jest używany do:
- Filtrowania ostrzeżeń meteorologicznych i hydrologicznych według kodu TERYT
- Wyświetlania informacji w nazwach urządzeń
- Automatycznej konfiguracji ostrzeżeń

## Przykłady automatyzacji

### Powiadomienie o nowym ostrzeżeniu meteo

```yaml
automation:
  - alias: "Ostrzeżenie IMGW"
    trigger:
      - platform: numeric_state
        entity_id: sensor.imgw_auto_discovery_warnings_meteo_count
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "Ostrzeżenie meteorologiczne"
          message: >
            {{ state_attr('sensor.imgw_auto_discovery_warnings_meteo_latest', 'event') }}
            Stopień: {{ state_attr('sensor.imgw_auto_discovery_warnings_meteo_latest', 'level') }}
            Ważne: {{ state_attr('sensor.imgw_auto_discovery_warnings_meteo_latest', 'valid_from') }} - {{ state_attr('sensor.imgw_auto_discovery_warnings_meteo_latest', 'valid_to') }}
```

### Alert mrozowy

```yaml
automation:
  - alias: "Alert mrozowy"
    trigger:
      - platform: numeric_state
        entity_id: sensor.imgw_auto_discovery_temperature
        below: -15
    action:
      - service: notify.mobile_app
        data:
          title: "Silny mróz"
          message: "Temperatura spadła do {{ states('sensor.imgw_auto_discovery_temperature') }}°C w {{ state_attr('sensor.imgw_auto_discovery_temperature', 'station_name') }}"
```

### Alert wysokiego stanu wody

```yaml
automation:
  - alias: "Alert stan wody"
    trigger:
      - platform: numeric_state
        entity_id: sensor.imgw_auto_discovery_water_level
        above: 500
    action:
      - service: notify.mobile_app
        data:
          title: "Wysoki stan wody"
          message: >
            Stan wody w {{ state_attr('sensor.imgw_auto_discovery_water_level', 'river') }}
            w {{ state_attr('sensor.imgw_auto_discovery_water_level', 'station_name') }}
            wynosi {{ states('sensor.imgw_auto_discovery_water_level') }} cm
```

### Powiadomienie o silnym wietrze

```yaml
automation:
  - alias: "Alert silny wiatr"
    trigger:
      - platform: numeric_state
        entity_id: sensor.imgw_auto_discovery_wind_speed
        above: 15
    action:
      - service: notify.mobile_app
        data:
          title: "Silny wiatr"
          message: "Prędkość wiatru: {{ states('sensor.imgw_auto_discovery_wind_speed') }} m/s ({{ (states('sensor.imgw_auto_discovery_wind_speed') | float * 3.6) | round(0) }} km/h)"
```

### Dashboard z ostrzeżeniami i pogodą

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Ostrzeżenia IMGW
    entities:
      - entity: sensor.imgw_auto_discovery_warnings_meteo_count
        name: Aktywne ostrzeżenia meteo
      - entity: sensor.imgw_auto_discovery_warnings_meteo_max_level
        name: Najwyższy stopień
      - entity: sensor.imgw_auto_discovery_warnings_meteo_latest
        name: Ostatnie ostrzeżenie
      - entity: sensor.imgw_auto_discovery_warnings_hydro_count
        name: Aktywne ostrzeżenia hydro
  - type: weather-forecast
    entity: weather.home
  - type: entities
    title: Dane IMGW
    entities:
      - entity: sensor.imgw_auto_discovery_temperature
        name: Temperatura
      - entity: sensor.imgw_auto_discovery_wind_speed
        name: Wiatr
      - entity: sensor.imgw_auto_discovery_humidity
        name: Wilgotność
      - entity: sensor.imgw_auto_discovery_pressure
        name: Ciśnienie
```

## Limity API i optymalizacja

API IMGW-PIB nie wymaga klucza i nie ma oficjalnych limitów, ale warto zachować rozsądek:

- **Globalny koordynator** pobiera dane zgodnie z najkrótszym interwałem instancji (domyślnie 30 minut)
- **Rate limiting** - maksymalnie 2 równoczesne zapytania z opóźnieniem 200ms
- **Cache** - wszystkie instancje używają tych samych danych
- **Timeout** - timeout po 30 sekundach

Zalecenia:
- Nie ustawiaj interwału poniżej 5 minut
- Dla wielu instancji używaj tego samego interwału
- Dane z API są aktualizowane co godzinę, nie ma sensu odpytywać częściej niż co 15 minut

## Rozwiązywanie problemów

### Brak stacji w okolicy

Jeśli system nie znajduje żadnych stacji w promieniu 50 km:
- Sprawdź czy współrzędne GPS w Home Assistant są poprawne
- Spróbuj trybu manualnego i wpisz najbliższą dużą miejscowość
- Niektóre typy stacji (zwłaszcza hydrologiczne) nie są dostępne wszędzie

### Niepoprawne dane

Jeśli sensory pokazują `unavailable` lub `None`:
- Sprawdź logi Home Assistant (`Ustawienia - System - Logi`)
- Niektóre stacje nie raportują wszystkich parametrów
- API IMGW-PIB czasami zwraca puste wartości

### Ostrzeżenia nie są filtrowane po powiecie

- Sprawdź czy powiat został wykryty (informacja w logach)
- Dla ostrzeżeń hydro filtrowanie działa tylko jeśli nazwa powiatu występuje w opisie obszarów
- Możesz wyłączyć filtrowanie po powiecie i zostawić samo województwo

### Dane nie aktualizują się

- Sprawdź interwał aktualizacji w opcjach integracji
- Sprawdź czy globalny koordynator pobiera dane (logi)
- Sprawdź połączenie internetowe Home Assistant

## Źródło danych

Dane pochodzą z publicznego API IMGW-PIB:
- `https://danepubliczne.imgw.pl/api/data/synop`
- `https://danepubliczne.imgw.pl/api/data/hydro`
- `https://danepubliczne.imgw.pl/api/data/meteo`
- `https://danepubliczne.imgw.pl/api/data/warningsmeteo`
- `https://danepubliczne.imgw.pl/api/data/warningshydro`

Prognoza pogody:
- `https://imgw-api-proxy.evtlab.pl/forecast`

> Źródłem pochodzenia danych pomiarowych jest Instytut Meteorologii i Gospodarki Wodnej - Państwowy Instytut Badawczy.

## Autor

**Łukasz Kozik** - [lkozik@evilit.pl](mailto:lkozik@evilit.pl)

## Podziękowania

Dziękuję [Allon](https://github.com/AllonGit/) za pomoc w tworzeniu integracji.

## Licencja

[MIT](https://github.com/abnvle/ha-imgw-pib-monitor/blob/main/LICENSE)
