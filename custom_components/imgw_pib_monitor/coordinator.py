"""DataUpdateCoordinator for IMGW-PIB Monitor."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

import aiohttp

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ImgwApiClient, ImgwApiError
from .const import (
    CONF_AUTO_DETECT,
    CONF_ENABLE_ENHANCED_WARNINGS_METEO,
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
    DATA_TYPE_WARNINGS_METEO_ENHANCED,
    DEFAULT_MAX_DISTANCE,
    DOMAIN,
    FORECAST_API_URL,
    FORECAST_UPDATE_INTERVAL,
    HYDRO_TREND_MAP,
    RADAR_UPDATE_INTERVAL,
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
        self._fetch_lock = asyncio.Lock()
        self._last_fetch_time: float = 0
        self.synop_coords: dict[str, tuple[float, float]] = {}
        self._synop_coords_loaded = False

    async def get_synop_station_coords(self) -> dict[str, tuple[float, float]]:
        """Return synop station coordinates — fetched from API, fallback to hardcoded."""
        if not self._synop_coords_loaded:
            live = await self.api.get_synop_station_coords()
            if live:
                self.synop_coords = live
                _LOGGER.debug("Loaded %d synop coords from API", len(live))
            else:
                self.synop_coords = dict(SYNOP_STATIONS)
                _LOGGER.debug("Using %d hardcoded synop coords (API unavailable)", len(SYNOP_STATIONS))
            self._synop_coords_loaded = True
        return self.synop_coords

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all data from IMGW API without blocking the loop."""
        _LOGGER.debug("Fetching all IMGW-PIB data with rate limiting")

        # Load synop station coordinates once
        await self.get_synop_station_coords()

        async def _fetch_with_limit(coro, endpoint_name: str, default=None):
            if default is None:
                default = []
            async with self._semaphore:
                try:
                    res = await coro
                    await asyncio.sleep(0.2)
                    _LOGGER.debug(
                        "IMGW endpoint %s returned %d items",
                        endpoint_name,
                        len(res) if isinstance(res, (list, dict)) else 0,
                    )
                    return res
                except (ImgwApiError, asyncio.TimeoutError) as err:
                    _LOGGER.warning("Error fetching IMGW endpoint %s: %s", endpoint_name, err)
                    return default

        # Only fetch enhanced warnings if any entry has them enabled
        fetch_enhanced = any(
            e.data.get(CONF_ENABLE_ENHANCED_WARNINGS_METEO)
            for e in self.hass.config_entries.async_entries(DOMAIN)
        )

        coros = [
            _fetch_with_limit(self.api.get_all_synop_data(), "synop"),
            _fetch_with_limit(self.api.get_all_hydro_data(), "hydro"),
            _fetch_with_limit(self.api.get_all_meteo_data(), "meteo"),
            _fetch_with_limit(self.api.get_warnings_meteo(), "warnings_meteo"),
            _fetch_with_limit(self.api.get_warnings_hydro(), "warnings_hydro"),
        ]
        if fetch_enhanced:
            coros.append(
                _fetch_with_limit(
                    self.api.get_enhanced_warnings_meteo(),
                    "enhanced_warnings_meteo",
                    default={},
                )
            )

        results = await asyncio.gather(*coros)

        data: dict[str, Any] = {
            DATA_TYPE_SYNOP: results[0],
            DATA_TYPE_HYDRO: results[1],
            DATA_TYPE_METEO: results[2],
            DATA_TYPE_WARNINGS_METEO: results[3],
            DATA_TYPE_WARNINGS_HYDRO: results[4],
            DATA_TYPE_WARNINGS_METEO_ENHANCED: results[5] if fetch_enhanced else {},
        }

        if all(not r for r in results):
            raise UpdateFailed("Failed to fetch any data from IMGW API")

        self._last_fetch_time = time.monotonic()
        return data

    async def async_fetch_data(self) -> dict[str, Any]:
        """Fetch fresh data with deduplication for concurrent callers.

        Multiple entry coordinators may call this at roughly the same time.
        The lock ensures only one actual API call is made; subsequent callers
        within a short window reuse the same result.
        """
        async with self._fetch_lock:
            now = time.monotonic()
            # If data was fetched less than 30 seconds ago, reuse it
            if self.data and now - self._last_fetch_time < 30:
                _LOGGER.debug(
                    "Reusing global data fetched %.1fs ago",
                    now - self._last_fetch_time,
                )
                return self.data

            data = await self._async_update_data()
            self.data = data
            return data


_STATUS_CODE_MAP: dict[str, str] = {
    "lowOutdated": "low_outdated",
    "mediumOutdated": "medium_outdated",
    "highOutdated": "high_outdated",
    "no-char-states": "no_data",
    "no-water-state-data": "no_data",
}


def _normalize_status_code(code: str | None) -> str | None:
    """Map API statusCode to HA-compatible enum value (lowercase, no camelCase/hyphens)."""
    if code is None:
        return None
    return _STATUS_CODE_MAP.get(code, code)


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
        # Fetch fresh data directly from the global coordinator.
        # We bypass async_refresh() because it silently swallows errors
        # and keeps stale self.data, making sensors show old values
        # without any indication of a problem.
        try:
            global_data = await self.global_coordinator.async_fetch_data()
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Failed to fetch IMGW data: {err}") from err

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
            DATA_TYPE_WARNINGS_METEO_ENHANCED: {},
        }

        # 1. Synop
        for sid in self.config_data.get(CONF_SELECTED_SYNOP, []):
            for item in global_data.get(DATA_TYPE_SYNOP, []):
                if str(item.get("id_stacji")) == str(sid):
                    parsed = self._parse_synop(item)
                    # Coordinates for distance calculation
                    s_coords = self.global_coordinator.synop_coords.get(str(sid))
                    s_lat = parsed.get("latitude") or (s_coords[0] if s_coords else None)
                    s_lon = parsed.get("longitude") or (s_coords[1] if s_coords else None)
                    if ha_lat and ha_lon and s_lat and s_lon:
                        parsed["distance"] = round(haversine(ha_lat, ha_lon, s_lat, s_lon), 1)
                        parsed["latitude"] = s_lat
                        parsed["longitude"] = s_lon
                    result[DATA_TYPE_SYNOP][sid] = parsed
                    break

        # 2. Hydro (from hydro-back.imgw.pl/list/hydro)
        for sid in self.config_data.get(CONF_SELECTED_HYDRO, []):
            for item in global_data.get(DATA_TYPE_HYDRO, []):
                if str(item.get("code")) == str(sid):
                    parsed = self._parse_hydro(item)
                    if ha_lat and ha_lon and parsed.get("latitude") and parsed.get("longitude"):
                        parsed["distance"] = round(haversine(ha_lat, ha_lon, parsed["latitude"], parsed["longitude"]), 1)
                    result[DATA_TYPE_HYDRO][sid] = parsed
                    break

        # 2b. Enrich hydro with discharge and water temperature (parallel per station)
        if result[DATA_TYPE_HYDRO]:
            api = self.global_coordinator.api
            sids = list(result[DATA_TYPE_HYDRO].keys())

            async def _enrich_hydro(sid: str) -> tuple[str, dict | None, dict | None]:
                discharge = await api.get_hydro_discharge(str(sid))
                water_temp = await api.get_hydro_water_temperature(str(sid))
                return sid, discharge, water_temp

            enrichments = await asyncio.gather(
                *[_enrich_hydro(sid) for sid in sids],
                return_exceptions=True,
            )
            for item in enrichments:
                if isinstance(item, BaseException):
                    _LOGGER.debug("Hydro enrichment error: %s", item)
                    continue
                sid, discharge, water_temp = item
                parsed = result[DATA_TYPE_HYDRO][sid]
                if discharge:
                    parsed["flow"] = self._safe_float(discharge.get("value"))
                    parsed["flow_date"] = discharge.get("date")
                if water_temp:
                    parsed["water_temperature"] = self._safe_float(water_temp.get("value"))
                    parsed["water_temperature_date"] = water_temp.get("date")
                _LOGGER.debug(
                    "Hydro-back: station %s — state=%s, flow=%s, water_temp=%s",
                    sid, parsed.get("water_level_state"),
                    parsed.get("flow"), parsed.get("water_temperature"),
                )

        # 3. Meteo
        for sid in self.config_data.get(CONF_SELECTED_METEO, []):
            for item in global_data.get(DATA_TYPE_METEO, []):
                if str(item.get("kod_stacji")) == str(sid):
                    parsed = self._parse_meteo(item)
                    if ha_lat and ha_lon and parsed.get("latitude") and parsed.get("longitude"):
                        parsed["distance"] = round(haversine(ha_lat, ha_lon, parsed["latitude"], parsed["longitude"]), 1)
                    result[DATA_TYPE_METEO][sid] = parsed
                    break

        # 4. Warnings Meteo
        if self.config_data.get(CONF_ENABLE_WARNINGS_METEO):
            voivodeship = self.config_data.get(CONF_VOIVODESHIP)
            powiat = self.config_data.get(CONF_POWIAT)
            use_powiat = self.config_data.get(CONF_USE_POWIAT_FOR_WARNINGS, False)
            teryt_filter = powiat if (use_powiat and powiat and powiat != "all") else voivodeship
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

        # 6. Enhanced Warnings Meteo (meteo.imgw.pl)
        if self.config_data.get(CONF_ENABLE_ENHANCED_WARNINGS_METEO):
            voivodeship = self.config_data.get(CONF_VOIVODESHIP)
            powiat = self.config_data.get(CONF_POWIAT)
            use_powiat = self.config_data.get(CONF_USE_POWIAT_FOR_WARNINGS, False)
            teryt_filter = powiat if (use_powiat and powiat and powiat != "all") else voivodeship

            enhanced_raw = global_data.get(DATA_TYPE_WARNINGS_METEO_ENHANCED, {})
            result[DATA_TYPE_WARNINGS_METEO_ENHANCED] = self._parse_enhanced_warnings_meteo(
                enhanced_raw, teryt_filter
            )

        return result

    def _update_auto_config(self, global_data: dict[str, Any], lat: float, lon: float) -> None:
        """Update selected stations dynamically if HA moved."""
        if lat is None or lon is None:
            return

        def find_nearest_synop(stations):
            # Use coordinates from global coordinator (fetched from API, fallback to hardcoded)
            nearest, d_min = None, DEFAULT_MAX_DISTANCE
            synop_coords = self.global_coordinator.synop_coords
            for s in stations:
                sid = str(s.get("id_stacji"))
                coords = synop_coords.get(sid)
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
                station_name = nearest_station.get("stacja") or nearest_station.get("nazwa_stacji") or nearest_station.get("name") or "Unknown"
                river = nearest_station.get("rzeka") or nearest_station.get("river", "")
                river_info = f" ({river})" if river else ""
                _LOGGER.debug(
                    "Auto-selected %s station '%s'%s (ID: %s) at %.2f km",
                    station_type, station_name, river_info, nearest, d_min
                )
            return nearest

        ns = find_nearest_synop(global_data.get(DATA_TYPE_SYNOP, []))
        nh = find_nearest(global_data.get(DATA_TYPE_HYDRO, []), "latitude", "longitude", "code", "HYDRO")
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
        """Safely parse hydrological data from hydro-back API."""
        current_state = data.get("currentState") or {}
        river_raw = data.get("river", "")
        # Strip code suffix, e.g. "Dunajec (214)" → "Dunajec"
        river = river_raw.split("(")[0].strip() if river_raw else ""

        alarm_val = self._safe_float(data.get("alarmValue"))
        warning_val = self._safe_float(data.get("warningValue"))
        water_level = self._safe_float(current_state.get("value"))

        trend_code = data.get("trend")
        water_level_trend = HYDRO_TREND_MAP.get(trend_code) if trend_code is not None else None

        alarm_remaining = None
        warning_remaining = None
        if water_level is not None and alarm_val is not None:
            alarm_remaining = alarm_val - water_level
        if water_level is not None and warning_val is not None:
            warning_remaining = warning_val - water_level

        return {
            "station_name": data.get("name"),
            "station_id": data.get("code"),
            "river": river,
            "voivodeship": data.get("province"),
            "longitude": self._safe_float(data.get("longitude")),
            "latitude": self._safe_float(data.get("latitude")),
            "water_level": round(self._safe_float(current_state.get("value"))) if current_state.get("value") is not None else None,
            "water_level_date": current_state.get("date"),
            "water_level_state": _normalize_status_code(data.get("statusCode")),
            "water_level_trend": water_level_trend,
            "alarm_level": alarm_val,
            "warning_level": warning_val,
            "alarm_remaining": alarm_remaining,
            "warning_remaining": warning_remaining,
            # Populated later from per-station endpoints
            "water_temperature": None,
            "water_temperature_date": None,
            "flow": None,
            "flow_date": None,
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
            try:
                lvl = int(w.get("stopien", 0))
            except (ValueError, TypeError):
                lvl = 0
            max_lvl = max(max_lvl, lvl)
            try:
                prob = int(w.get("prawdopodobienstwo", 0))
            except (ValueError, TypeError):
                prob = 0
            w_list.append({
                "event": w.get("nazwa_zdarzenia"),
                "level": lvl,
                "probability": prob,
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
                "probability": int(w.get("prawdopodobienstwo", 0)),
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

    def _parse_enhanced_warnings_meteo(
        self, raw_data: dict[str, Any], teryt_filter: str | None
    ) -> dict[str, Any]:
        """Parse enhanced meteorological warnings from meteo.imgw.pl."""
        if not raw_data:
            return self._empty_enhanced_warnings()

        teryt_map = raw_data.get("teryt", {})
        all_warnings = raw_data.get("warnings", {})

        # Collect unique warning IDs for the region
        warning_ids: set[str] = set()
        if teryt_filter:
            for teryt_code, ids in teryt_map.items():
                if teryt_code.startswith(teryt_filter):
                    warning_ids.update(ids if isinstance(ids, list) else [])
        else:
            for ids in teryt_map.values():
                warning_ids.update(ids if isinstance(ids, list) else [])

        # Parse warnings
        now = datetime.now(timezone.utc)
        warnings: list[dict[str, Any]] = []
        for wid in warning_ids:
            w = all_warnings.get(wid)
            if not w:
                continue

            start_at = self._parse_iso_datetime(w.get("LxValidFrom"))
            end_at = self._parse_iso_datetime(w.get("LxValidTo"))
            is_active = bool(start_at and end_at and start_at <= now <= end_at)

            try:
                level = int(w.get("Level", 0))
            except (ValueError, TypeError):
                level = 0

            try:
                probability = int(w.get("Probability", 0))
            except (ValueError, TypeError):
                probability = 0

            warnings.append({
                "id": wid,
                "phenomenon_code": w.get("PhenomenonCode", ""),
                "phenomenon_name": w.get("PhenomenonName", ""),
                "phenomenon_name_en": w.get("EnPhenomenonName", ""),
                "level": level,
                "probability": probability,
                "valid_from": w.get("LxValidFrom"),
                "valid_to": w.get("LxValidTo"),
                "released_at": w.get("LxReleaseDateTime"),
                "content": w.get("Content", ""),
                "content_en": w.get("EnContent", ""),
                "sms": w.get("SMS", ""),
                "comments": w.get("Comments", ""),
                "is_active": is_active,
            })

        warnings.sort(key=lambda x: (-x["level"], x.get("valid_from", "")))

        # Compute aggregates
        present = warnings
        active = [w for w in warnings if w["is_active"]]

        by_phenomenon_present: dict[str, list[dict[str, Any]]] = {}
        by_phenomenon_active: dict[str, list[dict[str, Any]]] = {}
        for w in present:
            code = w["phenomenon_code"]
            by_phenomenon_present.setdefault(code, []).append(w)
        for w in active:
            code = w["phenomenon_code"]
            by_phenomenon_active.setdefault(code, []).append(w)

        return {
            "present_count": len(present),
            "active_count": len(active),
            "present_max_level": max((w["level"] for w in present), default=0),
            "active_max_level": max((w["level"] for w in active), default=0),
            "present_phenomena": list(by_phenomenon_present.keys()),
            "active_phenomena": list(by_phenomenon_active.keys()),
            "warnings": warnings,
            "by_phenomenon_present": by_phenomenon_present,
            "by_phenomenon_active": by_phenomenon_active,
        }

    @staticmethod
    def _empty_enhanced_warnings() -> dict[str, Any]:
        """Return empty enhanced warnings structure."""
        return {
            "present_count": 0,
            "active_count": 0,
            "present_max_level": 0,
            "active_max_level": 0,
            "present_phenomena": [],
            "active_phenomena": [],
            "warnings": [],
            "by_phenomenon_present": {},
            "by_phenomenon_active": {},
        }

    @staticmethod
    def _parse_iso_datetime(dt_str: str | None) -> datetime | None:
        """Parse ISO 8601 datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return None

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


class ImgwRadarCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch radar map image from IMGW API Proxy."""

    def __init__(self, hass: HomeAssistant, lat: float, lon: float, product: str = "cmax", update_interval_seconds: int | None = None) -> None:
        """Initialize the radar coordinator."""
        interval = update_interval_seconds or RADAR_UPDATE_INTERVAL
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_radar_{product}",
            update_interval=timedelta(seconds=interval),
        )
        self.lat = lat
        self.lon = lon
        self.product = product
        self.image_bytes: bytes | None = None
        self.image_timestamp: str | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch radar map from IMGW API Proxy."""
        url = f"{FORECAST_API_URL}/radar?lat={self.lat}&lon={self.lon}&product={self.product}"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(
                        f"IMGW radar API returned {resp.status}"
                    )
                self.image_bytes = await resp.read()
                self.image_timestamp = resp.headers.get("X-Radar-Timestamp")
                return {"timestamp": self.image_timestamp}
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error fetching IMGW radar map: {err}"
            ) from err
