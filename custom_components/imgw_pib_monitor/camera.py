"""Camera platform for IMGW-PIB Monitor — radar imagery."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_FORECAST_LAT,
    CONF_FORECAST_LON,
    CONF_LOCATION_NAME,
    CONF_RADAR_PRODUCTS,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import ImgwRadarAnimCoordinator, ImgwRadarCoordinator

PRODUCT_LABELS = {
    "cmax": "Odbiciowość (CMAX)",
    "sri": "Opady (SRI)",
    "pac": "Suma opadów 1h (PAC)",
    "natural_color": "Zdjęcie satelitarne",
    "infrared": "Zachmurzenie (IR)",
    "water_vapor": "Para wodna",
    "cloud_type": "Typy chmur",
    "oze_pv": "Prognoza generacji PV",
    "oze_wind": "Prognoza generacji wiatr",
    "oze_pv_anim": "Animacja generacji PV (24h)",
    "oze_wind_anim": "Animacja generacji wiatr (24h)",
}

ANIM_PRODUCTS = {
    "oze_pv_anim": "oze_pv",
    "oze_wind_anim": "oze_wind",
}

SAT_PRODUCTS = {"natural_color", "infrared", "water_vapor", "cloud_type"}
OZE_PRODUCTS = {"oze_pv", "oze_wind"}
ANIM_PRODUCT_SET = set(ANIM_PRODUCTS.keys())

ALL_KNOWN_PRODUCTS = set(PRODUCT_LABELS.keys())


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IMGW Radar Camera entities."""
    products = entry.data.get(CONF_RADAR_PRODUCTS, [])
    entities: list[ImgwRadarCamera | ImgwRadarAnimCamera] = []

    for product in products:
        coordinator = hass.data[DOMAIN].get(f"{entry.entry_id}_radar_{product}")
        if coordinator:
            if product in ANIM_PRODUCTS:
                entities.append(ImgwRadarAnimCamera(coordinator, entry, product))
            else:
                entities.append(ImgwRadarCamera(coordinator, entry, product))

    async_add_entities(entities)


class ImgwRadarCamera(CoordinatorEntity[ImgwRadarCoordinator], Camera):
    """IMGW Radar composite camera entity."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_content_type = "image/png"
    _attr_frame_interval = 60

    def __init__(self, coordinator, config_entry, product):
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._config_entry = config_entry
        self._product = product
        self._attr_unique_id = f"{DOMAIN}_radar_{product}_{config_entry.entry_id}"
        self._attr_name = PRODUCT_LABELS.get(product, product)

    @property
    def device_info(self):
        location_name = self._config_entry.data.get(CONF_LOCATION_NAME, self._config_entry.title)
        return {
            "identifiers": {(DOMAIN, f"radar_{self._config_entry.entry_id}")},
            "name": f"IMGW Radar — {location_name}",
            "manufacturer": MANUFACTURER,
            "model": "Radar IMGW-PIB",
            "entry_type": "service",
            "configuration_url": "https://github.com/abnvle/ha-imgw-pib-monitor",
        }

    def camera_image(self, width=None, height=None):
        return self.coordinator.image_bytes

    async def async_camera_image(self, width=None, height=None):
        return self.coordinator.image_bytes

    @property
    def extra_state_attributes(self):
        lat = self._config_entry.data.get(CONF_FORECAST_LAT)
        lon = self._config_entry.data.get(CONF_FORECAST_LON)
        timestamp_str = None
        if self.coordinator.image_timestamp:
            try:
                ts = int(self.coordinator.image_timestamp)
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                timestamp_str = dt.isoformat()
            except (ValueError, TypeError, OSError):
                timestamp_str = str(self.coordinator.image_timestamp)
        return {
            "location_latitude": lat,
            "location_longitude": lon,
            "radar_product": self._product.upper(),
            "image_timestamp": timestamp_str,
        }


class ImgwRadarAnimCamera(CoordinatorEntity[ImgwRadarAnimCoordinator], Camera):
    """IMGW animated GIF camera entity for OZE forecasts."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_content_type = "image/gif"
    _attr_frame_interval = 300

    def __init__(self, coordinator, config_entry, product):
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._config_entry = config_entry
        self._product = product
        self._attr_unique_id = f"{DOMAIN}_radar_{product}_{config_entry.entry_id}"
        self._attr_name = PRODUCT_LABELS.get(product, product)

    @property
    def device_info(self):
        location_name = self._config_entry.data.get(CONF_LOCATION_NAME, self._config_entry.title)
        return {
            "identifiers": {(DOMAIN, f"radar_{self._config_entry.entry_id}")},
            "name": f"IMGW Radar — {location_name}",
            "manufacturer": MANUFACTURER,
            "model": "Radar IMGW-PIB",
            "entry_type": "service",
            "configuration_url": "https://github.com/abnvle/ha-imgw-pib-monitor",
        }

    def camera_image(self, width=None, height=None):
        return self.coordinator.image_bytes

    async def async_camera_image(self, width=None, height=None):
        return self.coordinator.image_bytes

    @property
    def extra_state_attributes(self):
        base_product = ANIM_PRODUCTS.get(self._product, self._product)
        return {
            "location_latitude": self._config_entry.data.get(CONF_FORECAST_LAT),
            "location_longitude": self._config_entry.data.get(CONF_FORECAST_LON),
            "radar_product": base_product,
            "animation_hours": self.coordinator.hours,
        }
