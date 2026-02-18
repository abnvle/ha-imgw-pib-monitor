"""IMGW-PIB Monitor — comprehensive integration for IMGW-PIB data."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ImgwApiClient
from .const import (
    CONF_ENABLE_WEATHER_FORECAST,
    CONF_FORECAST_LAT,
    CONF_FORECAST_LON,
    CONF_LOCATION_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import (
    ImgwDataUpdateCoordinator,
    ImgwForecastCoordinator,
    ImgwGlobalDataCoordinator,
)

_LOGGER = logging.getLogger(__name__)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register frontend resources (only once, only when needed)."""
    if hass.data.get(DOMAIN, {}).get("_frontend_registered"):
        return

    from .frontend import JSModuleRegistration

    module_register = JSModuleRegistration(hass)
    await module_register.async_register()
    hass.data.setdefault(DOMAIN, {})["_frontend_registered"] = True
    _LOGGER.debug("IMGW Weather frontend registered")


async def _async_unregister_frontend(hass: HomeAssistant) -> None:
    """Remove frontend resources when no forecast entries remain."""
    from .frontend import JSModuleRegistration

    module_register = JSModuleRegistration(hass)
    await module_register.async_unregister()
    hass.data.get(DOMAIN, {}).pop("_frontend_registered", None)
    _LOGGER.debug("IMGW Weather frontend unregistered")



def _async_cleanup_forecast(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove forecast entity and device from registries when forecast is disabled."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "weather", DOMAIN, f"{DOMAIN}_weather_{entry.entry_id}"
    )
    if entity_id:
        ent_reg.async_remove(entity_id)
        _LOGGER.debug("Removed forecast entity: %s", entity_id)

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(
        identifiers={(DOMAIN, f"forecast_{entry.entry_id}")}
    )
    if device:
        dev_reg.async_remove_device(device.id)
        _LOGGER.debug("Removed forecast device: %s", device.name)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IMGW-PIB Monitor from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    # Initialize global coordinator if not already present
    if "global_coordinator" not in hass.data[DOMAIN]:
        session = async_get_clientsession(hass)
        api = ImgwApiClient(session)
        hass.data[DOMAIN]["global_coordinator"] = ImgwGlobalDataCoordinator(
            hass, api, update_interval
        )
    else:
        # Sync global coordinator interval to the shortest across all entries
        global_coord = hass.data[DOMAIN]["global_coordinator"]
        min_interval = update_interval
        for other_entry in hass.config_entries.async_entries(DOMAIN):
            if other_entry.entry_id != entry.entry_id:
                other_interval = other_entry.data.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                )
                min_interval = min(min_interval, other_interval)
        global_coord.update_interval = timedelta(minutes=min_interval)

    global_coordinator = hass.data[DOMAIN]["global_coordinator"]

    coordinator = ImgwDataUpdateCoordinator(
        hass=hass,
        global_coordinator=global_coordinator,
        entry=entry,
        update_interval=update_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Determine which platforms to load
    platforms = ["sensor"]

    # Forecast support (weather platform)
    if entry.data.get(CONF_ENABLE_WEATHER_FORECAST):
        lat = entry.data.get(CONF_FORECAST_LAT, hass.config.latitude)
        lon = entry.data.get(CONF_FORECAST_LON, hass.config.longitude)

        forecast_coordinator = ImgwForecastCoordinator(hass, lat, lon, update_interval)
        await forecast_coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][f"{entry.entry_id}_forecast"] = forecast_coordinator
        platforms.append("weather")
    else:
        # Forecast disabled — clean up leftover entity/device from registry
        _async_cleanup_forecast(hass, entry)

    # Register frontend resources (always, so the card is available)
    await _async_register_frontend(hass)

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to new version."""
    if config_entry.version < 8:
        _LOGGER.debug(
            "Migrating config entry %s from version %s to 8",
            config_entry.entry_id,
            config_entry.version,
        )
        new_data = {**config_entry.data}
        new_data.setdefault(CONF_ENABLE_WEATHER_FORECAST, False)
        new_data.setdefault(CONF_LOCATION_NAME, config_entry.title)
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=8
        )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    platforms = ["sensor"]
    # Check what was actually loaded (not current config, which may already
    # be updated by the options flow before the reload triggers).
    if f"{entry.entry_id}_forecast" in hass.data.get(DOMAIN, {}):
        platforms.append("weather")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_forecast", None)

        # Unregister frontend if no other entries remain
        remaining = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        if not remaining:
            await _async_unregister_frontend(hass)

    return unload_ok
