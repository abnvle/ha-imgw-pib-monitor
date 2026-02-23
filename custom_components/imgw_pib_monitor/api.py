"""API client for IMGW-PIB public data."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_ENDPOINT_HYDRO,
    API_ENDPOINT_METEO,
    API_ENDPOINT_SYNOP,
    API_ENDPOINT_WARNINGS_HYDRO,
    API_ENDPOINT_WARNINGS_METEO,
)

_LOGGER = logging.getLogger(__name__)

class ImgwApiError(Exception):
    """Base exception for IMGW API errors."""

class ImgwApiConnectionError(ImgwApiError):
    """Exception for connection errors."""

class ImgwApiClient:
    """Client for the IMGW-PIB public API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._session = session

    async def _fetch(self, url: str) -> list[dict[str, Any]] | dict[str, Any]:
        """Fetch data from the API."""
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    raise ImgwApiError(f"API returned status {resp.status}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise ImgwApiConnectionError(f"Connection error: {err}") from err
        except Exception as err:
            raise ImgwApiError(f"Unexpected error: {err}") from err

    async def _fetch_list(self, url: str, endpoint_name: str) -> list[dict[str, Any]]:
        """Fetch data and validate it is a list."""
        data = await self._fetch(url)
        if not isinstance(data, list):
            _LOGGER.warning(
                "IMGW %s returned unexpected type %s, expected list",
                endpoint_name,
                type(data).__name__,
            )
            return []
        return data

    async def get_all_synop_data(self) -> list[dict[str, Any]]:
        """Get synoptic data for all stations."""
        return await self._fetch_list(API_ENDPOINT_SYNOP, "synop")

    async def get_all_hydro_data(self) -> list[dict[str, Any]]:
        """Get hydrological data for all stations."""
        return await self._fetch_list(API_ENDPOINT_HYDRO, "hydro")

    async def get_all_meteo_data(self) -> list[dict[str, Any]]:
        """Get meteorological data for all stations."""
        return await self._fetch_list(API_ENDPOINT_METEO, "meteo")

    async def get_warnings_meteo(self) -> list[dict[str, Any]]:
        """Get all meteorological warnings."""
        return await self._fetch_list(API_ENDPOINT_WARNINGS_METEO, "warnings_meteo")

    async def get_warnings_hydro(self) -> list[dict[str, Any]]:
        """Get all hydrological warnings."""
        return await self._fetch_list(API_ENDPOINT_WARNINGS_HYDRO, "warnings_hydro")

    async def get_synop_stations(self) -> dict[str, str]:
        """Return {id: name} for all synoptic stations."""
        data = await self.get_all_synop_data()
        return {
            item["id_stacji"]: item["stacja"]
            for item in data
            if item.get("id_stacji") and item.get("stacja")
        }

    async def get_hydro_stations(self) -> dict[str, str]:
        """Return {id: 'name (river)'} for all hydro stations."""
        data = await self.get_all_hydro_data()
        stations: dict[str, str] = {}
        for item in data:
            sid = item.get("id_stacji")
            name = item.get("stacja")
            river = item.get("rzeka", "")
            if sid and name:
                label = f"{name} ({river})" if river else name
                stations[sid] = label
        return stations

    async def get_meteo_stations(self) -> dict[str, str]:
        """Return {code: name} for all meteo stations."""
        data = await self.get_all_meteo_data()
        return {
            item["kod_stacji"]: item["nazwa_stacji"]
            for item in data
            if item.get("kod_stacji") and item.get("nazwa_stacji")
        }
