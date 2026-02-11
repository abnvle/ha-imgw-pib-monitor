"""DataUpdateCoordinator for IMGW-PIB Monitor."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ImgwApiClient, ImgwApiConnectionError, ImgwApiError
from .const import (
    CONF_DATA_TYPE,
    CONF_POWIAT,
    CONF_STATION_ID,
    CONF_VOIVODESHIP,
    DATA_TYPE_HYDRO,
    DATA_TYPE_METEO,
    DATA_TYPE_SYNOP,
    DATA_TYPE_WARNINGS_HYDRO,
    DATA_TYPE_WARNINGS_METEO,
    DOMAIN,
    VOIVODESHIPS,
)

_LOGGER = logging.getLogger(__name__)


class ImgwDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch IMGW-PIB data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ImgwApiClient,
        config: dict[str, Any],
        update_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.config = config
        self.data_type: str = config[CONF_DATA_TYPE]
        self.station_id: str | None = config.get(CONF_STATION_ID)
        self.voivodeship: str | None = config.get(CONF_VOIVODESHIP)
        self.powiat: str | None = config.get(CONF_POWIAT)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.data_type}_{self.station_id or self.voivodeship}",
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from IMGW API."""
        try:
            if self.data_type == DATA_TYPE_SYNOP:
                data = await self.api.get_synop_data(self.station_id)
                if data is None:
                    raise UpdateFailed(f"No synoptic data for station {self.station_id}")
                return self._parse_synop(data)

            elif self.data_type == DATA_TYPE_HYDRO:
                data = await self.api.get_hydro_data(self.station_id)
                if data is None:
                    raise UpdateFailed(f"No hydro data for station {self.station_id}")
                return self._parse_hydro(data)

            elif self.data_type == DATA_TYPE_METEO:
                data = await self.api.get_meteo_data(self.station_id)
                if data is None:
                    raise UpdateFailed(f"No meteo data for station {self.station_id}")
                return self._parse_meteo(data)

            elif self.data_type == DATA_TYPE_WARNINGS_METEO:
                # Use powiat code for filtering if specific powiat selected,
                # otherwise use voivodeship code (2-digit prefix)
                if self.powiat and self.powiat != "all":
                    teryt_filter = self.powiat
                else:
                    teryt_filter = self.voivodeship
                data = await self.api.get_warnings_meteo(teryt_filter)
                return self._parse_warnings_meteo(data)

            elif self.data_type == DATA_TYPE_WARNINGS_HYDRO:
                voiv_name = VOIVODESHIPS.get(self.voivodeship, "")
                data = await self.api.get_warnings_hydro(voiv_name)
                return self._parse_warnings_hydro(data)

            else:
                raise UpdateFailed(f"Unknown data type: {self.data_type}")

        except ImgwApiConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except ImgwApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

    @staticmethod
    def _safe_float(value: str | None) -> float | None:
        """Safely convert a string to float."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value: str | None) -> int | None:
        """Safely convert a string to int."""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _parse_synop(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse synoptic data."""
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
        }

    def _parse_hydro(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse hydrological data."""
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
            "overgrowth_phenomenon": self._safe_int(data.get("zjawisko_zarastania")),
        }

    def _parse_meteo(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse meteorological data."""
        return {
            "station_name": data.get("nazwa_stacji"),
            "station_code": data.get("kod_stacji"),
            "longitude": self._safe_float(data.get("lon")),
            "latitude": self._safe_float(data.get("lat")),
            "ground_temperature": self._safe_float(data.get("temperatura_gruntu")),
            "ground_temperature_date": data.get("temperatura_gruntu_data"),
            "air_temperature": self._safe_float(data.get("temperatura_powietrza")),
            "air_temperature_date": data.get("temperatura_powietrza_data"),
            "wind_direction": self._safe_int(data.get("wiatr_kierunek")),
            "wind_direction_date": data.get("wiatr_kierunek_data"),
            "wind_avg_speed": self._safe_float(data.get("wiatr_srednia_predkosc")),
            "wind_avg_speed_date": data.get("wiatr_srednia_predkosc_data"),
            "wind_max_speed": self._safe_float(data.get("wiatr_predkosc_maksymalna")),
            "wind_max_speed_date": data.get("wiatr_predkosc_maksymalna_data"),
            "humidity": self._safe_float(data.get("wilgotnosc_wzgledna")),
            "humidity_date": data.get("wilgotnosc_wzgledna_data"),
            "wind_gust_10min": self._safe_float(data.get("wiatr_poryw_10min")),
            "wind_gust_10min_date": data.get("wiatr_poryw_10min_data"),
            "precipitation_10min": self._safe_float(data.get("opad_10min")),
            "precipitation_10min_date": data.get("opad_10min_data"),
        }

    @staticmethod
    def _parse_warnings_meteo(data: list[dict[str, Any]]) -> dict[str, Any]:
        """Parse meteorological warnings."""
        if not data:
            return {
                "active_warnings_count": 0,
                "max_level": 0,
                "warnings": [],
            }

        warnings_list = []
        max_level = 0
        for w in data:
            level = int(w.get("stopien", 0))
            max_level = max(max_level, level)
            warnings_list.append({
                "id": w.get("id"),
                "event": w.get("nazwa_zdarzenia"),
                "level": level,
                "probability": int(w.get("prawdopodobienstwo", 0)),
                "valid_from": w.get("obowiazuje_od"),
                "valid_to": w.get("obowiazuje_do"),
                "published": w.get("opublikowano"),
                "content": w.get("tresc"),
                "comment": w.get("komentarz"),
                "office": w.get("biuro"),
            })

        # Sort by level descending, then by valid_from
        warnings_list.sort(key=lambda x: (-x["level"], x.get("valid_from", "")))

        return {
            "active_warnings_count": len(warnings_list),
            "max_level": max_level,
            "warnings": warnings_list,
            "latest_warning": warnings_list[0] if warnings_list else None,
        }

    @staticmethod
    def _parse_warnings_hydro(data: list[dict[str, Any]]) -> dict[str, Any]:
        """Parse hydrological warnings."""
        if not data:
            return {
                "active_warnings_count": 0,
                "max_level": 0,
                "warnings": [],
            }

        warnings_list = []
        max_level = 0
        for w in data:
            level_raw = w.get("stopień", w.get("stopien", "0"))
            try:
                level = abs(int(level_raw))
            except (ValueError, TypeError):
                level = 0
            max_level = max(max_level, level)

            areas = w.get("obszary", [])
            area_descriptions = [a.get("opis", "") for a in areas]

            warnings_list.append({
                "number": w.get("numer"),
                "event": w.get("zdarzenie"),
                "level": level,
                "probability": int(w.get("prawdopodobienstwo", 0)),
                "valid_from": w.get("data_od"),
                "valid_to": w.get("data_do"),
                "published": w.get("opublikowano"),
                "description": w.get("przebieg"),
                "comment": w.get("komentarz"),
                "office": w.get("biuro"),
                "areas": area_descriptions,
            })

        warnings_list.sort(key=lambda x: (-x["level"], x.get("published", "")))

        return {
            "active_warnings_count": len(warnings_list),
            "max_level": max_level,
            "warnings": warnings_list,
            "latest_warning": warnings_list[0] if warnings_list else None,
        }