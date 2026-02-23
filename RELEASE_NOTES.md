# 🚀 IMGW-PIB Monitor v2.0.0

Pełna przebudowa integracji. Nowa architektura, nowe funkcje, ostrzeżenia pogodowe i prognoza pogody.

---

## ✨ Nowe funkcje

### Architektura
- **Globalny koordynator** — centralne pobieranie danych z rate limiting i deduplikacją zapytań. Wiele instancji integracji współdzieli jedno połączenie z API IMGW.
- **Koordynator instancji** — każda lokalizacja przetwarza tylko swoje dane, filtrowane po stacjach i regionach.
- **Migracja konfiguracji** — automatyczna migracja wpisów z v1.x do nowego formatu (wersja konfiguracji 8).

### Konfiguracja
- **Dwa tryby konfiguracji** — automatyczny (GPS) i manualny (wyszukiwanie po nazwie miejscowości).
- **Geokodowanie** — wyszukiwanie lokalizacji z podpowiedziami (gmina, powiat, województwo) przez Nominatim + IMGW API.
- **Auto-Discovery** — automatyczne wykrywanie i aktualizacja najbliższych stacji pomiarowych na podstawie lokalizacji HA.
- **Options Flow** — zmiana interwału aktualizacji (5-120 min) i zarządzanie prognozą pogody bez rekonfiguracji.

### Dane i sensory
- **5 źródeł danych** — synoptyczne (SYNOP), hydrologiczne, meteorologiczne, ostrzeżenia meteo, ostrzeżenia hydro.
- **Do 40 sensorów** — temperatura, wiatr, wilgotność, ciśnienie, stan wody, przepływ, zjawiska lodowe, odległość do stacji i więcej.
- **Ostrzeżenia meteorologiczne** — aktywne alerty z filtrowaniem po województwie lub powiecie (kody TERYT).
- **Ostrzeżenia hydrologiczne** — alerty powodziowe z filtrowaniem po powiecie.
- **Encja pogodowa** — opcjonalna prognoza dzienna i godzinowa (platforma `weather`).
- **Obliczanie odległości** — każdy sensor zawiera dystans do stacji pomiarowej.
- **Wiele instancji** — możliwość dodania integracji wielokrotnie dla różnych lokalizacji.

### Tłumaczenia
- Pełne tłumaczenia PL i EN dla interfejsu konfiguracji oraz nazw sensorów.

---

## 🐛 Poprawki błędów

- **Opisy ostrzeżeń** — sensory „Treść ostrzeżenia" i „Opis ostrzeżenia hydro" pokazują teraz opisy **wszystkich** aktywnych ostrzeżeń (połączone separatorem ` | `), a nie tylko najpoważniejszego.
- **Nazwy zdarzeń** — sensory „Zdarzenie meteorologiczne" i „Zdarzenie hydrologiczne" wyświetlają nazwy wszystkich aktywnych ostrzeżeń.
- **Config flow crash** — naprawiono niezdefiniowaną zmienną `location_name` w kroku wyszukiwania stacji (tryb manualny), który powodował crash przy braku stacji w pobliżu.
- **Precyzja zmiennoprzecinkowa** — poprawiono wyświetlanie wartości sensorów z nadmierną precyzją.

---

## ⚡ Wydajność

- **Usunięto `force_update`** — sensory nie wymuszają już zapisu do bazy danych przy każdym odświeżeniu, gdy wartość się nie zmieniła. Znacząco zmniejsza obciążenie bazy HA.
- **Rate limiting** — semafor z limitem 2 równoczesnych zapytań + 0.2s przerwy między wywołaniami API.
- **Deduplikacja** — współbieżne odświeżenia koordynatorów współdzielą wynik jednego zapytania (okno 30s).

---

## 🛡️ Jakość kodu

- **Węższe łapanie wyjątków** — `except Exception` zamieniono na `except (ImgwApiError, asyncio.TimeoutError)` w globalnym koordynatorze. Prawdziwe bugi nie będą już cicho połykane.
- **Walidacja odpowiedzi API** — dodano logowanie ostrzeżeń gdy API IMGW zwróci nieoczekiwany typ danych.
- **Wymaganie wersji HA** — dodano `"homeassistant": "2024.1.0"` do manifestu.
- **Eliminacja duplikacji** — wyekstrahowano wspólne funkcje wyszukiwania stacji w config flow.

---

## 🧪 Testy i CI/CD

- Pełny zestaw testów pytest: API, config flow, koordynator, sensory, stałe, utils, pogoda.
- Workflow GitHub Actions: HACS validation, hassfest, testy automatyczne.

---

## ⬆️ Aktualizacja z v1.x

Aktualizacja jest automatyczna. Wpisy konfiguracji zostaną zmigrowane do nowego formatu przy pierwszym uruchomieniu. Nie jest wymagana żadna ręczna interwencja.

---

## Wymagania

- Home Assistant 2024.1.0 lub nowszy
- HACS (do instalacji)

---

*Źródłem danych jest Instytut Meteorologii i Gospodarki Wodnej — Państwowy Instytut Badawczy (IMGW-PIB).*
