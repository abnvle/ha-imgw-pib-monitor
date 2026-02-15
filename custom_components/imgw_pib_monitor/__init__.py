"""IMGW-PIB Monitor — comprehensive integration for IMGW-PIB data."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ImgwApiClient
from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ImgwDataUpdateCoordinator, ImgwGlobalDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IMGW-PIB Monitor from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize global coordinator if not already present
    if "global_coordinator" not in hass.data[DOMAIN]:
        session = async_get_clientsession(hass)
        api = ImgwApiClient(session)
        hass.data[DOMAIN]["global_coordinator"] = ImgwGlobalDataCoordinator(hass, api)

    global_coordinator = hass.data[DOMAIN]["global_coordinator"]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator = ImgwDataUpdateCoordinator(
        hass=hass,
        global_coordinator=global_coordinator,
        entry=entry,
        update_interval=update_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
