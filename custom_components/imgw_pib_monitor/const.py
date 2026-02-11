"""Constants for the IMGW-PIB Monitor integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "imgw_pib_monitor"
MANUFACTURER: Final = "IMGW-PIB"
ATTRIBUTION: Final = (
    "Źródłem pochodzenia danych jest Instytut Meteorologii "
    "i Gospodarki Wodnej – Państwowy Instytut Badawczy"
)

# API Base URL
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

# Data types
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

# TERYT codes for voivodeships (first 2 digits)
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

# Platforms
PLATFORMS: Final = ["sensor"]