"""API client for IMGW-PIB public data."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_ENDPOINT_METEO,
    API_ENDPOINT_SYNOP,
    FORECAST_API_URL,
    USER_AGENT,
    API_ENDPOINT_WARNINGS_HYDRO,
    API_ENDPOINT_WARNINGS_METEO,
    API_HYDRO_BACK_DISCHARGE_URL,
    API_HYDRO_BACK_LIST_URL,
    API_HYDRO_BACK_STATION_URL,
    API_HYDRO_BACK_WATER_TEMP_URL,
    API_METEO_IMGW_OSMET_URL,
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
        self._hydro_session: aiohttp.ClientSession | None = None

    async def _fetch(self, url: str) -> list[dict[str, Any]] | dict[str, Any]:
        """Fetch data from the API."""
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    raise ImgwApiError(f"API returned status {resp.status}")
                return await resp.json()
        except ImgwApiError:
            raise
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

    async def _fetch_hydro_back(self, url: str, endpoint_name: str) -> list[dict[str, Any]] | dict[str, Any]:
        """Fetch data from hydro-back API using dedicated session."""
        try:
            session = self._get_hydro_session()
            async with session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning(
                        "Hydro-back %s returned status %s",
                        endpoint_name,
                        resp.status,
                    )
                    return []
                return await resp.json()
        except Exception as err:
            _LOGGER.warning(
                "Hydro-back %s unavailable: %s",
                endpoint_name,
                err,
            )
            return []

    async def get_all_synop_data(self) -> list[dict[str, Any]]:
        """Get synoptic data for all stations."""
        return await self._fetch_list(API_ENDPOINT_SYNOP, "synop")

    async def get_all_hydro_data(self) -> list[dict[str, Any]]:
        """Get hydrological data for all stations from hydro-back API."""
        data = await self._fetch_hydro_back(API_HYDRO_BACK_LIST_URL, "hydro_list")
        if not isinstance(data, list):
            return []
        return data

    async def get_all_meteo_data(self) -> list[dict[str, Any]]:
        """Get meteorological data for all stations."""
        return await self._fetch_list(API_ENDPOINT_METEO, "meteo")

    async def get_warnings_meteo(self) -> list[dict[str, Any]]:
        """Get all meteorological warnings."""
        return await self._fetch_list(API_ENDPOINT_WARNINGS_METEO, "warnings_meteo")

    async def get_warnings_hydro(self) -> list[dict[str, Any]]:
        """Get all hydrological warnings."""
        return await self._fetch_list(API_ENDPOINT_WARNINGS_HYDRO, "warnings_hydro")

    async def get_enhanced_warnings_meteo(self) -> dict[str, Any]:
        """Get enhanced meteorological warnings from meteo.imgw.pl."""
        data = await self._fetch(API_METEO_IMGW_OSMET_URL)
        if not isinstance(data, dict):
            _LOGGER.warning(
                "Enhanced warnings returned unexpected type %s, expected dict",
                type(data).__name__,
            )
            return {}
        return data

    async def get_synop_stations(self) -> dict[str, str]:
        """Return {id: name} for all synoptic stations."""
        data = await self.get_all_synop_data()
        return {
            item["id_stacji"]: item["stacja"]
            for item in data
            if item.get("id_stacji") and item.get("stacja")
        }

    async def get_synop_station_coords(self) -> dict[str, tuple[float, float]]:
        """Return {station_id: (lat, lon)} for synoptic stations from IMGW API Proxy.

        Falls back to empty dict on failure — callers should use SYNOP_STATIONS as fallback.
        """
        url = f"{FORECAST_API_URL}/stations/synop"
        try:
            async with self._session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Station coords API returned %s", resp.status)
                    return {}
                data = await resp.json()
                return {
                    sid: (s["lat"], s["lon"])
                    for sid, s in data.items()
                    if s.get("lat") and s.get("lon")
                }
        except Exception as err:
            _LOGGER.debug("Station coords unavailable: %s", err)
            return {}

    async def get_hydro_stations(self) -> dict[str, str]:
        """Return {code: 'name (river)'} for all hydro stations."""
        data = await self.get_all_hydro_data()
        stations: dict[str, str] = {}
        for item in data:
            sid = item.get("code")
            name = item.get("name")
            river_raw = item.get("river", "")
            # River field contains code in parentheses, e.g. "Dunajec (214)" — strip it
            river = river_raw.split("(")[0].strip() if river_raw else ""
            if sid and name:
                label = f"{name} ({river})" if river else name
                stations[sid] = label
        return stations

    def _get_hydro_session(self) -> aiohttp.ClientSession:
        """Return a reusable session for hydro-back API.

        hydro-back.imgw.pl rejects requests without a proper User-Agent
        header (403), and the shared HA session may override per-request
        headers via multidict merging. A dedicated session avoids this.
        """
        if self._hydro_session is None or self._hydro_session.closed:
            self._hydro_session = aiohttp.ClientSession(
                headers={"User-Agent": USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._hydro_session

    async def close(self) -> None:
        """Close any internally managed sessions."""
        if self._hydro_session and not self._hydro_session.closed:
            await self._hydro_session.close()
            self._hydro_session = None

    async def get_hydro_station_details(self, station_id: str) -> dict[str, Any]:
        """Get extended hydro data (alarm levels, trend) from hydro-back API."""
        url = f"{API_HYDRO_BACK_STATION_URL}?id={station_id}"
        data = await self._fetch_hydro_back(url, f"station_details/{station_id}")
        return data if isinstance(data, dict) else {}

    async def get_hydro_discharge(self, station_id: str) -> dict[str, Any] | None:
        """Get current discharge (flow) for a hydro station.

        Returns the latest operational measurement as {date, value} or None.
        """
        url = f"{API_HYDRO_BACK_DISCHARGE_URL}?id={station_id}&hoursInterval=6"
        data = await self._fetch_hydro_back(url, f"discharge/{station_id}")
        if not isinstance(data, dict):
            return None
        operational = data.get("operational")
        if operational and isinstance(operational, list):
            return operational[-1]  # Latest measurement
        return None

    async def get_hydro_water_temperature(self, station_id: str) -> dict[str, Any] | None:
        """Get current water temperature for a hydro station.

        Returns the latest operational measurement as {date, value} or None.
        """
        url = f"{API_HYDRO_BACK_WATER_TEMP_URL}?id={station_id}&hoursInterval=6"
        data = await self._fetch_hydro_back(url, f"water_temp/{station_id}")
        if not isinstance(data, dict):
            return None
        operational = data.get("operational")
        if operational and isinstance(operational, list):
            return operational[-1]  # Latest measurement
        return None

    async def get_meteo_stations(self) -> dict[str, str]:
        """Return {code: name} for all meteo stations."""
        data = await self.get_all_meteo_data()
        return {
            item["kod_stacji"]: item["nazwa_stacji"]
            for item in data
            if item.get("kod_stacji") and item.get("nazwa_stacji")
        }
