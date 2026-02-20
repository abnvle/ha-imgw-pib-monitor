"""Tests for the weather entity logic."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.imgw_pib_monitor.const import parse_imgw_icon
from custom_components.imgw_pib_monitor.weather import ImgwWeatherEntity

from .conftest import SAMPLE_FORECAST_DATA


def _make_weather_entity(data=None):
    """Create a weather entity with mocked coordinator."""
    coordinator = MagicMock()
    coordinator.data = data if data is not None else SAMPLE_FORECAST_DATA

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_123"

    entity = ImgwWeatherEntity.__new__(ImgwWeatherEntity)
    entity.coordinator = coordinator
    entity._location_name = "Warszawa"
    entity._attr_name = None
    entity._attr_unique_id = f"imgw_pib_monitor_weather_{config_entry.entry_id}"
    entity._entry_id = config_entry.entry_id

    return entity


# ── Current weather properties ────────────────────────────────


class TestWeatherCurrentProperties:
    """Tests for current weather property accessors."""

    def test_native_temperature(self):
        entity = _make_weather_entity()
        assert entity.native_temperature == 5.3

    def test_native_apparent_temperature(self):
        entity = _make_weather_entity()
        assert entity.native_apparent_temperature == 2.1

    def test_humidity(self):
        entity = _make_weather_entity()
        assert entity.humidity == 72

    def test_native_pressure(self):
        entity = _make_weather_entity()
        assert entity.native_pressure == 1013

    def test_native_wind_speed(self):
        entity = _make_weather_entity()
        assert entity.native_wind_speed == 3.2

    def test_native_wind_gust_speed(self):
        entity = _make_weather_entity()
        assert entity.native_wind_gust_speed == 7.5

    def test_wind_bearing(self):
        entity = _make_weather_entity()
        assert entity.wind_bearing == 180

    def test_cloud_coverage(self):
        entity = _make_weather_entity()
        assert entity.cloud_coverage == 75

    def test_all_none_when_no_data(self):
        entity = _make_weather_entity(data={})
        assert entity.native_temperature is None
        assert entity.humidity is None
        assert entity.native_pressure is None
        assert entity.native_wind_speed is None

    def test_all_none_when_no_current(self):
        entity = _make_weather_entity(data={"daily": [], "hourly": []})
        assert entity.native_temperature is None
        assert entity.condition is None


# ── Condition logic ───────────────────────────────────────────


class TestWeatherCondition:
    """Tests for weather condition derivation."""

    def test_condition_from_icon(self):
        entity = _make_weather_entity()
        # icon "n5z00d" → cloud=5, precip=0, day → partlycloudy
        assert entity.condition == "partlycloudy"

    def test_condition_fallback_snow(self):
        data = {**SAMPLE_FORECAST_DATA, "current": {"snow": 2.0, "precip": 0, "cloud": 100}}
        entity = _make_weather_entity(data=data)
        assert entity.condition == "snowy"

    def test_condition_fallback_pouring(self):
        data = {**SAMPLE_FORECAST_DATA, "current": {"snow": 0, "precip": 5.0, "cloud": 100}}
        entity = _make_weather_entity(data=data)
        assert entity.condition == "pouring"

    def test_condition_fallback_rainy(self):
        data = {**SAMPLE_FORECAST_DATA, "current": {"snow": 0, "precip": 1.0, "cloud": 100}}
        entity = _make_weather_entity(data=data)
        assert entity.condition == "rainy"

    def test_condition_fallback_sunny(self):
        data = {**SAMPLE_FORECAST_DATA, "current": {"snow": 0, "precip": 0, "cloud": 5}}
        entity = _make_weather_entity(data=data)
        assert entity.condition == "sunny"

    def test_condition_fallback_partly_cloudy(self):
        data = {**SAMPLE_FORECAST_DATA, "current": {"snow": 0, "precip": 0, "cloud": 40}}
        entity = _make_weather_entity(data=data)
        assert entity.condition == "partlycloudy"

    def test_condition_fallback_cloudy(self):
        data = {**SAMPLE_FORECAST_DATA, "current": {"snow": 0, "precip": 0, "cloud": 80}}
        entity = _make_weather_entity(data=data)
        assert entity.condition == "cloudy"

    def test_condition_none_without_data(self):
        entity = _make_weather_entity(data={})
        assert entity.condition is None


# ── Extra state attributes ────────────────────────────────────


class TestWeatherExtraAttributes:
    """Tests for extra state attributes."""

    def test_includes_location(self):
        entity = _make_weather_entity()
        attrs = entity.extra_state_attributes
        assert attrs["location"] == "Warszawa"

    def test_includes_sun_data(self):
        entity = _make_weather_entity()
        attrs = entity.extra_state_attributes
        assert attrs["sunrise"] == "07:30"
        assert attrs["sunset"] == "16:15"

    def test_includes_icon(self):
        entity = _make_weather_entity()
        attrs = entity.extra_state_attributes
        assert attrs["icon_imgw"] == "n5z00d"

    def test_includes_hourly_and_daily(self):
        entity = _make_weather_entity()
        attrs = entity.extra_state_attributes
        assert len(attrs["hourly"]) == 2
        assert len(attrs["daily"]) == 3


# ── Daily forecast ────────────────────────────────────────────


class TestWeatherDailyForecast:
    """Tests for daily forecast generation."""

    @pytest.mark.asyncio
    async def test_groups_by_date(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_daily()

        # Sample data has 2 entries for 2024-01-15 and 1 for 2024-01-16
        assert len(forecasts) == 2

    @pytest.mark.asyncio
    async def test_first_date_merged_temperatures(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_daily()

        fc_jan15 = forecasts[0]
        # Day: max 6.0, min 1.0; Night: max 3.0, min -1.0
        # Merged: hi=max(6.0, 3.0)=6.0, lo=min(1.0, -1.0)=-1.0
        assert fc_jan15["native_temperature"] == 6.0
        assert fc_jan15["native_templow"] == -1.0

    @pytest.mark.asyncio
    async def test_first_date_prefers_day_icon(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_daily()

        fc_jan15 = forecasts[0]
        # is_day=True entry has icon "n5z00d"
        assert fc_jan15["condition"] == parse_imgw_icon("n5z00d")

    @pytest.mark.asyncio
    async def test_precipitation_summed(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_daily()

        fc_jan15 = forecasts[0]
        # 0.2 + 0.0 = 0.2
        assert fc_jan15["precipitation"] == pytest.approx(0.2)

    @pytest.mark.asyncio
    async def test_wind_max_across_entries(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_daily()

        fc_jan15 = forecasts[0]
        # max(8.0, 5.0) = 8.0
        assert fc_jan15["native_wind_speed"] == 8.0

    @pytest.mark.asyncio
    async def test_sorted_by_date(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_daily()

        dates = [f["datetime"] for f in forecasts]
        assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_empty_data(self):
        entity = _make_weather_entity(data={})
        forecasts = await entity.async_forecast_daily()
        assert forecasts == []


# ── Hourly forecast ───────────────────────────────────────────


class TestWeatherHourlyForecast:
    """Tests for hourly forecast generation."""

    @pytest.mark.asyncio
    async def test_returns_all_entries(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_hourly()

        assert len(forecasts) == 2

    @pytest.mark.asyncio
    async def test_first_entry_properties(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_hourly()

        fc = forecasts[0]
        assert fc["datetime"] == "2024-01-15T13:00:00"
        assert fc["native_temperature"] == 5.5
        assert fc["humidity"] == 70
        assert fc["native_pressure"] == 1013
        assert fc["native_wind_speed"] == 3.0

    @pytest.mark.asyncio
    async def test_second_entry_has_rain_condition(self):
        entity = _make_weather_entity()
        forecasts = await entity.async_forecast_hourly()

        fc = forecasts[1]
        # icon "n7z61d" → rain_light → rainy
        assert fc["condition"] == "rainy"

    @pytest.mark.asyncio
    async def test_empty_data(self):
        entity = _make_weather_entity(data={})
        forecasts = await entity.async_forecast_hourly()
        assert forecasts == []


# ── Device info ───────────────────────────────────────────────


class TestWeatherDeviceInfo:
    """Tests for weather entity device info."""

    def test_device_info_name(self):
        entity = _make_weather_entity()
        info = entity.device_info
        assert "Warszawa" in info["name"]

    def test_device_info_identifiers(self):
        entity = _make_weather_entity()
        info = entity.device_info
        identifiers = info["identifiers"]
        assert ("imgw_pib_monitor", "forecast_test_entry_123") in identifiers
