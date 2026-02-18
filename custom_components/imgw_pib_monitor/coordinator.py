"""DataUpdateCoordinator for IMGW-PIB Monitor."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

import aiohttp

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ImgwApiClient
from .const import (
    CONF_AUTO_DETECT,
    CONF_ENABLE_WARNINGS_HYDRO,
    CONF_ENABLE_WARNINGS_METEO,
    CONF_POWIAT,
    CONF_POWIAT_NAME,
    CONF_SELECTED_HYDRO,
    CONF_SELECTED_METEO,
    CONF_SELECTED_SYNOP,
    CONF_USE_POWIAT_FOR_WARNINGS,
    CONF_VOIVODESHIP,
    DATA_TYPE_HYDRO,
    DATA_TYPE_METEO,
    DATA_TYPE_SYNOP,
    DATA_TYPE_WARNINGS_HYDRO,
    DATA_TYPE_WARNINGS_METEO,
    DEFAULT_MAX_DISTANCE,
    DOMAIN,
    FORECAST_API_URL,
    FORECAST_UPDATE_INTERVAL,
    SYNOP_STATIONS,
    VOIVODESHIP_CAPITALS,
    VOIVODESHIPS,
)
from .utils import haversine

_LOGGER = logging.getLogger(__name__)

class ImgwGlobalDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Global coordinator to fetch all IMGW-PIB data with rate limiting."""

    def __init__(self, hass: HomeAssistant, api: ImgwApiClient, update_interval_minutes: int | None = None) -> None:
        """Initialize the global coordinator."""
        interval = timedelta(minutes=update_interval_minutes) if update_interval_minutes else timedelta(minutes=15)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_global",
            update_interval=interval,
        )
        self.api = api
        self._semaphore = asyncio.Semaphore(2)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all data from IMGW API without blocking the loop."""
        _LOGGER.debug("Fetching all IMGW-PIB data with rate limiting")

        async def _fetch_with_limit(coro):
            async with self._semaphore:
                try:
                    res = await coro
                    await asyncio.sleep(0.2)
                    return res
                except Exception as err:
                    _LOGGER.warning("Error fetching IMGW endpoint: %s", err)
                    return []

        results = await asyncio.gather(
            _fetch_with_limit(self.api.get_all_synop_data()),
            _fetch_with_limit(self.api.get_all_hydro_data()),
            _fetch_with_limit(self.api.get_all_meteo_data()),
            _fetch_with_limit(self.api.get_warnings_meteo()),
            _fetch_with_limit(self.api.get_warnings_hydro()),
        )

        data: dict[str, Any] = {
            DATA_TYPE_SYNOP: results[0],
            DATA_TYPE_HYDRO: results[1],
            DATA_TYPE_METEO: results[2],
            DATA_TYPE_WARNINGS_METEO: results[3],
            DATA_TYPE_WARNINGS_HYDRO: results[4],
        }

        if all(not r for r in results):
            raise UpdateFailed("Failed to fetch any data from IMGW API")

        return data


class ImgwDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for a specific config entry serving sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        global_coordinator: ImgwGlobalDataCoordinator,
        entry: ConfigEntry,
        update_interval: int,
    ) -> None:
        """Initialize the entry coordinator."""
        self.global_coordinator = global_coordinator
        self.config_entry = entry
        self.config_data = dict(entry.data)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.title}",
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Prepare specific slice of data for this entry."""
        # Always refresh global data from IMGW API.
        # The global coordinator has no entity listeners of its own, so its
        # automatic scheduling never fires.  We must trigger it explicitly
        # each time the entry coordinator's timer fires.
        await self.global_coordinator.async_refresh()

        global_data = self.global_coordinator.data
        if not global_data:
            raise UpdateFailed("Global IMGW data is unavailable")

        ha_lat = self.hass.config.latitude
        ha_lon = self.hass.config.longitude

        if self.config_data.get(CONF_AUTO_DETECT):
            self._update_auto_config(global_data, ha_lat, ha_lon)

        result: dict[str, Any] = {
            DATA_TYPE_SYNOP: {},
            DATA_TYPE_HYDRO: {},
            DATA_TYPE_METEO: {},
            DATA_TYPE_WARNINGS_METEO: {},
            DATA_TYPE_WARNINGS_HYDRO: {},
            "auto": {},
        }

        # 1. Synop
        for sid in self.config_data.get(CONF_SELECTED_SYNOP, []):
            for item in global_data.get(DATA_TYPE_SYNOP, []):
                if str(item.get("id_stacji")) == str(sid):
                    parsed = self._parse_synop(item)
                    # Coordinates for distance calculation
                    s_coords = SYNOP_STATIONS.get(str(sid))
                    s_lat = parsed.get("latitude") or (s_coords[0] if s_coords else None)
                    s_lon = parsed.get("longitude") or (s_coords[1] if s_coords else None)
                    if ha_lat and ha_lon and s_lat and s_lon:
                        parsed["distance"] = round(haversine(ha_lat, ha_lon, s_lat, s_lon), 1)
                        parsed["latitude"] = s_lat
                        parsed["longitude"] = s_lon
                    result[DATA_TYPE_SYNOP][sid] = parsed
                    if self.config_data.get(CONF_AUTO_DETECT):
                        result["auto"][DATA_TYPE_SYNOP] = parsed
                    break

        # 2. Hydro
        for sid in self.config_data.get(CONF_SELECTED_HYDRO, []):
            for item in global_data.get(DATA_TYPE_HYDRO, []):
                if str(item.get("id_stacji")) == str(sid):
                    parsed = self._parse_hydro(item)
                    if ha_lat and ha_lon and parsed.get("latitude") and parsed.get("longitude"):
                        parsed["distance"] = round(haversine(ha_lat, ha_lon, parsed["latitude"], parsed["longitude"]), 1)
                    result[DATA_TYPE_HYDRO][sid] = parsed
                    if self.config_data.get(CONF_AUTO_DETECT):
                        result["auto"][DATA_TYPE_HYDRO] = parsed
                    break

        # 3. Meteo
        for sid in self.config_data.get(CONF_SELECTED_METEO, []):
            for item in global_data.get(DATA_TYPE_METEO, []):
                if str(item.get("kod_stacji")) == str(sid):
                    parsed = self._parse_meteo(item)
                    if ha_lat and ha_lon and parsed.get("latitude") and parsed.get("longitude"):
                        parsed["distance"] = round(haversine(ha_lat, ha_lon, parsed["latitude"], parsed["longitude"]), 1)
                    result[DATA_TYPE_METEO][sid] = parsed
                    if self.config_data.get(CONF_AUTO_DETECT):
                        result["auto"][DATA_TYPE_METEO] = parsed
                    break

        # 4. Warnings Meteo
        if self.config_data.get(CONF_ENABLE_WARNINGS_METEO):
            voivodeship = self.config_data.get(CONF_VOIVODESHIP)
            powiat = self.config_data.get(CONF_POWIAT)
            teryt_filter = powiat if (powiat and powiat != "all") else voivodeship
            warnings = global_data.get(DATA_TYPE_WARNINGS_METEO, [])
            filtered = [
                w for w in warnings 
                if any(t.startswith(teryt_filter) for t in w.get("teryt", []))
            ] if teryt_filter else warnings
            result[DATA_TYPE_WARNINGS_METEO] = self._parse_warnings_meteo(filtered)

        # 5. Warnings Hydro
        if self.config_data.get(CONF_ENABLE_WARNINGS_HYDRO):
            voivodeship = self.config_data.get(CONF_VOIVODESHIP)
            powiat = self.config_data.get(CONF_POWIAT)
            use_powiat = self.config_data.get(CONF_USE_POWIAT_FOR_WARNINGS, False)

            warnings = global_data.get(DATA_TYPE_WARNINGS_HYDRO, [])

            # If powiat filtering is enabled and powiat is set
            if use_powiat and powiat and powiat != "all":
                powiat_name = self.config_data.get(CONF_POWIAT_NAME, "")
                if powiat_name:
                    filtered = [
                        w for w in warnings
                        if any(
                            powiat_name.lower() in area.get("opis", "").lower()
                            for area in w.get("obszary", [])
                        )
                    ]
                else:
                    filtered = warnings
            else:
                # Filter by voivodeship
                voiv_name = VOIVODESHIPS.get(voivodeship, "")
                filtered = [
                    w for w in warnings
                    if any(voiv_name.lower() in area.get("wojewodztwo", "").lower() for area in w.get("obszary", []))
                ] if voiv_name else warnings

            result[DATA_TYPE_WARNINGS_HYDRO] = self._parse_warnings_hydro(filtered)

        return result

    def _update_auto_config(self, global_data: dict[str, Any], lat: float, lon: float) -> None:
        """Update selected stations dynamically if HA moved."""
        if lat is None or lon is None:
            return

        def find_nearest_synop(stations):
            # Use hardcoded coordinates from SYNOP_STATIONS to find the nearest station
            # (API does not provide coordinates for SYNOP stations)
            nearest, d_min = None, DEFAULT_MAX_DISTANCE
            for s in stations:
                sid = str(s.get("id_stacji"))
                coords = SYNOP_STATIONS.get(sid)
                if not coords:
                    continue
                d = haversine(lat, lon, coords[0], coords[1])
                if d < d_min:
                    d_min, nearest = d, sid
            if nearest:
                _LOGGER.debug(
                    "Auto-selected SYNOP station ID %s at %.2f km",
                    nearest, d_min
                )
            return nearest

        def find_nearest(stations, lat_key, lon_key, id_key, station_type=""):
            nearest, d_min = None, DEFAULT_MAX_DISTANCE
            nearest_station = None
            for s in stations:
                try:
                    s_lat = float(s.get(lat_key) or s.get("szerokosc") or 0)
                    s_lon = float(s.get(lon_key) or s.get("dlugosc") or 0)
                    if not s_lat or not s_lon:
                        continue
                    d = haversine(lat, lon, s_lat, s_lon)
                    if d < d_min:
                        d_min, nearest, nearest_station = d, s.get(id_key), s
                except (ValueError, TypeError):
                    continue
            if nearest and nearest_station:
                station_name = nearest_station.get("stacja") or nearest_station.get("nazwa_stacji") or "Unknown"
                river = nearest_station.get("rzeka", "")
                river_info = f" ({river})" if river else ""
                _LOGGER.debug(
                    "Auto-selected %s station '%s'%s (ID: %s) at %.2f km",
                    station_type, station_name, river_info, nearest, d_min
                )
            return nearest

        ns = find_nearest_synop(global_data.get(DATA_TYPE_SYNOP, []))
        nh = find_nearest(global_data.get(DATA_TYPE_HYDRO, []), "lat", "lon", "id_stacji", "HYDRO")
        nm = find_nearest(global_data.get(DATA_TYPE_METEO, []), "lat", "lon", "kod_stacji", "METEO")

        # Only update station types that were originally selected by the user
        original_data = self.config_entry.data
        if ns and CONF_SELECTED_SYNOP in original_data:
            self.config_data[CONF_SELECTED_SYNOP] = [ns]
        if nh and CONF_SELECTED_HYDRO in original_data:
            self.config_data[CONF_SELECTED_HYDRO] = [nh]
        if nm and CONF_SELECTED_METEO in original_data:
            self.config_data[CONF_SELECTED_METEO] = [nm]

        # Region inference
        min_dist_v = float("inf")
        best_voiv = None
        for code, coords in VOIVODESHIP_CAPITALS.items():
            dist = haversine(lat, lon, coords[0], coords[1])
            if dist < min_dist_v:
                min_dist_v, best_voiv = dist, code
        if best_voiv:
            self.config_data[CONF_VOIVODESHIP] = best_voiv

    def _parse_synop(self, data: dict[str, Any]) -> dict[str, Any]:
        """Safely parse synoptic data."""
        return {
            "station_name": data.get("stacja"),
            "station_id": data.get("id_stacji"),
            "measurement_date": data.get("data_pomiaru"),
            "measurement_hour": data.get("godzina_pomiaru"),
            "temperature": self._safe_float(data.get("temperatura")),
            "wind_speed": self._safe_float(data.get("predkosc_wiatru")),
            "wind_direction": self._safe_int(data.get("kierunek_wiatru")),
            "humidity": self._safe_float(data.get("wilgotnosc_wzgledna")),
            "precipitation": self._safe_float(data.get("suma_opadu")),
            "pressure": self._safe_float(data.get("cisnienie")),
            "latitude": self._safe_float(data.get("lat") or data.get("szerokosc")),
            "longitude": self._safe_float(data.get("lon") or data.get("dlugosc")),
        }

    def _parse_hydro(self, data: dict[str, Any]) -> dict[str, Any]:
        """Safely parse hydrological data."""
        return {
            "station_name": data.get("stacja"),
            "station_id": data.get("id_stacji"),
            "river": data.get("rzeka"),
            "voivodeship": data.get("wojewodztwo"),
            "longitude": self._safe_float(data.get("lon")),
            "latitude": self._safe_float(data.get("lat")),
            "water_level": self._safe_int(data.get("stan_wody")),
            "water_level_date": data.get("stan_wody_data_pomiaru"),
            "water_temperature": self._safe_float(data.get("temperatura_wody")),
            "water_temperature_date": data.get("temperatura_wody_data_pomiaru"),
            "flow": self._safe_float(data.get("przelyw")),
            "flow_date": data.get("przeplyw_data"),
            "ice_phenomenon": self._safe_int(data.get("zjawisko_lodowe")),
            "ice_phenomenon_date": data.get("zjawisko_lodowe_data_pomiaru"),
        }

    def _parse_meteo(self, data: dict[str, Any]) -> dict[str, Any]:
        """Safely parse meteorological data."""
        return {
            "station_name": data.get("nazwa_stacji"),
            "station_code": data.get("kod_stacji"),
            "longitude": self._safe_float(data.get("lon")),
            "latitude": self._safe_float(data.get("lat")),
            "ground_temperature": self._safe_float(data.get("temperatura_gruntu")),
            "air_temperature": self._safe_float(data.get("temperatura_powietrza")),
            "wind_direction": self._safe_int(data.get("wiatr_kierunek")),
            "wind_avg_speed": self._safe_float(data.get("wiatr_srednia_predkosc")),
            "wind_max_speed": self._safe_float(data.get("wiatr_predkosc_maksymalna")),
            "humidity": self._safe_float(data.get("wilgotnosc_wzgledna")),
            "wind_gust_10min": self._safe_float(data.get("wiatr_poryw_10min")),
            "precipitation_10min": self._safe_float(data.get("opad_10min")),
        }

    def _parse_warnings_meteo(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """Safely parse meteorological warnings."""
        if not data:
            return {"active_warnings_count": 0, "max_level": 0, "warnings": []}
        w_list = []
        max_lvl = 0
        for w in data:
            lvl = int(w.get("stopien", 0))
            max_lvl = max(max_lvl, lvl)
            w_list.append({
                "event": w.get("nazwa_zdarzenia"),
                "level": lvl,
                "probability": int(w.get("prawdopodobienstwo", 0)),
                "valid_from": w.get("obowiazuje_od"),
                "valid_to": w.get("obowiazuje_do"),
                "content": w.get("tresc"),
                "comment": w.get("komentarz"),
            })
        w_list.sort(key=lambda x: (-x["level"], x.get("valid_from", "")))
        return {
            "active_warnings_count": len(w_list),
            "max_level": max_lvl,
            "warnings": w_list,
            "latest_warning": w_list[0] if w_list else None,
        }

    def _parse_warnings_hydro(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """Safely parse hydrological warnings."""
        if not data:
            return {"active_warnings_count": 0, "max_level": 0, "warnings": []}
        w_list = []
        max_lvl = 0
        for w in data:
            level_raw = w.get("stopień", w.get("stopien", "0"))
            try:
                lvl = abs(int(level_raw))
            except (ValueError, TypeError):
                lvl = 0
            max_lvl = max(max_lvl, lvl)
            areas = [a.get("opis", "") for a in w.get("obszary", [])]
            w_list.append({
                "number": w.get("numer"),
                "event": w.get("zdarzenie"),
                "level": lvl,
                "probability": w.get("prawdopodobienstwo"),
                "valid_from": w.get("data_od"),
                "valid_to": w.get("data_do"),
                "description": w.get("przebieg"),
                "areas": areas,
            })
        w_list.sort(key=lambda x: (-x["level"], x.get("number", "")))
        latest = w_list[0] if w_list else None
        if latest:
            _LOGGER.debug(
                "Hydro warnings: count=%d, max_level=%d, latest_event='%s', latest_desc='%s'",
                len(w_list), max_lvl, latest.get("event"),
                latest.get("description", "")[:50] if latest.get("description") else ""
            )
        return {
            "active_warnings_count": len(w_list),
            "max_level": max_lvl,
            "warnings": w_list,
            "latest_warning": latest,
        }

    @staticmethod
    def _safe_float(v: Any) -> float | None:
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(v: Any) -> int | None:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class ImgwForecastCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch weather forecast data from IMGW API Proxy."""

    def __init__(self, hass: HomeAssistant, lat: float, lon: float, update_interval_minutes: int | None = None) -> None:
        """Initialize the forecast coordinator."""
        if update_interval_minutes is not None:
            interval = timedelta(minutes=update_interval_minutes)
        else:
            interval = timedelta(seconds=FORECAST_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_forecast",
            update_interval=interval,
        )
        self.lat = lat
        self.lon = lon

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch forecast data from IMGW API Proxy."""
        url = f"{FORECAST_API_URL}/forecast?lat={self.lat}&lon={self.lon}"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(
                        f"IMGW forecast API returned {resp.status}"
                    )
                data = await resp.json()
                if "data" in data and isinstance(data["data"], dict):
                    return data["data"]
                return data
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error communicating with IMGW forecast API: {err}"
            ) from err
