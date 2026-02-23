"""Tests for constants and icon parsing."""

from __future__ import annotations

import pytest

from custom_components.imgw_pib_monitor.const import (
    ICON_TO_CONDITION,
    VOIVODESHIPS,
    VOIVODESHIP_CAPITALS,
    SYNOP_STATIONS,
    parse_imgw_icon,
)


class TestParseImgwIcon:
    """Tests for IMGW icon code → HA weather condition mapping."""

    # ── Clear sky ─────────────────────────────────────────────

    def test_clear_day(self):
        # n0z00d: cloud=0, precip=0, day
        assert parse_imgw_icon("n0z00d") == "sunny"

    def test_clear_night(self):
        # n1z00n: cloud=1, precip=0, night
        assert parse_imgw_icon("n1z00n") == "clear-night"

    # ── Partly cloudy ─────────────────────────────────────────

    def test_partly_cloudy_day(self):
        # n3z00d: cloud=3, precip=0, day
        assert parse_imgw_icon("n3z00d") == "partlycloudy"

    def test_partly_cloudy_night(self):
        # n5z00n: cloud=5, precip=0, night
        assert parse_imgw_icon("n5z00n") == "partlycloudy"

    # ── Cloudy ────────────────────────────────────────────────

    def test_cloudy_day(self):
        # n8z00d: cloud=8, precip=0, day
        assert parse_imgw_icon("n8z00d") == "cloudy"

    def test_cloudy_night(self):
        # n6z00n: cloud=6, precip=0, night
        assert parse_imgw_icon("n6z00n") == "cloudy"

    # ── Rain ──────────────────────────────────────────────────

    def test_light_rain_day(self):
        # n7z61d: cloud=7, precip=61, day → rain_light → rainy
        assert parse_imgw_icon("n7z61d") == "rainy"

    def test_light_rain_night(self):
        # n7z65n: cloud=7, precip=65, night → rain_light → rainy
        assert parse_imgw_icon("n7z65n") == "rainy"

    def test_heavy_rain_day(self):
        # n8z80d: cloud=8, precip=80, day → rain_heavy → pouring
        assert parse_imgw_icon("n8z80d") == "pouring"

    def test_heavy_rain_night(self):
        # n8z85n: cloud=8, precip=85, night → rain_heavy → pouring
        assert parse_imgw_icon("n8z85n") == "pouring"

    # ── Snow ──────────────────────────────────────────────────

    def test_snow_day(self):
        # n8z70d: cloud=8, precip=70, day → snow → snowy
        assert parse_imgw_icon("n8z70d") == "snowy"

    def test_snow_night(self):
        # n8z75n: cloud=8, precip=75, night → snow → snowy
        assert parse_imgw_icon("n8z75n") == "snowy"

    # ── Low precip codes ──────────────────────────────────────

    def test_small_precip_code(self):
        # n7z10d: precip=10 (>0 but <60) → rain_light
        assert parse_imgw_icon("n7z10d") == "rainy"

    # ── Edge cases ────────────────────────────────────────────

    def test_none_returns_none(self):
        assert parse_imgw_icon(None) is None

    def test_empty_string_returns_none(self):
        assert parse_imgw_icon("") is None

    def test_too_short_returns_none(self):
        assert parse_imgw_icon("n0z0") is None

    def test_not_string_returns_none(self):
        assert parse_imgw_icon(12345) is None

    def test_invalid_format_returns_none(self):
        # Doesn't start with 'n' followed by digit followed by 'z'
        assert parse_imgw_icon("xyzabc") is None

    def test_non_numeric_cloud_returns_none(self):
        assert parse_imgw_icon("nXz00d") is None

    def test_default_time_of_day(self):
        # If last char is not 'd' or 'n', defaults to 'd'
        result = parse_imgw_icon("n0z00x")
        assert result == "sunny"


class TestConstants:
    """Basic sanity checks for constant data."""

    def test_all_voivodeships_have_capitals(self):
        for code in VOIVODESHIPS:
            assert code in VOIVODESHIP_CAPITALS, (
                f"Voivodeship {code} ({VOIVODESHIPS[code]}) has no capital coordinates"
            )

    def test_voivodeship_count(self):
        assert len(VOIVODESHIPS) == 16

    def test_synop_stations_have_valid_coords(self):
        for sid, (lat, lon) in SYNOP_STATIONS.items():
            assert 49.0 <= lat <= 55.0, f"Station {sid} lat {lat} out of Poland range"
            assert 14.0 <= lon <= 24.0, f"Station {sid} lon {lon} out of Poland range"

    def test_voivodeship_capitals_in_poland(self):
        for code, (lat, lon) in VOIVODESHIP_CAPITALS.items():
            assert 49.0 <= lat <= 55.0, f"Capital {code} lat {lat} out of range"
            assert 14.0 <= lon <= 24.0, f"Capital {code} lon {lon} out of range"

    def test_icon_to_condition_has_day_and_night(self):
        # Each weather type should have both day and night variants
        weather_types = set(key[0] for key in ICON_TO_CONDITION)
        for wtype in weather_types:
            assert (wtype, "d") in ICON_TO_CONDITION, f"Missing day variant for {wtype}"
            assert (wtype, "n") in ICON_TO_CONDITION, f"Missing night variant for {wtype}"
