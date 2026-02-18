"""Constants for the IMGW-PIB Monitor integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "imgw_pib_monitor"
MANUFACTURER: Final = "Łukasz Kozik (lkozik@evilit.pl)"
ATTRIBUTION: Final = (
    "Źródłem pochodzenia danych jest Instytut Meteorologii "
    "i Gospodarki Wodnej – Państwowy Instytut Badawczy"
)

# API Base URL and Endpoints
API_BASE_URL: Final = "https://danepubliczne.imgw.pl/api/data"
API_ENDPOINT_SYNOP: Final = f"{API_BASE_URL}/synop"
API_ENDPOINT_HYDRO: Final = f"{API_BASE_URL}/hydro"
API_ENDPOINT_METEO: Final = f"{API_BASE_URL}/meteo"
API_ENDPOINT_WARNINGS_METEO: Final = f"{API_BASE_URL}/warningsmeteo"
API_ENDPOINT_WARNINGS_HYDRO: Final = f"{API_BASE_URL}/warningshydro"

# Config keys
CONF_STATION_ID: Final = "station_id"
CONF_STATION_NAME: Final = "station_name"
CONF_DATA_TYPE: Final = "data_type"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_VOIVODESHIP: Final = "voivodeship"
CONF_POWIAT: Final = "powiat"
CONF_POWIAT_NAME: Final = "powiat_name"
CONF_USE_POWIAT_FOR_WARNINGS: Final = "use_powiat_for_warnings"

# Setup Modes
CONF_SETUP_MODE: Final = "setup_mode"
SETUP_MODE_AUTO: Final = "auto"
SETUP_MODE_MANUAL: Final = "manual"

# New configuration keys for multi-sensor entries
CONF_AUTO_DETECT: Final = "auto_detect"
CONF_SELECTED_SYNOP: Final = "selected_synop"
CONF_SELECTED_HYDRO: Final = "selected_hydro"
CONF_SELECTED_METEO: Final = "selected_meteo"
CONF_ENABLE_WARNINGS_METEO: Final = "enable_warnings_meteo"
CONF_ENABLE_WARNINGS_HYDRO: Final = "enable_warnings_hydro"

# Data types (Legacy & Internal Mapping)
DATA_TYPE_SYNOP: Final = "synop"
DATA_TYPE_HYDRO: Final = "hydro"
DATA_TYPE_METEO: Final = "meteo"
DATA_TYPE_WARNINGS_METEO: Final = "warnings_meteo"
DATA_TYPE_WARNINGS_HYDRO: Final = "warnings_hydro"

DATA_TYPES: Final = {
    DATA_TYPE_SYNOP: "Dane synoptyczne",
    DATA_TYPE_HYDRO: "Dane hydrologiczne",
    DATA_TYPE_METEO: "Dane meteorologiczne",
    DATA_TYPE_WARNINGS_METEO: "Ostrzeżenia meteorologiczne",
    DATA_TYPE_WARNINGS_HYDRO: "Ostrzeżenia hydrologiczne",
}

# Default update intervals (minutes)
DEFAULT_UPDATE_INTERVAL: Final = 30
DEFAULT_UPDATE_INTERVAL_WARNINGS: Final = 15
MIN_UPDATE_INTERVAL: Final = 5
MAX_UPDATE_INTERVAL: Final = 120
DEFAULT_MAX_DISTANCE: Final = 50.0  # km for auto-detection

# TERYT codes and capital coordinates for voivodeships (first 2 digits)
VOIVODESHIPS: Final = {
    "02": "dolnośląskie",
    "04": "kujawsko-pomorskie",
    "06": "lubelskie",
    "08": "lubuskie",
    "10": "łódzkie",
    "12": "małopolskie",
    "14": "mazowieckie",
    "16": "opolskie",
    "18": "podkarpackie",
    "20": "podlaskie",
    "22": "pomorskie",
    "24": "śląskie",
    "26": "świętokrzyskie",
    "28": "warmińsko-mazurskie",
    "30": "wielkopolskie",
    "32": "zachodniopomorskie",
}

VOIVODESHIP_CAPITALS: Final = {
    "02": (51.1079, 17.0385),  # Wrocław
    "04": (53.1235, 18.0084),  # Bydgoszcz
    "06": (51.2465, 22.5666),  # Lublin
    "08": (52.7368, 15.2285),  # Gorzów Wlkp.
    "10": (51.7592, 19.4560),  # Łódź
    "12": (50.0647, 19.9450),  # Kraków
    "14": (52.2297, 21.0122),  # Warszawa
    "16": (50.6751, 17.9213),  # Opole
    "18": (50.0412, 21.9991),  # Rzeszów
    "20": (53.1325, 23.1688),  # Białystok
    "22": (54.3520, 18.6466),  # Gdańsk
    "24": (50.2649, 19.0238),  # Katowice
    "26": (50.8661, 20.6286),  # Kielce
    "28": (53.7784, 20.4801),  # Olsztyn
    "30": (52.4064, 16.9252),  # Poznań
    "32": (53.4285, 14.5528),  # Szczecin
}

# IMGW SYNOP stations coordinates (not provided by API)
# Updated based on IMGW API: https://danepubliczne.imgw.pl/api/data/synop
# Mapping: station_id -> (latitude, longitude)
SYNOP_STATIONS: Final[dict[str, tuple[float, float]]] = {
    "12001": (54.85, 18.67),  # Platforma
    "12100": (54.18, 15.58),  # Kołobrzeg
    "12105": (54.19, 16.17),  # Koszalin
    "12115": (54.58, 16.86),  # Ustka
    "12120": (54.76, 17.56),  # Łeba
    "12125": (54.54, 17.75),  # Lębork
    "12135": (54.61, 18.80),  # Hel
    "12155": (54.35, 18.65),  # Gdańsk
    "12160": (54.16, 19.40),  # Elbląg
    "12185": (54.08, 21.38),  # Kętrzyn
    "12195": (54.10, 22.93),  # Suwałki
    "12200": (53.91, 14.25),  # Świnoujście
    "12205": (53.43, 14.55),  # Szczecin
    "12210": (53.77, 15.40),  # Resko
    "12215": (53.71, 16.69),  # Szczecinek
    "12230": (53.15, 16.74),  # Piła
    "12235": (53.70, 17.56),  # Chojnice
    "12250": (53.01, 18.60),  # Toruń
    "12270": (53.11, 20.38),  # Mława
    "12272": (53.78, 20.48),  # Olsztyn
    "12280": (53.80, 21.57),  # Mikołajki
    "12285": (53.08, 21.57),  # Ostrołęka
    "12295": (53.13, 23.17),  # Białystok
    "12300": (52.74, 15.23),  # Gorzów
    "12310": (52.35, 14.56),  # Słubice
    "12330": (52.41, 16.93),  # Poznań
    "12345": (52.20, 18.64),  # Koło
    "12360": (52.55, 19.71),  # Płock
    "12375": (52.23, 21.01),  # Warszawa
    "12385": (52.17, 22.29),  # Siedlce
    "12399": (52.08, 23.62),  # Terespol
    "12400": (51.94, 15.51),  # Zielona Góra
    "12415": (51.21, 16.16),  # Legnica
    "12418": (51.84, 16.57),  # Leszno
    "12424": (51.11, 17.03),  # Wrocław
    "12435": (51.76, 18.09),  # Kalisz
    "12455": (51.22, 18.57),  # Wieluń
    "12465": (51.76, 19.46),  # Łódź
    "12469": (51.35, 19.88),  # Sulejów
    "12488": (51.55, 21.55),  # Kozienice
    "12495": (51.25, 22.57),  # Lublin
    "12497": (51.55, 23.55),  # Włodawa
    "12500": (50.90, 15.72),  # Jelenia Góra
    "12510": (50.74, 15.74),  # Śnieżka
    "12520": (50.44, 16.65),  # Kłodzko
    "12530": (50.67, 17.93),  # Opole
    "12540": (50.09, 18.22),  # Racibórz
    "12550": (50.81, 19.12),  # Częstochowa
    "12560": (50.26, 19.02),  # Katowice
    "12566": (50.06, 19.94),  # Kraków
    "12570": (50.87, 20.63),  # Kielce
    "12575": (50.01, 21.01),  # Tarnów
    "12580": (50.04, 22.00),  # Rzeszów
    "12585": (50.68, 21.75),  # Sandomierz
    "12595": (50.72, 23.25),  # Zamość
    "12600": (49.82, 19.05),  # Bielsko Biała
    "12625": (49.30, 19.95),  # Zakopane
    "12650": (49.23, 19.98),  # Kasprowy Wierch
    "12660": (49.62, 20.71),  # Nowy Sącz
    "12670": (49.69, 21.77),  # Krosno
    "12690": (49.47, 22.33),  # Lesko
    "12695": (49.78, 22.77),  # Przemyśl
}

# Forecast (weather entity) config
CONF_ENABLE_WEATHER_FORECAST: Final = "enable_weather_forecast"
CONF_FORECAST_LAT: Final = "forecast_lat"
CONF_FORECAST_LON: Final = "forecast_lon"
CONF_LOCATION_NAME: Final = "location_name"

# Forecast API (IMGW Proxy)
FORECAST_API_URL: Final = "https://imgw-api-proxy.evtlab.pl"
FORECAST_UPDATE_INTERVAL: Final = 600  # 10 minutes, in seconds

# Frontend
FRONTEND_URL_BASE: Final = "/imgw-pib-monitor"

# IMGW icon → HA condition mapping
ICON_TO_CONDITION: Final = {
    ("clear", "d"): "sunny",
    ("clear", "n"): "clear-night",
    ("partly", "d"): "partlycloudy",
    ("partly", "n"): "partlycloudy",
    ("cloudy", "d"): "cloudy",
    ("cloudy", "n"): "cloudy",
    ("rain_light", "d"): "rainy",
    ("rain_light", "n"): "rainy",
    ("rain_heavy", "d"): "pouring",
    ("rain_heavy", "n"): "pouring",
    ("snow", "d"): "snowy",
    ("snow", "n"): "snowy",
    ("sleet", "d"): "snowy-rainy",
    ("sleet", "n"): "snowy-rainy",
}


def parse_imgw_icon(icon: str) -> str | None:
    """Parse IMGW icon code to HA weather condition.

    Format: n{cloud}z{precip}{d/n} e.g. n4z61d
    """
    if not icon or not isinstance(icon, str) or len(icon) < 6:
        return None

    try:
        if icon[0] == "n" and icon[2] == "z":
            cloud = int(icon[1])
            precip = int(icon[3:5])
            time_of_day = icon[-1] if icon[-1] in ("d", "n") else "d"
        else:
            return None
    except (ValueError, IndexError):
        return None

    if precip >= 80:
        precip_type = "rain_heavy"
    elif 70 <= precip < 80:
        precip_type = "snow"
    elif 60 <= precip < 70:
        precip_type = "rain_light"
    elif precip > 0:
        precip_type = "rain_light"
    else:
        precip_type = "none"

    if precip_type != "none":
        return ICON_TO_CONDITION.get((precip_type, time_of_day), "rainy")

    if cloud <= 1:
        key = ("clear", time_of_day)
    elif cloud <= 5:
        key = ("partly", time_of_day)
    else:
        key = ("cloudy", time_of_day)

    return ICON_TO_CONDITION.get(key, "cloudy")
