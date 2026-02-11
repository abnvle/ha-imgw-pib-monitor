"""Config flow for IMGW-PIB Monitor integration."""

from __future__ import annotations

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
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import ImgwApiClient, ImgwApiError
from .const import (
    CONF_DATA_TYPE,
    CONF_POWIAT,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    CONF_UPDATE_INTERVAL,
    CONF_VOIVODESHIP,
    DATA_TYPE_HYDRO,
    DATA_TYPE_METEO,
    DATA_TYPE_SYNOP,
    DATA_TYPE_WARNINGS_HYDRO,
    DATA_TYPE_WARNINGS_METEO,
    DATA_TYPES,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_WARNINGS,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    VOIVODESHIPS,
)
from .teryt import POWIATY

_LOGGER = logging.getLogger(__name__)

POWIAT_ALL = "all"


def _station_selector(stations: dict[str, str]) -> SelectSelector:
    """Build a station SelectSelector."""
    sorted_stations = sorted(stations.items(), key=lambda x: x[1])
    options = [
        SelectOptionDict(value=sid, label=name)
        for sid, name in sorted_stations
    ]
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _voivodeship_selector() -> SelectSelector:
    """Build a voivodeship SelectSelector."""
    sorted_voivodeships = sorted(VOIVODESHIPS.items(), key=lambda x: x[1])
    options = [
        SelectOptionDict(value=code, label=name)
        for code, name in sorted_voivodeships
    ]
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _powiat_selector(voivodeship_code: str) -> SelectSelector:
    """Build a powiat SelectSelector for given voivodeship."""
    powiaty = POWIATY.get(voivodeship_code, {})
    sorted_powiaty = sorted(powiaty.items(), key=lambda x: x[1])

    options = [
        SelectOptionDict(value=POWIAT_ALL, label="— Całe województwo —"),
    ]
    options.extend(
        SelectOptionDict(value=code, label=f"pow. {name}")
        for code, name in sorted_powiaty
    )
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class ImgwPibMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IMGW-PIB Monitor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._stations: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ImgwPibMonitorOptionsFlow:
        """Get the options flow for this handler."""
        return ImgwPibMonitorOptionsFlow(config_entry)

    async def _fetch_stations(self) -> dict[str, str]:
        """Fetch station list based on selected data type."""
        api = ImgwApiClient(async_get_clientsession(self.hass))
        data_type = self._data[CONF_DATA_TYPE]

        if data_type == DATA_TYPE_SYNOP:
            return await api.get_synop_stations()
        elif data_type == DATA_TYPE_HYDRO:
            return await api.get_hydro_stations()
        elif data_type == DATA_TYPE_METEO:
            return await api.get_meteo_stations()
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Choose data type."""
        if user_input is not None:
            self._data[CONF_DATA_TYPE] = user_input[CONF_DATA_TYPE]

            if user_input[CONF_DATA_TYPE] == DATA_TYPE_WARNINGS_METEO:
                return await self.async_step_voivodeship()
            if user_input[CONF_DATA_TYPE] == DATA_TYPE_WARNINGS_HYDRO:
                return await self.async_step_voivodeship_hydro()
            return await self.async_step_station()

        data_type_options = [
            SelectOptionDict(value=k, label=v)
            for k, v in DATA_TYPES.items()
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DATA_TYPE): SelectSelector(
                        SelectSelectorConfig(
                            options=data_type_options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2a: Choose station."""
        errors: dict[str, str] = {}

        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]
            station_name = self._stations.get(station_id, station_id)
            self._data[CONF_STATION_ID] = station_id
            self._data[CONF_STATION_NAME] = station_name
            return await self.async_step_interval()

        if not self._stations:
            try:
                self._stations = await self._fetch_stations()
                if not self._stations:
                    errors["base"] = "no_stations"
            except ImgwApiError:
                errors["base"] = "cannot_connect"

        if errors:
            return self.async_show_form(
                step_id="station",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID): _station_selector(
                        self._stations
                    ),
                }
            ),
        )

    async def async_step_voivodeship(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2b: Choose voivodeship (for meteo warnings → then powiat)."""
        if user_input is not None:
            self._data[CONF_VOIVODESHIP] = user_input[CONF_VOIVODESHIP]
            return await self.async_step_powiat()

        return self.async_show_form(
            step_id="voivodeship",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VOIVODESHIP): _voivodeship_selector(),
                }
            ),
        )

    async def async_step_powiat(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2c: Choose powiat within voivodeship (meteo warnings)."""
        if user_input is not None:
            self._data[CONF_POWIAT] = user_input[CONF_POWIAT]
            return await self.async_step_interval()

        voivodeship_code = self._data[CONF_VOIVODESHIP]

        return self.async_show_form(
            step_id="powiat",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POWIAT, default=POWIAT_ALL
                    ): _powiat_selector(voivodeship_code),
                }
            ),
        )

    async def async_step_voivodeship_hydro(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2d: Choose voivodeship (for hydro warnings — no powiat)."""
        if user_input is not None:
            self._data[CONF_VOIVODESHIP] = user_input[CONF_VOIVODESHIP]
            return await self.async_step_interval()

        return self.async_show_form(
            step_id="voivodeship_hydro",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VOIVODESHIP): _voivodeship_selector(),
                }
            ),
        )

    async def async_step_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: Configure update interval."""
        if user_input is not None:
            self._data[CONF_UPDATE_INTERVAL] = user_input[CONF_UPDATE_INTERVAL]

            data_type = self._data[CONF_DATA_TYPE]
            if data_type == DATA_TYPE_WARNINGS_METEO:
                powiat = self._data.get(CONF_POWIAT, POWIAT_ALL)
                if powiat == POWIAT_ALL:
                    unique_id = f"{data_type}_{self._data[CONF_VOIVODESHIP]}"
                else:
                    unique_id = f"{data_type}_{powiat}"
            else:
                station_or_voiv = self._data.get(CONF_STATION_ID) or self._data.get(
                    CONF_VOIVODESHIP
                )
                unique_id = f"{data_type}_{station_or_voiv}"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            title = self._build_title()
            return self.async_create_entry(title=title, data=self._data)

        is_warning = self._data[CONF_DATA_TYPE] in (
            DATA_TYPE_WARNINGS_METEO,
            DATA_TYPE_WARNINGS_HYDRO,
        )
        default = (
            DEFAULT_UPDATE_INTERVAL_WARNINGS if is_warning else DEFAULT_UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="interval",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UPDATE_INTERVAL, default=default): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                    ),
                }
            ),
        )

    def _build_title(self) -> str:
        """Build a descriptive title for the config entry."""
        data_type = self._data[CONF_DATA_TYPE]
        type_label = DATA_TYPES.get(data_type, data_type)

        if data_type == DATA_TYPE_WARNINGS_METEO:
            voiv_code = self._data.get(CONF_VOIVODESHIP, "")
            voiv_name = VOIVODESHIPS.get(voiv_code, voiv_code)
            powiat_code = self._data.get(CONF_POWIAT, POWIAT_ALL)
            if powiat_code != POWIAT_ALL:
                powiaty = POWIATY.get(voiv_code, {})
                powiat_name = powiaty.get(powiat_code, powiat_code)
                return f"IMGW {type_label} — pow. {powiat_name}"
            return f"IMGW {type_label} — woj. {voiv_name}"

        if data_type == DATA_TYPE_WARNINGS_HYDRO:
            voiv_code = self._data.get(CONF_VOIVODESHIP, "")
            voiv_name = VOIVODESHIPS.get(voiv_code, voiv_code)
            return f"IMGW {type_label} — {voiv_name}"

        station_name = self._data.get(CONF_STATION_NAME, "")
        return f"IMGW {type_label} — {station_name}"


class ImgwPibMonitorOptionsFlow(OptionsFlow):
    """Handle options for IMGW-PIB Monitor."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            new_data = {**self._config_entry.data, **user_input}

            # Resolve station name if station was changed
            if CONF_STATION_ID in user_input:
                data_type = self._config_entry.data.get(CONF_DATA_TYPE)
                try:
                    api = ImgwApiClient(async_get_clientsession(self.hass))
                    if data_type == DATA_TYPE_SYNOP:
                        stations = await api.get_synop_stations()
                    elif data_type == DATA_TYPE_HYDRO:
                        stations = await api.get_hydro_stations()
                    else:
                        stations = await api.get_meteo_stations()
                    new_data[CONF_STATION_NAME] = stations.get(
                        user_input[CONF_STATION_ID],
                        user_input[CONF_STATION_ID],
                    )
                except ImgwApiError:
                    pass

            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            return self.async_create_entry(title="", data=user_input)

        data_type = self._config_entry.data.get(CONF_DATA_TYPE)
        current_interval = self._config_entry.data.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_UPDATE_INTERVAL, default=current_interval): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
            ),
        }

        # Station-based types
        if data_type in (DATA_TYPE_SYNOP, DATA_TYPE_HYDRO, DATA_TYPE_METEO):
            try:
                api = ImgwApiClient(async_get_clientsession(self.hass))
                if data_type == DATA_TYPE_SYNOP:
                    stations = await api.get_synop_stations()
                elif data_type == DATA_TYPE_HYDRO:
                    stations = await api.get_hydro_stations()
                else:
                    stations = await api.get_meteo_stations()

                current_station = self._config_entry.data.get(CONF_STATION_ID)
                schema_dict[
                    vol.Required(CONF_STATION_ID, default=current_station)
                ] = _station_selector(stations)
            except ImgwApiError:
                _LOGGER.warning("Could not fetch stations for options flow")

        # Meteo warnings — powiat selection
        if data_type == DATA_TYPE_WARNINGS_METEO:
            voiv_code = self._config_entry.data.get(CONF_VOIVODESHIP)
            current_powiat = self._config_entry.data.get(CONF_POWIAT, POWIAT_ALL)

            schema_dict[
                vol.Required(CONF_VOIVODESHIP, default=voiv_code)
            ] = _voivodeship_selector()

            if voiv_code:
                schema_dict[
                    vol.Required(CONF_POWIAT, default=current_powiat)
                ] = _powiat_selector(voiv_code)

        # Hydro warnings — voivodeship only
        if data_type == DATA_TYPE_WARNINGS_HYDRO:
            current_voiv = self._config_entry.data.get(CONF_VOIVODESHIP)
            schema_dict[
                vol.Required(CONF_VOIVODESHIP, default=current_voiv)
            ] = _voivodeship_selector()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )