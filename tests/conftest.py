"""Shared fixtures for IMGW-PIB Monitor tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Sample API responses ──────────────────────────────────────

SAMPLE_SYNOP_DATA = [
    {
        "id_stacji": "12375",
        "stacja": "Warszawa",
        "data_pomiaru": "2024-01-15",
        "godzina_pomiaru": "12",
        "temperatura": "5.3",
        "predkosc_wiatru": "3.2",
        "kierunek_wiatru": "180",
        "wilgotnosc_wzgledna": "72.5",
        "suma_opadu": "0.0",
        "cisnienie": "1013.2",
    },
    {
        "id_stacji": "12566",
        "stacja": "Kraków",
        "data_pomiaru": "2024-01-15",
        "godzina_pomiaru": "12",
        "temperatura": "3.1",
        "predkosc_wiatru": "2.5",
        "kierunek_wiatru": "220",
        "wilgotnosc_wzgledna": "80.0",
        "suma_opadu": "1.2",
        "cisnienie": "1010.5",
    },
]

SAMPLE_HYDRO_DATA = [
    {
        "id_stacji": "150190370",
        "stacja": "Warszawa",
        "rzeka": "Wisła",
        "wojewodztwo": "mazowieckie",
        "lat": "52.2297",
        "lon": "21.0122",
        "stan_wody": "250",
        "stan_wody_data_pomiaru": "2024-01-15 12:00:00",
        "temperatura_wody": "4.5",
        "temperatura_wody_data_pomiaru": "2024-01-15 12:00:00",
        "przelyw": "350.5",
        "przeplyw_data": "2024-01-15 12:00:00",
        "zjawisko_lodowe": "0",
        "zjawisko_lodowe_data_pomiaru": "2024-01-15 12:00:00",
    },
]

SAMPLE_METEO_DATA = [
    {
        "kod_stacji": "249200080",
        "nazwa_stacji": "Warszawa",
        "lat": "52.2297",
        "lon": "21.0122",
        "temperatura_gruntu": "2.1",
        "temperatura_powietrza": "5.0",
        "wiatr_kierunek": "200",
        "wiatr_srednia_predkosc": "3.5",
        "wiatr_predkosc_maksymalna": "7.2",
        "wilgotnosc_wzgledna": "75.3",
        "wiatr_poryw_10min": "9.1",
        "opad_10min": "0.0",
    },
]

SAMPLE_WARNINGS_METEO = [
    {
        "nazwa_zdarzenia": "Silny wiatr",
        "stopien": "2",
        "prawdopodobienstwo": "80",
        "obowiazuje_od": "2024-01-15T06:00:00",
        "obowiazuje_do": "2024-01-15T18:00:00",
        "tresc": "Prognozuje się wystąpienie silnego wiatru o średniej prędkości...",
        "komentarz": "Test comment",
        "teryt": ["1461", "1462"],
    },
    {
        "nazwa_zdarzenia": "Oblodzenie",
        "stopien": "1",
        "prawdopodobienstwo": "60",
        "obowiazuje_od": "2024-01-15T00:00:00",
        "obowiazuje_do": "2024-01-15T08:00:00",
        "tresc": "Prognozuje się oblodzenie...",
        "komentarz": None,
        "teryt": ["1461"],
    },
]

SAMPLE_WARNINGS_HYDRO = [
    {
        "numer": "001/2024",
        "zdarzenie": "Wezbranie z przekroczeniem stanów ostrzegawczych",
        "stopień": "2",
        "prawdopodobienstwo": "90",
        "data_od": "2024-01-15T06:00:00",
        "data_do": "2024-01-16T06:00:00",
        "przebieg": "Na Wiśle w rejonie Warszawy...",
        "obszary": [
            {"opis": "Wisła od Warszawy do Płocka", "wojewodztwo": "mazowieckie"},
        ],
    },
]

SAMPLE_COORDINATOR_DATA = {
    "synop": {
        "12375": {
            "station_name": "Warszawa",
            "station_id": "12375",
            "measurement_date": "2024-01-15",
            "measurement_hour": "12",
            "temperature": 5.3,
            "wind_speed": 3.2,
            "wind_direction": 180,
            "humidity": 72.5,
            "precipitation": 0.0,
            "pressure": 1013.2,
            "latitude": 52.23,
            "longitude": 21.01,
            "distance": 1.5,
        },
    },
    "hydro": {
        "150190370": {
            "station_name": "Warszawa",
            "station_id": "150190370",
            "river": "Wisła",
            "voivodeship": "mazowieckie",
            "longitude": 21.0122,
            "latitude": 52.2297,
            "water_level": 250,
            "water_level_date": "2024-01-15 12:00:00",
            "water_temperature": 4.5,
            "water_temperature_date": "2024-01-15 12:00:00",
            "flow": 350.5,
            "flow_date": "2024-01-15 12:00:00",
            "ice_phenomenon": 0,
            "ice_phenomenon_date": "2024-01-15 12:00:00",
            "distance": 2.3,
        },
    },
    "meteo": {
        "249200080": {
            "station_name": "Warszawa",
            "station_code": "249200080",
            "longitude": 21.0122,
            "latitude": 52.2297,
            "ground_temperature": 2.1,
            "air_temperature": 5.0,
            "wind_direction": 200,
            "wind_avg_speed": 3.5,
            "wind_max_speed": 7.2,
            "humidity": 75.3,
            "wind_gust_10min": 9.1,
            "precipitation_10min": 0.0,
            "distance": 2.3,
        },
    },
    "warnings_meteo": {
        "active_warnings_count": 2,
        "max_level": 2,
        "warnings": [
            {
                "event": "Silny wiatr",
                "level": 2,
                "probability": 80,
                "valid_from": "2024-01-15T06:00:00",
                "valid_to": "2024-01-15T18:00:00",
                "content": "Prognozuje się wystąpienie silnego wiatru...",
                "comment": "Test comment",
            },
            {
                "event": "Oblodzenie",
                "level": 1,
                "probability": 60,
                "valid_from": "2024-01-15T00:00:00",
                "valid_to": "2024-01-15T08:00:00",
                "content": "Prognozuje się oblodzenie...",
                "comment": None,
            },
        ],
        "latest_warning": {
            "event": "Silny wiatr",
            "level": 2,
            "probability": 80,
            "valid_from": "2024-01-15T06:00:00",
            "valid_to": "2024-01-15T18:00:00",
            "content": "Prognozuje się wystąpienie silnego wiatru...",
            "comment": "Test comment",
        },
    },
    "warnings_hydro": {
        "active_warnings_count": 1,
        "max_level": 2,
        "warnings": [
            {
                "number": "001/2024",
                "event": "Wezbranie z przekroczeniem stanów ostrzegawczych",
                "level": 2,
                "probability": 90,
                "valid_from": "2024-01-15T06:00:00",
                "valid_to": "2024-01-16T06:00:00",
                "description": "Na Wiśle w rejonie Warszawy...",
                "areas": ["Wisła od Warszawy do Płocka"],
            },
        ],
        "latest_warning": {
            "number": "001/2024",
            "event": "Wezbranie z przekroczeniem stanów ostrzegawczych",
            "level": 2,
            "probability": 90,
            "valid_from": "2024-01-15T06:00:00",
            "valid_to": "2024-01-16T06:00:00",
            "description": "Na Wiśle w rejonie Warszawy...",
            "areas": ["Wisła od Warszawy do Płocka"],
        },
    },
}

SAMPLE_FORECAST_DATA = {
    "current": {
        "temp": 5.3,
        "feels_like": 2.1,
        "humidity": 72,
        "pressure": 1013,
        "wind_speed": 3.2,
        "wind_gust": 7.5,
        "wind_dir": 180,
        "cloud": 75,
        "precip": 0.0,
        "rain": 0.0,
        "snow": 0.0,
        "model": "AROME",
        "icon": "n5z00d",
    },
    "sun": {"Sunrise": "07:30", "Sunset": "16:15"},
    "hourly": [
        {
            "date": "2024-01-15T13:00:00",
            "temp": 5.5,
            "feels_like": 2.3,
            "humidity": 70,
            "pressure": 1013,
            "wind_speed": 3.0,
            "wind_gust": 7.0,
            "wind_dir": 180,
            "cloud": 80,
            "precip": 0.0,
            "icon": "n5z00d",
        },
        {
            "date": "2024-01-15T14:00:00",
            "temp": 5.0,
            "feels_like": 1.8,
            "humidity": 73,
            "pressure": 1012,
            "wind_speed": 3.5,
            "wind_gust": 8.0,
            "wind_dir": 190,
            "cloud": 90,
            "precip": 0.2,
            "icon": "n7z61d",
        },
    ],
    "daily": [
        {
            "date": "2024-01-15",
            "temp_max": 6.0,
            "temp_min": 1.0,
            "icon": "n5z00d",
            "wind_max": 8.0,
            "precip": 0.2,
            "is_day": True,
        },
        {
            "date": "2024-01-15",
            "temp_max": 3.0,
            "temp_min": -1.0,
            "icon": "n7z00n",
            "wind_max": 5.0,
            "precip": 0.0,
            "is_day": False,
        },
        {
            "date": "2024-01-16",
            "temp_max": 4.0,
            "temp_min": -2.0,
            "icon": "n3z00d",
            "wind_max": 6.0,
            "precip": 0.0,
            "is_day": True,
        },
    ],
}


# ── Geocoding responses ───────────────────────────────────────

SAMPLE_NOMINATIM_RESPONSE = {
    "address": {
        "city": "Warszawa",
        "state": "mazowieckie",
        "country": "Polska",
    },
    "name": "Warszawa",
}

SAMPLE_IMGW_PROXY_SEARCH_RESPONSE = [
    {
        "name": "Warszawa",
        "lat": "52.2297",
        "lon": "21.0122",
        "teryt": "1465",
        "province": "mazowieckie",
        "district": "Warszawa",
        "commune": "Warszawa",
        "rank": "10",
        "identifier": "Warszawa, mazowieckie",
        "synoptic": True,
    },
    {
        "name": "Warszawa",
        "lat": "52.23",
        "lon": "21.01",
        "teryt": "1465",
        "province": "mazowieckie",
        "district": "Warszawa",
        "commune": "Praga Południe",
        "rank": "5",
        "identifier": "Warszawa, Praga Południe, mazowieckie",
        "synoptic": False,
    },
]
