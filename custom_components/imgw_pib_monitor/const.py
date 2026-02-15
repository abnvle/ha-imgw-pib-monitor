"""Constants for the IMGW-PIB Monitor integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "imgw_pib_monitor"
MANUFACTURER: Final = "IMGW-PIB"
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
# Mapping: station_id -> (latitude, longitude)
SYNOP_STATIONS: Final[dict[str, tuple[float, float]]] = {
    "12001": (53.92, 14.23),  # Świnoujście
    "12100": (54.18, 16.14),  # Kołobrzeg
    "12105": (54.21, 16.16),  # Koszalin
    "12115": (54.59, 16.85),  # Ustka
    "12120": (54.55, 17.75),  # Lębork
    "12125": (54.75, 18.51),  # Hel
    "12135": (53.77, 15.42),  # Resko
    "12155": (54.38, 18.47),  # Gdańsk
    "12160": (54.17, 19.43),  # Elbląg
    "12195": (54.13, 22.95),  # Suwałki
    "12205": (53.40, 14.62),  # Szczecin
    "12210": (53.10, 17.98),  # Bydgoszcz
    "12215": (53.71, 16.68),  # Szczecinek
    "12230": (53.03, 18.59),  # Toruń
    "12235": (52.81, 18.50),  # Ciechocinek
    "12250": (53.03, 18.59),  # Toruń (duplicate check)
    "12270": (53.11, 20.36),  # Mława
    "12272": (53.77, 20.41),  # Olsztyn
    "12280": (53.08, 21.57),  # Ostrołęka
    "12285": (53.18, 22.03),  # Łomża
    "12295": (53.11, 23.17),  # Białystok
    "12300": (52.73, 15.28),  # Gorzów Wlkp.
    "12310": (52.35, 14.59),  # Słubice
    "12330": (52.41, 16.83),  # Poznań
    "12345": (52.17, 18.25),  # Koło
    "12360": (52.56, 19.72),  # Płock
    "12375": (52.17, 20.97),  # Warszawa
    "12385": (52.17, 22.25),  # Siedlce
    "12399": (52.07, 23.61),  # Terespol
    "12400": (51.93, 15.53),  # Zielona Góra
    "12410": (51.84, 16.53),  # Leszno
    "12415": (51.21, 16.18),  # Legnica
    "12420": (51.78, 18.08),  # Kalisz
    "12424": (51.10, 16.89),  # Wrocław
    "12435": (51.64, 16.71),  # Rawicz
    "12455": (50.81, 19.10),  # Częstochowa
    "12465": (51.73, 19.40),  # Łódź
    "12469": (51.22, 18.57),  # Wieluń
    "12470": (51.37, 19.87),  # Sulejów
    "12485": (51.55, 21.08),  # Kozienice
    "12495": (51.23, 22.61),  # Lublin
    "12497": (51.52, 23.54),  # Włodawa
    "12500": (50.90, 15.79),  # Jelenia Góra
    "12510": (50.44, 16.66),  # Kłodzko
    "12520": (50.47, 17.27),  # Nysa
    "12530": (50.62, 17.97),  # Opole
    "12540": (50.06, 18.19),  # Racibórz
    "12550": (50.81, 20.69),  # Kielce
    "12560": (50.24, 19.03),  # Katowice
    "12566": (50.08, 19.79),  # Kraków
    "12570": (50.03, 20.98),  # Tarnów
    "12575": (49.61, 20.70),  # Nowy Sącz
    "12580": (50.11, 22.05),  # Rzeszów
    "12595": (50.70, 23.25),  # Zamość
    "12600": (49.30, 15.79),  # Śnieżka
    "12625": (49.30, 19.96),  # Zakopane
    "12650": (49.23, 19.98),  # Kasprowy Wierch
    "12660": (49.44, 20.95),  # Krynica
    "12670": (49.71, 21.77),  # Krosno
    "12690": (49.38, 22.58),  # Lesko
    "12695": (49.78, 22.76),  # Przemyśl
}

# Platforms
PLATFORMS: Final = ["sensor"]
