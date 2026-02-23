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
    CONF_ENABLE_WEATHER_FORECAST,
    CONF_FORECAST_LAT,
    CONF_FORECAST_LON,
    CONF_LOCATION_NAME,
    CONF_POWIAT,
    CONF_POWIAT_NAME,
    CONF_SELECTED_HYDRO,
    CONF_SELECTED_METEO,
    CONF_SELECTED_SYNOP,
    CONF_SETUP_MODE,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    CONF_UPDATE_INTERVAL,
    CONF_USE_POWIAT_FOR_WARNINGS,
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
    VOIVODESHIPS,
)
from .utils import geocode_location, haversine, nominatim_reverse_geocode, reverse_geocode

_LOGGER = logging.getLogger(__name__)


def _find_nearest_synop(
    stations: list[dict[str, Any]], lat: float, lon: float
) -> str | None:
    """Find nearest SYNOP station using hardcoded coordinates."""
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


def _find_nearest_station(
    stations: list[dict[str, Any]],
    lat: float,
    lon: float,
    lat_key: str,
    lon_key: str,
    id_key: str,
) -> str | None:
    """Find nearest station using coordinates from API data."""
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


class ImgwPibMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a minimalist and smart config flow for IMGW-PIB Monitor."""

    VERSION = 8

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._found_stations: list[dict[str, Any]] = []
        self._nearest_synop: str | None = None
        self._nearest_hydro: str | None = None
        self._nearest_meteo: str | None = None
        self._location_coords: tuple[float, float] | None = None
        self._detected_powiat_code: str | None = None
        self._detected_powiat_name: str | None = None
        self._detected_voivodeship: str | None = None
        self._detected_location_name: str | None = None
        self._location_results: list[tuple[float, float, dict[str, Any], str]] = []

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
        """Automatic Path: Find nearest stations of EACH type and show options."""
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

            # Find nearest for each type independently
            self._nearest_synop = _find_nearest_synop(synop_data, lat, lon)
            self._nearest_hydro = _find_nearest_station(hydro_data, lat, lon, "lat", "lon", "id_stacji")
            self._nearest_meteo = _find_nearest_station(meteo_data, lat, lon, "lat", "lon", "kod_stacji")
            self._location_coords = (lat, lon)

            # Get location name from Nominatim, then use it to query IMGW for admin details
            try:
                session = async_get_clientsession(self.hass)

                # Step 1: Nominatim reverse geocoding to get city/village name
                nominatim_name = await nominatim_reverse_geocode(session, lat, lon)
                if nominatim_name:
                    self._detected_location_name = nominatim_name
                    _LOGGER.debug("Auto-discovery: Nominatim returned: %s", nominatim_name)

                    # Step 2: Use that name to query IMGW API for administrative details
                    location_details = await reverse_geocode(
                        session, lat, lon, [nominatim_name]
                    )
                    if location_details:
                        _LOGGER.debug(
                            "Auto-discovery: IMGW details - province: %s, district: %s, teryt: %s",
                            location_details.get("province"),
                            location_details.get("district"),
                            location_details.get("teryt"),
                        )

                        # Get voivodeship from API response
                        province_name = location_details.get("province", "")
                        if province_name:
                            for voiv_code, voiv_name in VOIVODESHIPS.items():
                                if voiv_name.lower() == province_name.lower():
                                    self._detected_voivodeship = voiv_code
                                    _LOGGER.debug(
                                        "Auto-discovery: voivodeship: %s -> %s",
                                        province_name, voiv_name,
                                    )
                                    break

                        # Get powiat code and name
                        teryt_code = location_details.get("teryt")
                        district_name = location_details.get("district")
                        if teryt_code and district_name:
                            self._detected_powiat_code = teryt_code
                            self._detected_powiat_name = district_name
                            _LOGGER.debug(
                                "Auto-discovery: powiat: %s (%s)",
                                district_name, teryt_code,
                            )

                        # Use IMGW name if more precise
                        imgw_name = location_details.get("name")
                        if imgw_name:
                            self._detected_location_name = imgw_name
            except Exception as e:
                _LOGGER.debug("Auto-discovery location detection failed: %s", e)

            if not self._nearest_synop and not self._nearest_hydro and not self._nearest_meteo:
                return self.async_abort(reason="no_stations_nearby")

            return await self.async_step_auto_options()

        except Exception as e:
            _LOGGER.error("Auto-discovery failed: %s", e)
            return self.async_abort(reason="cannot_connect")

    async def async_step_auto_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Auto STEP 2: Choose which data types to add."""
        if user_input is not None:
            final_config = {
                CONF_AUTO_DETECT: True,
                CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            }

            # Add selected station types
            if user_input.get("add_synop") and self._nearest_synop:
                final_config[CONF_SELECTED_SYNOP] = [self._nearest_synop]
            if user_input.get("add_meteo") and self._nearest_meteo:
                final_config[CONF_SELECTED_METEO] = [self._nearest_meteo]
            if user_input.get("add_hydro") and self._nearest_hydro:
                final_config[CONF_SELECTED_HYDRO] = [self._nearest_hydro]

            # Add warnings
            if user_input.get("enable_warnings_meteo") or user_input.get("enable_warnings_hydro"):
                voivodeship = self._infer_voivodeship()
                final_config[CONF_VOIVODESHIP] = voivodeship

                # Check if user wants powiat-level filtering
                if user_input.get(CONF_USE_POWIAT_FOR_WARNINGS) and self._detected_powiat_code:
                    final_config[CONF_POWIAT] = self._detected_powiat_code
                    final_config[CONF_POWIAT_NAME] = self._detected_powiat_name
                    final_config[CONF_USE_POWIAT_FOR_WARNINGS] = True

            if user_input.get("enable_warnings_meteo"):
                final_config[CONF_ENABLE_WARNINGS_METEO] = True
            if user_input.get("enable_warnings_hydro"):
                final_config[CONF_ENABLE_WARNINGS_HYDRO] = True

            # Weather forecast
            if user_input.get(CONF_ENABLE_WEATHER_FORECAST):
                final_config[CONF_ENABLE_WEATHER_FORECAST] = True
                final_config[CONF_FORECAST_LAT] = self.hass.config.latitude
                final_config[CONF_FORECAST_LON] = self.hass.config.longitude

            # Location name
            loc_name = self._detected_location_name or "IMGW Auto-Discovery"
            final_config[CONF_LOCATION_NAME] = loc_name

            return self.async_create_entry(title=loc_name, data=final_config)

        # Build schema based on available stations
        schema = {}

        # Weather data (SYNOP or METEO)
        if self._nearest_synop or self._nearest_meteo:
            schema[vol.Optional("add_synop", default=bool(self._nearest_synop))] = BooleanSelector()
            schema[vol.Optional("add_meteo", default=bool(self._nearest_meteo))] = BooleanSelector()

        # Hydro data
        if self._nearest_hydro:
            schema[vol.Optional("add_hydro", default=True)] = BooleanSelector()

        # Warnings
        schema[vol.Optional("enable_warnings_meteo", default=True)] = BooleanSelector()
        schema[vol.Optional("enable_warnings_hydro", default=True)] = BooleanSelector()

        # Powiat filtering checkbox (only if powiat was detected)
        if self._detected_powiat_code and self._detected_powiat_name:
            schema[vol.Optional(CONF_USE_POWIAT_FOR_WARNINGS, default=False)] = BooleanSelector()

        # Weather forecast
        schema[vol.Optional(CONF_ENABLE_WEATHER_FORECAST, default=False)] = BooleanSelector()

        return self.async_show_form(step_id="auto_options", data_schema=vol.Schema(schema))

    async def async_step_manual_start(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual STEP 1: Enter location name."""
        if user_input is not None:
            self._data["location_name"] = user_input["location_name"]
            return await self.async_step_manual_select_location()

        return self.async_show_form(
            step_id="manual_start",
            data_schema=vol.Schema({
                vol.Required("location_name"): TextSelector(TextSelectorConfig(
                    type="text",
                    autocomplete="off"
                ))
            }),
        )

    async def async_step_manual_select_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual STEP 2: Select location from geocoding results."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User selected a location
            selected_index = int(user_input["location_choice"])
            if 0 <= selected_index < len(self._location_results):
                lat, lon, location_details, display_name = self._location_results[selected_index]
                self._location_coords = (lat, lon)

                _LOGGER.debug("Selected location - province: %s, district: %s, teryt: %s",
                             location_details.get("province"), location_details.get("district"),
                             location_details.get("teryt"))

                # Get voivodeship from API response (province field)
                province_name = location_details.get("province", "")
                voivodeship = None

                # Match province name to voivodeship code
                if province_name:
                    for voiv_code, voiv_name in VOIVODESHIPS.items():
                        if voiv_name.lower() == province_name.lower():
                            voivodeship = voiv_code
                            _LOGGER.debug(
                                "Detected voivodeship from API: %s -> %s (%s)",
                                province_name, voiv_name, voiv_code
                            )
                            break

                # Fallback to distance-based detection if province name doesn't match
                if not voivodeship:
                    voivodeship = self._infer_voivodeship_from_coords((lat, lon))
                    _LOGGER.debug(
                        "Fallback: detected voivodeship from coordinates: %s (%s)",
                        VOIVODESHIPS.get(voivodeship, voivodeship), voivodeship
                    )

                # Store the detected voivodeship for later use
                self._detected_voivodeship = voivodeship

                # Get powiat code and name directly from API response
                teryt_code = location_details.get("teryt")
                district_name = location_details.get("district")

                if teryt_code and district_name:
                    self._detected_powiat_code = teryt_code
                    self._detected_powiat_name = district_name
                    _LOGGER.debug(
                        "Detected powiat from API: %s (%s)",
                        district_name, teryt_code
                    )

                # Store the most precise location name from geocoding
                loc_name = location_details.get("name")
                if loc_name:
                    self._detected_location_name = loc_name

                return await self.async_step_manual_find_stations()
            else:
                errors["base"] = "invalid_selection"

        # Geocode the location
        if not self._location_results:
            try:
                location_name = self._data["location_name"]
                geocode_results = await geocode_location(
                    async_get_clientsession(self.hass), location_name, limit=50
                )

                if not geocode_results:
                    errors["base"] = "location_not_found"
                    return self.async_show_form(
                        step_id="manual_start",
                        data_schema=vol.Schema({
                            vol.Required("location_name", default=location_name): TextSelector(
                                TextSelectorConfig(type="text", autocomplete="off")
                            )
                        }),
                        errors=errors,
                    )

                self._location_results = geocode_results

            except Exception as e:
                _LOGGER.error("Geocoding failed: %s", e)
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="manual_start",
                    data_schema=vol.Schema({
                        vol.Required("location_name", default=self._data.get("location_name", "")): TextSelector(
                            TextSelectorConfig(type="text", autocomplete="off")
                        )
                    }),
                    errors=errors,
                )

        # Build location options
        location_options = []
        for i, (lat, lon, location_details, display_name) in enumerate(self._location_results):
            # Format: "Miejscowość (gmina, powiat, województwo)"
            name = location_details.get("name")
            commune = location_details.get("commune")
            district = location_details.get("district")
            province = location_details.get("province")

            # Build label - only add non-empty, unique parts
            parts = []
            if name:
                parts.append(name)

            # Add commune if different from name
            if commune and commune != name:
                parts.append(f"gm. {commune}")

            # Add district if different from name and commune
            if district and district != name and district != commune:
                parts.append(district)

            # Always add province
            if province:
                parts.append(province)

            # Build final label
            if not parts:
                label = display_name
            elif len(parts) == 1:
                label = parts[0]
            else:
                label = f"{parts[0]} ({', '.join(parts[1:])})"

            location_options.append(SelectOptionDict(value=str(i), label=label))

        return self.async_show_form(
            step_id="manual_select_location",
            data_schema=vol.Schema({
                vol.Required("location_choice"): SelectSelector(
                    SelectSelectorConfig(
                        options=location_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }),
            errors=errors,
        )

    async def async_step_manual_find_stations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual STEP 3: Find nearest stations."""
        errors: dict[str, str] = {}

        try:
            # Use coordinates from selected location
            api = ImgwApiClient(async_get_clientsession(self.hass))
            lat, lon = self._location_coords

            # Find nearest stations
            results = await asyncio.gather(
                api.get_all_synop_data(),
                api.get_all_hydro_data(),
                api.get_all_meteo_data(),
            )
            synop_data, hydro_data, meteo_data = results

            # Find nearest for each type independently
            self._nearest_synop = _find_nearest_synop(synop_data, lat, lon)
            self._nearest_hydro = _find_nearest_station(hydro_data, lat, lon, "lat", "lon", "id_stacji")
            self._nearest_meteo = _find_nearest_station(meteo_data, lat, lon, "lat", "lon", "kod_stacji")

            if not self._nearest_synop and not self._nearest_hydro and not self._nearest_meteo:
                errors["base"] = "no_stations_nearby"
                return self.async_show_form(
                    step_id="manual_start",
                    data_schema=vol.Schema({
                        vol.Required("location_name", default=self._data.get("location_name", "")): TextSelector(
                            TextSelectorConfig(type="text", autocomplete="off")
                        )
                    }),
                    errors=errors,
                )

            return await self.async_step_manual_options()

        except Exception as e:
            _LOGGER.error("Manual station finding failed: %s", e)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="manual_start",
                data_schema=vol.Schema({
                    vol.Required("location_name", default=self._data.get("location_name", "")): TextSelector(
                        TextSelectorConfig(type="text", autocomplete="off")
                    )
                }),
                errors=errors,
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

    async def async_step_manual_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual STEP 3: Choose which data types to add."""
        if user_input is not None:
            final_config = {
                CONF_AUTO_DETECT: False,
                CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            }

            # Add selected station types
            if user_input.get("add_synop") and self._nearest_synop:
                final_config[CONF_SELECTED_SYNOP] = [self._nearest_synop]
            if user_input.get("add_meteo") and self._nearest_meteo:
                final_config[CONF_SELECTED_METEO] = [self._nearest_meteo]
            if user_input.get("add_hydro") and self._nearest_hydro:
                final_config[CONF_SELECTED_HYDRO] = [self._nearest_hydro]

            # Add warnings
            if user_input.get("enable_warnings_meteo") or user_input.get("enable_warnings_hydro"):
                # Use the voivodeship detected in manual_select_location, fallback to distance-based
                voivodeship = self._detected_voivodeship or self._infer_voivodeship_from_coords(self._location_coords)
                final_config[CONF_VOIVODESHIP] = voivodeship
                _LOGGER.debug(
                    "Using voivodeship for warnings: %s (%s)",
                    VOIVODESHIPS.get(voivodeship), voivodeship
                )

                # Check if user wants powiat-level filtering
                if user_input.get(CONF_USE_POWIAT_FOR_WARNINGS) and self._detected_powiat_code:
                    final_config[CONF_POWIAT] = self._detected_powiat_code
                    final_config[CONF_POWIAT_NAME] = self._detected_powiat_name
                    final_config[CONF_USE_POWIAT_FOR_WARNINGS] = True

            if user_input.get("enable_warnings_meteo"):
                final_config[CONF_ENABLE_WARNINGS_METEO] = True
            if user_input.get("enable_warnings_hydro"):
                final_config[CONF_ENABLE_WARNINGS_HYDRO] = True

            # Weather forecast
            if user_input.get(CONF_ENABLE_WEATHER_FORECAST):
                final_config[CONF_ENABLE_WEATHER_FORECAST] = True
                lat, lon = self._location_coords
                final_config[CONF_FORECAST_LAT] = lat
                final_config[CONF_FORECAST_LON] = lon

            # Location name
            location_name = self._detected_location_name or self._data.get("location_name", "Manual Setup")
            final_config[CONF_LOCATION_NAME] = location_name

            return self.async_create_entry(title=location_name, data=final_config)

        # Build schema based on available stations
        schema = {}

        # Weather data (SYNOP or METEO)
        if self._nearest_synop or self._nearest_meteo:
            schema[vol.Optional("add_synop", default=bool(self._nearest_synop))] = BooleanSelector()
            schema[vol.Optional("add_meteo", default=bool(self._nearest_meteo))] = BooleanSelector()

        # Hydro data
        if self._nearest_hydro:
            schema[vol.Optional("add_hydro", default=True)] = BooleanSelector()

        # Warnings
        schema[vol.Optional("enable_warnings_meteo", default=True)] = BooleanSelector()
        schema[vol.Optional("enable_warnings_hydro", default=True)] = BooleanSelector()

        # Powiat filtering checkbox (only if powiat was detected)
        if self._detected_powiat_code and self._detected_powiat_name:
            schema[vol.Optional(CONF_USE_POWIAT_FOR_WARNINGS, default=False)] = BooleanSelector()

        # Weather forecast
        schema[vol.Optional(CONF_ENABLE_WEATHER_FORECAST, default=False)] = BooleanSelector()

        return self.async_show_form(step_id="manual_options", data_schema=vol.Schema(schema))

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual STEP 3: Toggles (OLD - kept for backward compatibility)."""
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
        """Infer voivodeship from Home Assistant coordinates."""
        lat, lon = self.hass.config.latitude, self.hass.config.longitude
        if lat is None or lon is None:
            return None
        min_d, best_c = float("inf"), None
        for c, coords in VOIVODESHIP_CAPITALS.items():
            d = haversine(lat, lon, coords[0], coords[1])
            if d < min_d:
                min_d, best_c = d, c
        return best_c

    def _infer_voivodeship_from_coords(self, coords: tuple[float, float] | None) -> str | None:
        """Infer voivodeship from given coordinates."""
        if not coords:
            return None
        lat, lon = coords
        min_d, best_c = float("inf"), None
        for c, coord_pair in VOIVODESHIP_CAPITALS.items():
            d = haversine(lat, lon, coord_pair[0], coord_pair[1])
            if d < min_d:
                min_d, best_c = d, c
        return best_c

class ImgwPibMonitorOptionsFlow(OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            # Merge new options into existing config entry data
            new_data = {**self._config_entry.data}
            new_data[CONF_UPDATE_INTERVAL] = user_input[CONF_UPDATE_INTERVAL]

            # Handle weather forecast toggle
            enable_forecast = user_input.get(CONF_ENABLE_WEATHER_FORECAST, False)
            new_data[CONF_ENABLE_WEATHER_FORECAST] = enable_forecast

            if enable_forecast and CONF_FORECAST_LAT not in new_data:
                # First time enabling forecast — use HA coordinates as fallback
                new_data[CONF_FORECAST_LAT] = self.hass.config.latitude
                new_data[CONF_FORECAST_LON] = self.hass.config.longitude

            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            return self.async_create_entry(title="", data={})

        current_forecast = self._config_entry.data.get(
            CONF_ENABLE_WEATHER_FORECAST, False
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=self._config_entry.data.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_ENABLE_WEATHER_FORECAST,
                        default=current_forecast,
                    ): BooleanSelector(),
                }
            ),
        )
