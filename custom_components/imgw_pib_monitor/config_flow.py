"""Config flow for IMGW-PIB Monitor integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .api import ImgwApiClient, ImgwApiError
from .const import (
    CONF_AUTO_DETECT,
    CONF_ENABLE_WARNINGS_HYDRO,
    CONF_ENABLE_WARNINGS_METEO,
    CONF_SELECTED_HYDRO,
    CONF_SELECTED_METEO,
    CONF_SELECTED_SYNOP,
    CONF_SETUP_MODE,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    CONF_UPDATE_INTERVAL,
    CONF_VOIVODESHIP,
    DEFAULT_MAX_DISTANCE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    SETUP_MODE_AUTO,
    SETUP_MODE_MANUAL,
    SYNOP_STATIONS,
    VOIVODESHIP_CAPITALS,
)
from .utils import haversine

_LOGGER = logging.getLogger(__name__)

class ImgwPibMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a minimalist and smart config flow for IMGW-PIB Monitor."""

    VERSION = 6

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._found_stations: list[dict[str, Any]] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ImgwPibMonitorOptionsFlow:
        """Get the options flow for this handler."""
        return ImgwPibMonitorOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial choice: Automatic (GPS) or Manual Setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_SETUP_MODE] == SETUP_MODE_AUTO:
                if self.hass.config.latitude is None or self.hass.config.longitude is None:
                    errors["base"] = "no_coordinates"
                else:
                    return await self.async_step_auto()
            else:
                return await self.async_step_manual_start()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SETUP_MODE, default=SETUP_MODE_AUTO): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=SETUP_MODE_AUTO, label="auto"),
                                SelectOptionDict(value=SETUP_MODE_MANUAL, label="manual"),
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="setup_mode",
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_auto(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Automatic Path: Find nearest stations of EACH type and finish."""
        lat = self.hass.config.latitude
        lon = self.hass.config.longitude

        try:
            api = ImgwApiClient(async_get_clientsession(self.hass))
            results = await asyncio.gather(
                api.get_all_synop_data(),
                api.get_all_hydro_data(),
                api.get_all_meteo_data(),
            )
            synop_data, hydro_data, meteo_data = results

            def find_nearest_synop(stations):
                nearest, dist_min = None, DEFAULT_MAX_DISTANCE
                for s in stations:
                    sid = str(s.get("id_stacji"))
                    coords = SYNOP_STATIONS.get(sid)
                    if not coords:
                        continue
                    d = haversine(lat, lon, coords[0], coords[1])
                    if d < dist_min:
                        dist_min, nearest = d, sid
                return nearest

            def find_nearest(stations, lat_key, lon_key, id_key):
                nearest, dist_min = None, DEFAULT_MAX_DISTANCE
                for s in stations:
                    try:
                        s_lat = float(s.get(lat_key) or s.get("szerokosc") or 0)
                        s_lon = float(s.get(lon_key) or s.get("dlugosc") or 0)
                        if not s_lat or not s_lon:
                            continue
                        d = haversine(lat, lon, s_lat, s_lon)
                        if d < dist_min:
                            dist_min, nearest = d, s.get(id_key)
                    except (ValueError, TypeError):
                        continue
                return nearest

            # Find nearest for each type independently
            ns = find_nearest_synop(synop_data)
            nh = find_nearest(hydro_data, "lat", "lon", "id_stacji")
            nm = find_nearest(meteo_data, "lat", "lon", "kod_stacji")

            if not ns and not nh and not nm:
                return self.async_abort(reason="no_stations_nearby")

            final_config = {
                CONF_AUTO_DETECT: True,
                CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                CONF_ENABLE_WARNINGS_METEO: True,
                CONF_ENABLE_WARNINGS_HYDRO: True,
                CONF_VOIVODESHIP: self._infer_voivodeship(),
            }
            
            if ns:
                final_config[CONF_SELECTED_SYNOP] = [ns]
            if nh:
                final_config[CONF_SELECTED_HYDRO] = [nh]
            if nm:
                final_config[CONF_SELECTED_METEO] = [nm]

            return self.async_create_entry(title="IMGW Auto-Discovery", data=final_config)

        except Exception as e:
            _LOGGER.error("Auto-discovery failed: %s", e)
            return self.async_abort(reason="cannot_connect")

    async def async_step_manual_start(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual STEP 1: Search."""
        if user_input is not None:
            self._data[CONF_STATION_NAME] = user_input[CONF_STATION_NAME]
            return await self.async_step_select()

        return self.async_show_form(
            step_id="manual_start",
            data_schema=vol.Schema({
                vol.Required(CONF_STATION_NAME): TextSelector(TextSelectorConfig(type="text"))
            }),
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual STEP 2: Select Result."""
        errors: dict[str, str] = {}
        if user_input is not None:
            selected_station = next(
                s for s in self._found_stations if f"{s['type']}:{s['id']}" == user_input[CONF_STATION_ID]
            )
            self._data.update(selected_station)
            return await self.async_step_options()

        if not self._found_stations:
            try:
                api = ImgwApiClient(async_get_clientsession(self.hass))
                q = self._data[CONF_STATION_NAME].lower()
                synop = await api.get_synop_stations()
                hydro = await api.get_hydro_stations()
                meteo = await api.get_meteo_stations()
                for sid, name in synop.items():
                    if q in name.lower():
                        self._found_stations.append({"id": sid, "name": name, "type": "synop", "label": f"{name} (Weather)"})
                for sid, name in hydro.items():
                    if q in name.lower():
                        self._found_stations.append({"id": sid, "name": name, "type": "hydro", "label": f"{name} (River)"})
                for sid, name in meteo.items():
                    if q in name.lower():
                        self._found_stations.append({"id": sid, "name": name, "type": "meteo", "label": f"{name} (Meteo)"})
            except ImgwApiError:
                errors["base"] = "cannot_connect"

        if not self._found_stations and not errors:
            errors["base"] = "no_stations"
        if errors:
            return self.async_show_form(step_id="manual_start", errors=errors)

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({
                vol.Required(CONF_STATION_ID): SelectSelector(SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=f"{s['type']}:{s['id']}", label=s['label'])
                        for s in self._found_stations
                    ],
                    mode=SelectSelectorMode.DROPDOWN
                ))
            }),
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual STEP 3: Toggles."""
        if user_input is not None:
            final_config = {
                CONF_AUTO_DETECT: False,
                CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            }
            st, sid = self._data["type"], self._data["id"]
            if user_input.get("weather"):
                if st == "synop":
                    final_config[CONF_SELECTED_SYNOP] = [sid]
                elif st == "meteo":
                    final_config[CONF_SELECTED_METEO] = [sid]
            if user_input.get("river") and st == "hydro":
                final_config[CONF_SELECTED_HYDRO] = [sid]
            if user_input.get("warnings"):
                final_config[CONF_ENABLE_WARNINGS_METEO] = True
                final_config[CONF_ENABLE_WARNINGS_HYDRO] = True
                final_config[CONF_VOIVODESHIP] = self._infer_voivodeship()
            return self.async_create_entry(title=self._data["name"], data=final_config)

        schema = {}
        if self._data["type"] in ("synop", "meteo"):
            schema[vol.Optional("weather", default=True)] = BooleanSelector()
        if self._data["type"] == "hydro":
            schema[vol.Optional("river", default=True)] = BooleanSelector()
        schema[vol.Optional("warnings", default=True)] = BooleanSelector()
        return self.async_show_form(step_id="options", data_schema=vol.Schema(schema))

    def _infer_voivodeship(self) -> str | None:
        """Infer voivodeship from coordinates."""
        lat, lon = self.hass.config.latitude, self.hass.config.longitude
        if lat is None or lon is None:
            return None
        min_d, best_c = float("inf"), None
        for c, coords in VOIVODESHIP_CAPITALS.items():
            d = haversine(lat, lon, coords[0], coords[1])
            if d < min_d:
                min_d, best_c = d, c
        return best_c

class ImgwPibMonitorOptionsFlow(OptionsFlow):
    """Handle options flow."""
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(
                CONF_UPDATE_INTERVAL, 
                default=self._config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL))
        }))
