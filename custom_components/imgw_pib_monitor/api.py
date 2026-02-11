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
    DATA_TYPE_HYDRO,
    DATA_TYPE_METEO,
    DATA_TYPE_SYNOP,
    DATA_TYPE_WARNINGS_HYDRO,
    DATA_TYPE_WARNINGS_METEO,
)

_LOGGER = logging.getLogger(__name__)

ENDPOINTS = {
    DATA_TYPE_SYNOP: API_ENDPOINT_SYNOP,
    DATA_TYPE_HYDRO: API_ENDPOINT_HYDRO,
    DATA_TYPE_METEO: API_ENDPOINT_METEO,
    DATA_TYPE_WARNINGS_METEO: API_ENDPOINT_WARNINGS_METEO,
    DATA_TYPE_WARNINGS_HYDRO: API_ENDPOINT_WARNINGS_HYDRO,
}


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
        except ImgwApiError:
            raise
        except Exception as err:
            raise ImgwApiError(f"Unexpected error: {err}") from err

    # ── Station lists (for config flow) ─────────────────────────

    async def get_synop_stations(self) -> dict[str, str]:
        """Return {id: name} for all synoptic stations."""
        data = await self._fetch(API_ENDPOINT_SYNOP)
        return {
            item["id_stacji"]: item["stacja"]
            for item in data
            if item.get("id_stacji") and item.get("stacja")
        }

    async def get_hydro_stations(self) -> dict[str, str]:
        """Return {id: 'name (river)'} for all hydro stations."""
        data = await self._fetch(API_ENDPOINT_HYDRO)
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
        """Return {code: name} for all meteo stations.

        Duplicate names get station code appended for disambiguation.
        """
        data = await self._fetch(API_ENDPOINT_METEO)

        # First pass: collect all stations
        raw: list[tuple[str, str]] = []
        for item in data:
            code = item.get("kod_stacji")
            name = item.get("nazwa_stacji")
            if code and name:
                raw.append((code, name))

        # Find duplicate names
        name_counts: dict[str, int] = {}
        for _, name in raw:
            name_counts[name] = name_counts.get(name, 0) + 1

        # Build result with disambiguation for duplicates
        stations: dict[str, str] = {}
        for code, name in raw:
            if name_counts[name] > 1:
                stations[code] = f"{name} ({code})"
            else:
                stations[code] = name
        return stations

    # ── Data fetchers ───────────────────────────────────────────

    async def get_synop_data(self, station_id: str) -> dict[str, Any] | None:
        """Get synoptic data for a specific station."""
        url = f"{API_ENDPOINT_SYNOP}/id/{station_id}"
        data = await self._fetch(url)
        if isinstance(data, dict):
            return data if data else None
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return None

    async def get_hydro_data(self, station_id: str) -> dict[str, Any] | None:
        """Get hydrological data for a specific station."""
        data = await self._fetch(API_ENDPOINT_HYDRO)
        for item in data:
            if item.get("id_stacji") == station_id:
                return item
        return None

    async def get_meteo_data(self, station_code: str) -> dict[str, Any] | None:
        """Get meteorological data for a specific station."""
        data = await self._fetch(API_ENDPOINT_METEO)
        for item in data:
            if item.get("kod_stacji") == station_code:
                return item
        return None

    async def get_warnings_meteo(self, voivodeship_code: str | None = None) -> list[dict[str, Any]]:
        """Get meteorological warnings, optionally filtered by voivodeship TERYT."""
        data = await self._fetch(API_ENDPOINT_WARNINGS_METEO)
        if not voivodeship_code:
            return data

        filtered = []
        for warning in data:
            teryt_list = warning.get("teryt", [])
            if any(t.startswith(voivodeship_code) for t in teryt_list):
                filtered.append(warning)
        return filtered

    async def get_warnings_hydro(self, voivodeship_name: str | None = None) -> list[dict[str, Any]]:
        """Get hydrological warnings, optionally filtered by voivodeship name."""
        data = await self._fetch(API_ENDPOINT_WARNINGS_HYDRO)
        if not voivodeship_name:
            return data

        filtered = []
        for warning in data:
            areas = warning.get("obszary", [])
            if any(
                voivodeship_name.lower() in area.get("wojewodztwo", "").lower()
                for area in areas
            ):
                filtered.append(warning)
        return filtered