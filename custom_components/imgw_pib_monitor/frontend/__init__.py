"""JavaScript module registration for IMGW Weather card."""

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import FRONTEND_URL_BASE

_LOGGER = logging.getLogger(__name__)

JSMODULES = [
    {
        "name": "IMGW Weather Card",
        "filename": "imgw-weather-card.js",
        "version": "1.0.0",
    },
]


class JSModuleRegistration:
    """Registers JavaScript modules in Home Assistant."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the registrar."""
        self.hass = hass

    async def async_register(self) -> None:
        """Register frontend resources."""
        await self._async_register_path()
        await self._async_wait_for_lovelace_resources()

    async def async_unregister(self) -> None:
        """Remove frontend Lovelace resources."""
        resources = None
        lovelace_data = self.hass.data.get("lovelace")
        if lovelace_data is None:
            return
        if hasattr(lovelace_data, "resources"):
            resources = lovelace_data.resources
        elif isinstance(lovelace_data, dict) and "resources" in lovelace_data:
            resources = lovelace_data["resources"]
        if resources is None or not resources.loaded:
            return
        existing = [
            r for r in resources.async_items()
            if r["url"].startswith(FRONTEND_URL_BASE)
        ]
        for resource in existing:
            await resources.async_delete_item(resource["id"])
            _LOGGER.info("Removed frontend resource: %s", resource["url"])

    async def _async_register_path(self) -> None:
        """Register the static HTTP path."""
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_URL_BASE, str(Path(__file__).parent), False)]
            )
            _LOGGER.debug("Path registered: %s -> %s", FRONTEND_URL_BASE, Path(__file__).parent)
        except RuntimeError:
            _LOGGER.debug("Path already registered: %s", FRONTEND_URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Wait for Lovelace resources to load, then register modules."""
        resources = None
        lovelace_data = self.hass.data.get("lovelace")

        if lovelace_data is None:
            _LOGGER.debug("Lovelace data not available, skipping resource registration")
            return

        if hasattr(lovelace_data, "resources"):
            resources = lovelace_data.resources
        elif isinstance(lovelace_data, dict) and "resources" in lovelace_data:
            resources = lovelace_data["resources"]

        if resources is None:
            _LOGGER.debug("Lovelace resources not available, skipping auto-registration")
            return

        async def _check_loaded(_now: Any) -> None:
            if resources.loaded:
                await self._async_register_modules(resources)
            else:
                _LOGGER.debug("Lovelace resources not loaded, retrying in 5s")
                async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(0)

    async def _async_register_modules(self, resources) -> None:
        """Register or update JavaScript modules."""
        _LOGGER.debug("Installing IMGW Weather JavaScript modules")

        existing_resources = [
            r for r in resources.async_items()
            if r["url"].startswith(FRONTEND_URL_BASE)
        ]

        for module in JSMODULES:
            url = f"{FRONTEND_URL_BASE}/{module['filename']}"
            registered = False

            for resource in existing_resources:
                if self._get_path(resource["url"]) == url:
                    registered = True
                    if self._get_version(resource["url"]) != module["version"]:
                        _LOGGER.info(
                            "Updating %s to version %s",
                            module["name"], module["version"],
                        )
                        await resources.async_update_item(
                            resource["id"],
                            {
                                "res_type": "module",
                                "url": f"{url}?v={module['version']}",
                            },
                        )
                    break

            if not registered:
                _LOGGER.info(
                    "Registering %s version %s",
                    module["name"], module["version"],
                )
                await resources.async_create_item(
                    {
                        "res_type": "module",
                        "url": f"{url}?v={module['version']}",
                    }
                )

    def _get_path(self, url: str) -> str:
        """Extract path without parameters."""
        return url.split("?")[0]

    def _get_version(self, url: str) -> str:
        """Extract version from URL."""
        parts = url.split("?")
        if len(parts) > 1 and parts[1].startswith("v="):
            return parts[1].replace("v=", "")
        return "0"
