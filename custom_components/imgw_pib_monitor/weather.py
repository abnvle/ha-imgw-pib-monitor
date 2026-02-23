"""Weather platform for IMGW-PIB Monitor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LOCATION_NAME, DOMAIN, MANUFACTURER, parse_imgw_icon


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IMGW Weather entity."""
    coordinator = hass.data[DOMAIN][f"{config_entry.entry_id}_forecast"]
    location_name = config_entry.data.get(CONF_LOCATION_NAME, config_entry.title)
    async_add_entities([ImgwWeatherEntity(coordinator, location_name, config_entry)])


class ImgwWeatherEntity(CoordinatorEntity, WeatherEntity):
    """IMGW Weather entity with daily and hourly forecast."""

    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(self, coordinator, location_name: str, config_entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._location_name = location_name
        self._attr_name = None
        self._attr_unique_id = f"{DOMAIN}_weather_{config_entry.entry_id}"
        self._entry_id = config_entry.entry_id

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, f"forecast_{self._entry_id}")},
            "name": f"IMGW Prognoza — {self._location_name}",
            "manufacturer": MANUFACTURER,
            "model": "Prognoza pogody | IMGW-PIB",
            "entry_type": "service",
        }

    @property
    def _current(self) -> dict | None:
        if self.coordinator.data:
            return self.coordinator.data.get("current")
        return None

    @property
    def condition(self) -> str | None:
        current = self._current
        if not current:
            return None

        # Try icon first
        icon = current.get("icon")
        if icon and isinstance(icon, str) and len(icon) >= 6:
            return parse_imgw_icon(icon)

        # Fallback: derive condition from weather data
        precip = current.get("precip") or 0
        snow = current.get("snow") or 0
        cloud = current.get("cloud")

        if snow > 0:
            return "snowy"
        if precip > 2:
            return "pouring"
        if precip > 0:
            return "rainy"
        if cloud is not None:
            if cloud <= 10:
                return "sunny"
            if cloud <= 50:
                return "partlycloudy"
            return "cloudy"

        return None

    @property
    def native_temperature(self) -> float | None:
        current = self._current
        return current.get("temp") if current else None

    @property
    def native_apparent_temperature(self) -> float | None:
        current = self._current
        return current.get("feels_like") if current else None

    @property
    def humidity(self) -> float | None:
        current = self._current
        return current.get("humidity") if current else None

    @property
    def native_pressure(self) -> float | None:
        current = self._current
        return current.get("pressure") if current else None

    @property
    def native_wind_speed(self) -> float | None:
        current = self._current
        return current.get("wind_speed") if current else None

    @property
    def native_wind_gust_speed(self) -> float | None:
        current = self._current
        return current.get("wind_gust") if current else None

    @property
    def wind_bearing(self) -> float | None:
        current = self._current
        return current.get("wind_dir") if current else None

    @property
    def cloud_coverage(self) -> float | None:
        current = self._current
        return current.get("cloud") if current else None

    @property
    def extra_state_attributes(self) -> dict:
        """Extra attributes for the card."""
        data = self.coordinator.data or {}
        current = data.get("current", {})
        sun = data.get("sun", {})
        return {
            "location": self._location_name,
            "precipitation": current.get("precip"),
            "rain": current.get("rain"),
            "snow": current.get("snow"),
            "model": current.get("model"),
            "icon_imgw": current.get("icon"),
            "sunrise": sun.get("Sunrise"),
            "sunset": sun.get("Sunset"),
            "hourly": data.get("hourly", []),
            "daily": data.get("daily", []),
        }

    async def async_forecast_daily(self) -> list[Forecast]:
        """Return daily forecast."""
        data = self.coordinator.data or {}
        daily = data.get("daily", [])
        forecasts = []

        # Group by date, merge day+night into single entries
        by_date: dict[str, dict] = {}
        for entry in daily:
            date_key = entry.get("date", "")
            if "T" in date_key:
                date_key = date_key.split("T")[0]
            if not date_key:
                continue

            if date_key not in by_date:
                by_date[date_key] = {
                    "hi": None, "lo": None, "icon": None,
                    "wind": None, "precip": 0,
                }

            rec = by_date[date_key]
            t_max = entry.get("temp_max")
            t_min = entry.get("temp_min")
            if t_max is not None and (rec["hi"] is None or t_max > rec["hi"]):
                rec["hi"] = t_max
            if t_min is not None and (rec["lo"] is None or t_min < rec["lo"]):
                rec["lo"] = t_min
            if entry.get("is_day") and entry.get("icon"):
                rec["icon"] = entry["icon"]
            elif rec["icon"] is None and entry.get("icon"):
                rec["icon"] = entry["icon"]
            w = entry.get("wind_max")
            if w is not None and (rec["wind"] is None or w > rec["wind"]):
                rec["wind"] = w
            p = entry.get("precip")
            if p is not None:
                rec["precip"] = (rec["precip"] or 0) + p

        for date_key in sorted(by_date.keys()):
            rec = by_date[date_key]
            fc = Forecast(
                datetime=f"{date_key}T12:00:00",
                condition=parse_imgw_icon(rec["icon"] or ""),
                native_temperature=rec["hi"],
                native_templow=rec["lo"],
                native_wind_speed=rec["wind"],
                precipitation=rec["precip"],
            )
            forecasts.append(fc)

        return forecasts

    async def async_forecast_hourly(self) -> list[Forecast]:
        """Return hourly forecast."""
        data = self.coordinator.data or {}
        hourly = data.get("hourly", [])
        forecasts = []

        for entry in hourly:
            fc = Forecast(
                datetime=entry["date"],
                condition=parse_imgw_icon(entry.get("icon", "")),
                native_temperature=entry.get("temp"),
                native_apparent_temperature=entry.get("feels_like"),
                humidity=entry.get("humidity"),
                native_pressure=entry.get("pressure"),
                native_wind_speed=entry.get("wind_speed"),
                native_wind_gust_speed=entry.get("wind_gust"),
                wind_bearing=entry.get("wind_dir"),
                cloud_coverage=entry.get("cloud"),
                precipitation=entry.get("precip"),
            )
            forecasts.append(fc)

        return forecasts
