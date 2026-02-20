"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.imgw_pib_monitor.config_flow import (
    ImgwPibMonitorConfigFlow,
)
from custom_components.imgw_pib_monitor.const import (
    CONF_AUTO_DETECT,
    CONF_ENABLE_WARNINGS_HYDRO,
    CONF_ENABLE_WARNINGS_METEO,
    CONF_ENABLE_WEATHER_FORECAST,
    CONF_LOCATION_NAME,
    CONF_SELECTED_HYDRO,
    CONF_SELECTED_METEO,
    CONF_SELECTED_SYNOP,
    CONF_SETUP_MODE,
    CONF_UPDATE_INTERVAL,
    CONF_VOIVODESHIP,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SETUP_MODE_AUTO,
    SETUP_MODE_MANUAL,
    VOIVODESHIPS,
)

from .conftest import (
    SAMPLE_HYDRO_DATA,
    SAMPLE_METEO_DATA,
    SAMPLE_SYNOP_DATA,
)


def _make_flow_with_hass(lat=52.2297, lon=21.0122):
    """Create a config flow instance with a mocked hass."""
    flow = ImgwPibMonitorConfigFlow()

    hass = MagicMock()
    hass.config.latitude = lat
    hass.config.longitude = lon
    flow.hass = hass

    # Mock async_show_form, async_create_entry, async_abort
    flow.async_show_form = MagicMock()
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_abort = MagicMock(return_value={"type": "abort"})

    return flow


# ── Step: user (mode selection) ───────────────────────────────


class TestStepUser:
    """Tests for the initial user step — mode selection."""

    @pytest.mark.asyncio
    async def test_shows_form_without_input(self):
        flow = _make_flow_with_hass()

        await flow.async_step_user(user_input=None)
        flow.async_show_form.assert_called_once()
        call_kwargs = flow.async_show_form.call_args
        assert call_kwargs.kwargs.get("step_id") == "user" or call_kwargs[1].get("step_id") == "user"

    @pytest.mark.asyncio
    async def test_auto_mode_without_coordinates_shows_error(self):
        flow = _make_flow_with_hass(lat=None, lon=None)

        result = await flow.async_step_user({CONF_SETUP_MODE: SETUP_MODE_AUTO})
        flow.async_show_form.assert_called_once()
        call_kwargs = flow.async_show_form.call_args
        errors = call_kwargs.kwargs.get("errors") or call_kwargs[1].get("errors", {})
        assert errors.get("base") == "no_coordinates"


# ── Step: auto ────────────────────────────────────────────────


class TestStepAuto:
    """Tests for the automatic discovery step."""

    @pytest.mark.asyncio
    async def test_aborts_when_no_stations_nearby(self):
        flow = _make_flow_with_hass(lat=0.0, lon=0.0)  # In the ocean, no stations

        with patch(
            "custom_components.imgw_pib_monitor.config_flow.ImgwApiClient"
        ) as MockApiClient:
            api = MockApiClient.return_value
            api.get_all_synop_data = AsyncMock(return_value=SAMPLE_SYNOP_DATA)
            api.get_all_hydro_data = AsyncMock(return_value=SAMPLE_HYDRO_DATA)
            api.get_all_meteo_data = AsyncMock(return_value=SAMPLE_METEO_DATA)

            with patch(
                "custom_components.imgw_pib_monitor.config_flow.async_get_clientsession"
            ):
                await flow.async_step_auto()

        flow.async_abort.assert_called_once()
        assert flow.async_abort.call_args[1]["reason"] == "no_stations_nearby"

    @pytest.mark.asyncio
    async def test_aborts_on_api_error(self):
        flow = _make_flow_with_hass()

        with patch(
            "custom_components.imgw_pib_monitor.config_flow.ImgwApiClient"
        ) as MockApiClient:
            api = MockApiClient.return_value
            api.get_all_synop_data = AsyncMock(side_effect=Exception("API down"))
            api.get_all_hydro_data = AsyncMock(side_effect=Exception("API down"))
            api.get_all_meteo_data = AsyncMock(side_effect=Exception("API down"))

            with patch(
                "custom_components.imgw_pib_monitor.config_flow.async_get_clientsession"
            ):
                await flow.async_step_auto()

        flow.async_abort.assert_called_once()
        assert flow.async_abort.call_args[1]["reason"] == "cannot_connect"


# ── Step: auto_options ────────────────────────────────────────


class TestStepAutoOptions:
    """Tests for the auto options step (choosing data types)."""

    @pytest.mark.asyncio
    async def test_shows_form_without_input(self):
        flow = _make_flow_with_hass()
        flow._nearest_synop = "12375"
        flow._nearest_hydro = "150190370"
        flow._nearest_meteo = "249200080"

        await flow.async_step_auto_options(user_input=None)
        flow.async_show_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_entry_with_all_options(self):
        flow = _make_flow_with_hass()
        flow._nearest_synop = "12375"
        flow._nearest_hydro = "150190370"
        flow._nearest_meteo = "249200080"
        flow._detected_location_name = "Warszawa"

        user_input = {
            "add_synop": True,
            "add_meteo": True,
            "add_hydro": True,
            "enable_warnings_meteo": True,
            "enable_warnings_hydro": True,
            CONF_ENABLE_WEATHER_FORECAST: True,
        }

        await flow.async_step_auto_options(user_input=user_input)
        flow.async_create_entry.assert_called_once()

        call_kwargs = flow.async_create_entry.call_args[1]
        data = call_kwargs["data"]

        assert data[CONF_AUTO_DETECT] is True
        assert data[CONF_SELECTED_SYNOP] == ["12375"]
        assert data[CONF_SELECTED_HYDRO] == ["150190370"]
        assert data[CONF_SELECTED_METEO] == ["249200080"]
        assert data[CONF_ENABLE_WARNINGS_METEO] is True
        assert data[CONF_ENABLE_WARNINGS_HYDRO] is True
        assert data[CONF_ENABLE_WEATHER_FORECAST] is True
        assert data[CONF_LOCATION_NAME] == "Warszawa"
        assert call_kwargs["title"] == "Warszawa"

    @pytest.mark.asyncio
    async def test_creates_entry_synop_only(self):
        flow = _make_flow_with_hass()
        flow._nearest_synop = "12375"
        flow._nearest_hydro = None
        flow._nearest_meteo = None

        user_input = {
            "add_synop": True,
            "add_meteo": False,
            "add_hydro": False,
            "enable_warnings_meteo": False,
            "enable_warnings_hydro": False,
        }

        await flow.async_step_auto_options(user_input=user_input)
        flow.async_create_entry.assert_called_once()

        data = flow.async_create_entry.call_args[1]["data"]
        assert CONF_SELECTED_SYNOP in data
        assert CONF_SELECTED_HYDRO not in data
        assert CONF_SELECTED_METEO not in data
        assert CONF_ENABLE_WARNINGS_METEO not in data

    @pytest.mark.asyncio
    async def test_default_location_name(self):
        flow = _make_flow_with_hass()
        flow._nearest_synop = "12375"
        flow._detected_location_name = None

        user_input = {
            "add_synop": True,
            "enable_warnings_meteo": False,
            "enable_warnings_hydro": False,
        }

        await flow.async_step_auto_options(user_input=user_input)

        title = flow.async_create_entry.call_args[1]["title"]
        assert title == "IMGW Auto-Discovery"


# ── _infer_voivodeship ────────────────────────────────────────


class TestInferVoivodeship:
    """Tests for voivodeship inference from coordinates."""

    def test_warsaw_is_mazowieckie(self):
        flow = _make_flow_with_hass(lat=52.2297, lon=21.0122)
        result = flow._infer_voivodeship()
        assert result == "14"  # mazowieckie
        assert VOIVODESHIPS[result] == "mazowieckie"

    def test_krakow_is_malopolskie(self):
        flow = _make_flow_with_hass(lat=50.0647, lon=19.9450)
        result = flow._infer_voivodeship()
        assert result == "12"  # małopolskie

    def test_gdansk_is_pomorskie(self):
        flow = _make_flow_with_hass(lat=54.3520, lon=18.6466)
        result = flow._infer_voivodeship()
        assert result == "22"  # pomorskie

    def test_none_coordinates(self):
        flow = _make_flow_with_hass(lat=None, lon=None)
        result = flow._infer_voivodeship()
        assert result is None

    def test_infer_from_coords_method(self):
        flow = _make_flow_with_hass()
        result = flow._infer_voivodeship_from_coords((51.1079, 17.0385))
        assert result == "02"  # dolnośląskie (Wrocław)

    def test_infer_from_coords_none(self):
        flow = _make_flow_with_hass()
        result = flow._infer_voivodeship_from_coords(None)
        assert result is None


# ── Manual flow: manual_start ─────────────────────────────────


class TestStepManualStart:
    """Tests for the manual start step."""

    @pytest.mark.asyncio
    async def test_shows_form_without_input(self):
        flow = _make_flow_with_hass()

        await flow.async_step_manual_start(user_input=None)
        flow.async_show_form.assert_called_once()
        call_kwargs = flow.async_show_form.call_args
        assert call_kwargs.kwargs.get("step_id") == "manual_start" or call_kwargs[1].get("step_id") == "manual_start"

    @pytest.mark.asyncio
    async def test_stores_location_name(self):
        flow = _make_flow_with_hass()

        # Patch the next step to avoid it running
        flow.async_step_manual_select_location = AsyncMock(return_value={"type": "form"})

        await flow.async_step_manual_start({"location_name": "Kraków"})
        assert flow._data["location_name"] == "Kraków"
        flow.async_step_manual_select_location.assert_called_once()


# ── Manual flow: manual_options ───────────────────────────────


class TestStepManualOptions:
    """Tests for the manual options step."""

    @pytest.mark.asyncio
    async def test_creates_entry_with_manual_config(self):
        flow = _make_flow_with_hass()
        flow._nearest_synop = "12566"
        flow._nearest_hydro = None
        flow._nearest_meteo = None
        flow._location_coords = (50.0647, 19.9450)
        flow._detected_voivodeship = "12"
        flow._detected_location_name = "Kraków"
        flow._data = {"location_name": "Kraków"}

        user_input = {
            "add_synop": True,
            "add_meteo": False,
            "enable_warnings_meteo": True,
            "enable_warnings_hydro": False,
        }

        await flow.async_step_manual_options(user_input=user_input)
        flow.async_create_entry.assert_called_once()

        data = flow.async_create_entry.call_args[1]["data"]
        assert data[CONF_AUTO_DETECT] is False
        assert data[CONF_SELECTED_SYNOP] == ["12566"]
        assert data[CONF_ENABLE_WARNINGS_METEO] is True
        assert data[CONF_VOIVODESHIP] == "12"
        assert data[CONF_LOCATION_NAME] == "Kraków"
