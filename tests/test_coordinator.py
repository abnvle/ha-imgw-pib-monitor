"""Tests for data coordinators — parsing and helper logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.imgw_pib_monitor.coordinator import ImgwDataUpdateCoordinator

from .conftest import (
    SAMPLE_HYDRO_DATA,
    SAMPLE_METEO_DATA,
    SAMPLE_SYNOP_DATA,
    SAMPLE_WARNINGS_HYDRO,
    SAMPLE_WARNINGS_METEO,
)


# ── Helpers to get at static / instance methods without full HA init ──


def _make_coordinator_stub():
    """Create a minimal stub that lets us call parsing methods.

    We avoid instantiating the real coordinator (requires HA runtime)
    and instead build a thin object with the methods under test.
    """

    class Stub:
        _safe_float = staticmethod(ImgwDataUpdateCoordinator._safe_float)
        _safe_int = staticmethod(ImgwDataUpdateCoordinator._safe_int)

        def _parse_synop(self, data):
            return ImgwDataUpdateCoordinator._parse_synop(self, data)

        def _parse_hydro(self, data):
            return ImgwDataUpdateCoordinator._parse_hydro(self, data)

        def _parse_meteo(self, data):
            return ImgwDataUpdateCoordinator._parse_meteo(self, data)

        def _parse_warnings_meteo(self, data):
            return ImgwDataUpdateCoordinator._parse_warnings_meteo(self, data)

        def _parse_warnings_hydro(self, data):
            return ImgwDataUpdateCoordinator._parse_warnings_hydro(self, data)

    return Stub()


# ── _safe_float / _safe_int ───────────────────────────────────


class TestSafeFloat:
    """Tests for the _safe_float static method."""

    def test_normal_float_string(self):
        assert ImgwDataUpdateCoordinator._safe_float("3.14") == 3.14

    def test_integer_string(self):
        assert ImgwDataUpdateCoordinator._safe_float("42") == 42.0

    def test_negative(self):
        assert ImgwDataUpdateCoordinator._safe_float("-5.5") == -5.5

    def test_zero(self):
        assert ImgwDataUpdateCoordinator._safe_float("0") == 0.0

    def test_none_returns_none(self):
        assert ImgwDataUpdateCoordinator._safe_float(None) is None

    def test_empty_string_returns_none(self):
        assert ImgwDataUpdateCoordinator._safe_float("") is None

    def test_non_numeric_returns_none(self):
        assert ImgwDataUpdateCoordinator._safe_float("abc") is None

    def test_float_passthrough(self):
        assert ImgwDataUpdateCoordinator._safe_float(7.6) == 7.6

    def test_int_passthrough(self):
        assert ImgwDataUpdateCoordinator._safe_float(10) == 10.0


class TestSafeInt:
    """Tests for the _safe_int static method."""

    def test_normal_int_string(self):
        assert ImgwDataUpdateCoordinator._safe_int("42") == 42

    def test_negative(self):
        assert ImgwDataUpdateCoordinator._safe_int("-3") == -3

    def test_zero(self):
        assert ImgwDataUpdateCoordinator._safe_int("0") == 0

    def test_none_returns_none(self):
        assert ImgwDataUpdateCoordinator._safe_int(None) is None

    def test_empty_string_returns_none(self):
        assert ImgwDataUpdateCoordinator._safe_int("") is None

    def test_non_numeric_returns_none(self):
        assert ImgwDataUpdateCoordinator._safe_int("abc") is None

    def test_float_string_truncates(self):
        # int("3.14") raises ValueError → None
        assert ImgwDataUpdateCoordinator._safe_int("3.14") is None

    def test_int_passthrough(self):
        assert ImgwDataUpdateCoordinator._safe_int(5) == 5


# ── _parse_synop ──────────────────────────────────────────────


class TestParseSynop:
    """Tests for synoptic data parsing."""

    def test_parses_complete_data(self):
        stub = _make_coordinator_stub()
        result = stub._parse_synop(SAMPLE_SYNOP_DATA[0])

        assert result["station_name"] == "Warszawa"
        assert result["station_id"] == "12375"
        assert result["temperature"] == 5.3
        assert result["wind_speed"] == 3.2
        assert result["wind_direction"] == 180
        assert result["humidity"] == 72.5
        assert result["precipitation"] == 0.0
        assert result["pressure"] == 1013.2

    def test_handles_missing_fields(self):
        stub = _make_coordinator_stub()
        result = stub._parse_synop({"stacja": "Test", "id_stacji": "999"})

        assert result["station_name"] == "Test"
        assert result["temperature"] is None
        assert result["wind_speed"] is None
        assert result["pressure"] is None

    def test_handles_empty_dict(self):
        stub = _make_coordinator_stub()
        result = stub._parse_synop({})

        assert result["station_name"] is None
        assert result["temperature"] is None


# ── _parse_hydro ──────────────────────────────────────────────


class TestParseHydro:
    """Tests for hydrological data parsing."""

    def test_parses_complete_data(self):
        stub = _make_coordinator_stub()
        result = stub._parse_hydro(SAMPLE_HYDRO_DATA[0])

        assert result["station_name"] == "Warszawa"
        assert result["river"] == "Wisła"
        assert result["water_level"] == 250
        assert result["water_temperature"] == 4.5
        assert result["flow"] == 350.5
        assert result["latitude"] == 52.2297
        assert result["longitude"] == 21.0122

    def test_handles_missing_fields(self):
        stub = _make_coordinator_stub()
        result = stub._parse_hydro({"stacja": "Test"})

        assert result["station_name"] == "Test"
        assert result["water_level"] is None
        assert result["flow"] is None
        assert result["latitude"] is None


# ── _parse_meteo ──────────────────────────────────────────────


class TestParseMeteo:
    """Tests for meteorological data parsing."""

    def test_parses_complete_data(self):
        stub = _make_coordinator_stub()
        result = stub._parse_meteo(SAMPLE_METEO_DATA[0])

        assert result["station_name"] == "Warszawa"
        assert result["station_code"] == "249200080"
        assert result["air_temperature"] == 5.0
        assert result["ground_temperature"] == 2.1
        assert result["wind_avg_speed"] == 3.5
        assert result["wind_max_speed"] == 7.2
        assert result["humidity"] == 75.3
        assert result["wind_gust_10min"] == 9.1
        assert result["precipitation_10min"] == 0.0

    def test_handles_missing_fields(self):
        stub = _make_coordinator_stub()
        result = stub._parse_meteo({})

        assert result["station_name"] is None
        assert result["air_temperature"] is None


# ── _parse_warnings_meteo ─────────────────────────────────────


class TestParseWarningsMeteo:
    """Tests for meteorological warnings parsing."""

    def test_parses_warnings(self):
        stub = _make_coordinator_stub()
        result = stub._parse_warnings_meteo(SAMPLE_WARNINGS_METEO)

        assert result["active_warnings_count"] == 2
        assert result["max_level"] == 2
        assert len(result["warnings"]) == 2

    def test_sorted_by_level_desc(self):
        stub = _make_coordinator_stub()
        result = stub._parse_warnings_meteo(SAMPLE_WARNINGS_METEO)

        warnings = result["warnings"]
        assert warnings[0]["level"] >= warnings[1]["level"]

    def test_latest_warning_is_highest_level(self):
        stub = _make_coordinator_stub()
        result = stub._parse_warnings_meteo(SAMPLE_WARNINGS_METEO)

        assert result["latest_warning"]["event"] == "Silny wiatr"
        assert result["latest_warning"]["level"] == 2
        assert result["latest_warning"]["probability"] == 80

    def test_empty_list(self):
        stub = _make_coordinator_stub()
        result = stub._parse_warnings_meteo([])

        assert result["active_warnings_count"] == 0
        assert result["max_level"] == 0
        assert result["warnings"] == []

    def test_single_warning(self):
        stub = _make_coordinator_stub()
        result = stub._parse_warnings_meteo([SAMPLE_WARNINGS_METEO[0]])

        assert result["active_warnings_count"] == 1
        assert result["latest_warning"]["event"] == "Silny wiatr"


# ── _parse_warnings_hydro ─────────────────────────────────────


class TestParseWarningsHydro:
    """Tests for hydrological warnings parsing."""

    def test_parses_warnings(self):
        stub = _make_coordinator_stub()
        result = stub._parse_warnings_hydro(SAMPLE_WARNINGS_HYDRO)

        assert result["active_warnings_count"] == 1
        assert result["max_level"] == 2
        assert result["latest_warning"]["event"] == "Wezbranie z przekroczeniem stanów ostrzegawczych"
        assert result["latest_warning"]["probability"] == 90

    def test_areas_extracted(self):
        stub = _make_coordinator_stub()
        result = stub._parse_warnings_hydro(SAMPLE_WARNINGS_HYDRO)

        areas = result["latest_warning"]["areas"]
        assert "Wisła od Warszawy do Płocka" in areas

    def test_empty_list(self):
        stub = _make_coordinator_stub()
        result = stub._parse_warnings_hydro([])

        assert result["active_warnings_count"] == 0
        assert result["max_level"] == 0

    def test_handles_negative_level(self):
        """The code uses abs() on the level, so negative values should become positive."""
        stub = _make_coordinator_stub()
        data = [{
            "numer": "002/2024",
            "zdarzenie": "Test",
            "stopień": "-3",
            "prawdopodobienstwo": "50",
            "data_od": "2024-01-15",
            "data_do": "2024-01-16",
            "przebieg": "Test",
            "obszary": [],
        }]
        result = stub._parse_warnings_hydro(data)
        assert result["max_level"] == 3
        assert result["warnings"][0]["level"] == 3

    def test_handles_invalid_level(self):
        """Non-numeric level should default to 0."""
        stub = _make_coordinator_stub()
        data = [{
            "numer": "003/2024",
            "zdarzenie": "Test",
            "stopień": "abc",
            "prawdopodobienstwo": "0",
            "data_od": "2024-01-15",
            "data_do": "2024-01-16",
            "przebieg": None,
            "obszary": [],
        }]
        result = stub._parse_warnings_hydro(data)
        assert result["warnings"][0]["level"] == 0

    def test_handles_missing_level_key(self):
        """When neither stopień nor stopien is present, should use default 0."""
        stub = _make_coordinator_stub()
        data = [{
            "numer": "004/2024",
            "zdarzenie": "Test",
            "prawdopodobienstwo": "0",
            "data_od": "2024-01-15",
            "data_do": "2024-01-16",
            "przebieg": None,
            "obszary": [],
        }]
        result = stub._parse_warnings_hydro(data)
        assert result["warnings"][0]["level"] == 0

    def test_multiple_warnings_sorted(self):
        stub = _make_coordinator_stub()
        data = [
            {
                "numer": "001/2024",
                "zdarzenie": "Low level",
                "stopień": "1",
                "prawdopodobienstwo": "50",
                "data_od": "2024-01-15",
                "data_do": "2024-01-16",
                "przebieg": "low",
                "obszary": [],
            },
            {
                "numer": "002/2024",
                "zdarzenie": "High level",
                "stopień": "3",
                "prawdopodobienstwo": "90",
                "data_od": "2024-01-15",
                "data_do": "2024-01-16",
                "przebieg": "high",
                "obszary": [],
            },
        ]
        result = stub._parse_warnings_hydro(data)
        assert result["warnings"][0]["level"] == 3
        assert result["warnings"][0]["event"] == "High level"
        assert result["warnings"][1]["level"] == 1
