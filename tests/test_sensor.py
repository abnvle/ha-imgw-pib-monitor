"""Tests for sensor definitions and entity logic."""

from __future__ import annotations

import pytest

from custom_components.imgw_pib_monitor.sensor import (
    HYDRO_SENSORS,
    METEO_SENSORS,
    SYNOP_SENSORS,
    WARNINGS_HYDRO_SENSORS,
    WARNINGS_METEO_SENSORS,
    sid_to_uid,
)

from .conftest import SAMPLE_COORDINATOR_DATA


# ── sid_to_uid ────────────────────────────────────────────────


class TestSidToUid:
    """Tests for station ID to unique ID conversion."""

    def test_simple_string(self):
        assert sid_to_uid("12375") == "12375"

    def test_with_dash(self):
        assert sid_to_uid("150-190-370") == "150_190_370"

    def test_uppercase(self):
        assert sid_to_uid("ABC-123") == "abc_123"

    def test_integer_input(self):
        assert sid_to_uid(12375) == "12375"

    def test_empty_string(self):
        assert sid_to_uid("") == ""


# ── Sensor description value_fn ───────────────────────────────


class TestSynopSensorValues:
    """Test that SYNOP sensor value_fn extracts correct data."""

    def setup_method(self):
        self.data = SAMPLE_COORDINATOR_DATA["synop"]["12375"]

    def test_temperature(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "temperature")
        assert sensor.value_fn(self.data) == 5.3

    def test_wind_speed(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "wind_speed")
        assert sensor.value_fn(self.data) == 3.2

    def test_wind_direction(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "wind_direction")
        assert sensor.value_fn(self.data) == 180

    def test_humidity(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "humidity")
        assert sensor.value_fn(self.data) == 72.5

    def test_precipitation(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "precipitation")
        assert sensor.value_fn(self.data) == 0.0

    def test_pressure(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "pressure")
        assert sensor.value_fn(self.data) == 1013.2

    def test_station_id(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "station_id")
        assert sensor.value_fn(self.data) == "12375"

    def test_distance(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "distance")
        assert sensor.value_fn(self.data) == 1.5

    def test_missing_data_returns_none(self):
        sensor = next(s for s in SYNOP_SENSORS if s.key == "temperature")
        assert sensor.value_fn({}) is None


class TestHydroSensorValues:
    """Test that HYDRO sensor value_fn extracts correct data."""

    def setup_method(self):
        self.data = SAMPLE_COORDINATOR_DATA["hydro"]["150190370"]

    def test_water_level(self):
        sensor = next(s for s in HYDRO_SENSORS if s.key == "water_level")
        assert sensor.value_fn(self.data) == 250

    def test_flow(self):
        sensor = next(s for s in HYDRO_SENSORS if s.key == "flow")
        assert sensor.value_fn(self.data) == 350.5

    def test_water_temperature(self):
        sensor = next(s for s in HYDRO_SENSORS if s.key == "water_temperature")
        assert sensor.value_fn(self.data) == 4.5

    def test_ice_phenomenon(self):
        sensor = next(s for s in HYDRO_SENSORS if s.key == "ice_phenomenon")
        assert sensor.value_fn(self.data) == 0


class TestMeteoSensorValues:
    """Test that METEO sensor value_fn extracts correct data."""

    def setup_method(self):
        self.data = SAMPLE_COORDINATOR_DATA["meteo"]["249200080"]

    def test_air_temperature(self):
        sensor = next(s for s in METEO_SENSORS if s.key == "air_temperature")
        assert sensor.value_fn(self.data) == 5.0

    def test_ground_temperature(self):
        sensor = next(s for s in METEO_SENSORS if s.key == "ground_temperature")
        assert sensor.value_fn(self.data) == 2.1

    def test_wind_avg_speed(self):
        sensor = next(s for s in METEO_SENSORS if s.key == "wind_avg_speed")
        assert sensor.value_fn(self.data) == 3.5

    def test_wind_gust(self):
        sensor = next(s for s in METEO_SENSORS if s.key == "wind_gust")
        assert sensor.value_fn(self.data) == 9.1

    def test_precipitation_10min(self):
        sensor = next(s for s in METEO_SENSORS if s.key == "precipitation_10min")
        assert sensor.value_fn(self.data) == 0.0


class TestWarningsMeteoSensorValues:
    """Test that WARNINGS_METEO sensor value_fn extracts correct data."""

    def setup_method(self):
        self.data = SAMPLE_COORDINATOR_DATA["warnings_meteo"]

    def test_count(self):
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_count")
        assert sensor.value_fn(self.data) == 2

    def test_max_level(self):
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_max_level")
        assert sensor.value_fn(self.data) == 2

    def test_latest_event(self):
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_latest_event")
        assert sensor.value_fn(self.data) == "Silny wiatr"

    def test_latest_level(self):
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_latest_level")
        assert sensor.value_fn(self.data) == 2

    def test_latest_probability(self):
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_latest_probability")
        assert sensor.value_fn(self.data) == 80

    def test_latest_valid_from(self):
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_latest_valid_from")
        assert sensor.value_fn(self.data) == "2024-01-15T06:00:00"

    def test_latest_content_truncated(self):
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_latest_content")
        result = sensor.value_fn(self.data)
        assert len(result) <= 255

    def test_no_latest_warning(self):
        """When no warnings, latest fields return None."""
        empty_data = {"active_warnings_count": 0, "max_level": 0, "warnings": [], "latest_warning": None}
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_latest_event")
        assert sensor.value_fn(empty_data) is None

    def test_extra_attrs_fn(self):
        sensor = next(s for s in WARNINGS_METEO_SENSORS if s.key == "warnings_meteo_count")
        assert sensor.extra_attrs_fn is not None
        attrs = sensor.extra_attrs_fn(self.data)
        assert "warnings" in attrs
        assert len(attrs["warnings"]) == 2


class TestWarningsHydroSensorValues:
    """Test that WARNINGS_HYDRO sensor value_fn extracts correct data."""

    def setup_method(self):
        self.data = SAMPLE_COORDINATOR_DATA["warnings_hydro"]

    def test_count(self):
        sensor = next(s for s in WARNINGS_HYDRO_SENSORS if s.key == "warnings_hydro_count")
        assert sensor.value_fn(self.data) == 1

    def test_max_level(self):
        sensor = next(s for s in WARNINGS_HYDRO_SENSORS if s.key == "warnings_hydro_max_level")
        assert sensor.value_fn(self.data) == 2

    def test_latest_event(self):
        sensor = next(s for s in WARNINGS_HYDRO_SENSORS if s.key == "warnings_hydro_latest_event")
        result = sensor.value_fn(self.data)
        assert "Wezbranie" in result

    def test_latest_description_truncated(self):
        sensor = next(s for s in WARNINGS_HYDRO_SENSORS if s.key == "warnings_hydro_latest_description")
        result = sensor.value_fn(self.data)
        assert result is not None
        assert len(result) <= 255


# ── Sensor description sanity checks ─────────────────────────


class TestSensorDescriptionIntegrity:
    """Sanity checks for sensor descriptions."""

    def test_all_synop_sensors_have_unique_keys(self):
        keys = [s.key for s in SYNOP_SENSORS]
        assert len(keys) == len(set(keys))

    def test_all_hydro_sensors_have_unique_keys(self):
        keys = [s.key for s in HYDRO_SENSORS]
        assert len(keys) == len(set(keys))

    def test_all_meteo_sensors_have_unique_keys(self):
        keys = [s.key for s in METEO_SENSORS]
        assert len(keys) == len(set(keys))

    def test_all_warnings_meteo_sensors_have_unique_keys(self):
        keys = [s.key for s in WARNINGS_METEO_SENSORS]
        assert len(keys) == len(set(keys))

    def test_all_warnings_hydro_sensors_have_unique_keys(self):
        keys = [s.key for s in WARNINGS_HYDRO_SENSORS]
        assert len(keys) == len(set(keys))

    def test_all_sensors_have_translation_key(self):
        all_sensors = (
            SYNOP_SENSORS + HYDRO_SENSORS + METEO_SENSORS
            + WARNINGS_METEO_SENSORS + WARNINGS_HYDRO_SENSORS
        )
        for s in all_sensors:
            assert s.translation_key, f"Sensor {s.key} missing translation_key"

    def test_all_sensors_have_value_fn(self):
        all_sensors = (
            SYNOP_SENSORS + HYDRO_SENSORS + METEO_SENSORS
            + WARNINGS_METEO_SENSORS + WARNINGS_HYDRO_SENSORS
        )
        for s in all_sensors:
            assert callable(s.value_fn), f"Sensor {s.key} missing value_fn"

    def test_synop_sensor_count(self):
        assert len(SYNOP_SENSORS) == 8

    def test_hydro_sensor_count(self):
        assert len(HYDRO_SENSORS) == 6

    def test_meteo_sensor_count(self):
        assert len(METEO_SENSORS) == 10

    def test_warnings_meteo_sensor_count(self):
        assert len(WARNINGS_METEO_SENSORS) == 8

    def test_warnings_hydro_sensor_count(self):
        assert len(WARNINGS_HYDRO_SENSORS) == 8
