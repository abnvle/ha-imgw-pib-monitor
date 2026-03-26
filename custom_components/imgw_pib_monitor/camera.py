"""Camera platform for IMGW-PIB Monitor — radar imagery."""

from __future__ import annotations

from datetime import datetime, timezone
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
    CONF_RADAR_TYPE,
    DOMAIN,
    MANUFACTURER,
    RADAR_TYPE_ALL,
    RADAR_TYPE_ALL_RADAR,
    RADAR_TYPE_CMAX,
    RADAR_TYPE_PAC,
    RADAR_TYPE_SAT,
    RADAR_TYPE_SRI,
)
from .coordinator import ImgwRadarCoordinator

PRODUCT_LABELS = {
    RADAR_TYPE_CMAX: "Odbiciowość (CMAX)",
    RADAR_TYPE_SRI: "Opady (SRI)",
    RADAR_TYPE_PAC: "Suma opadów 1h (PAC)",
    RADAR_TYPE_SAT: "Zdjęcie satelitarne",
}

ALL_RADAR_PRODUCTS = [RADAR_TYPE_CMAX, RADAR_TYPE_SRI, RADAR_TYPE_PAC]
ALL_PRODUCTS = [RADAR_TYPE_CMAX, RADAR_TYPE_SRI, RADAR_TYPE_PAC, RADAR_TYPE_SAT]


def get_selected_products(radar_type: str) -> list[str]:
    """Return list of product codes for a given radar_type setting."""
    if radar_type == RADAR_TYPE_ALL:
        return list(ALL_PRODUCTS)
    if radar_type == RADAR_TYPE_ALL_RADAR:
        return list(ALL_RADAR_PRODUCTS)
    if radar_type in PRODUCT_LABELS:
        return [radar_type]
    # Legacy "both" value from older config entries
    if radar_type == "both":
        return [RADAR_TYPE_CMAX, RADAR_TYPE_SRI]
    return []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IMGW Radar Camera entities."""
    radar_type = entry.data.get(CONF_RADAR_TYPE, RADAR_TYPE_CMAX)
    products = get_selected_products(radar_type)
    entities: list[ImgwRadarCamera] = []

    for product in products:
        coordinator = hass.data[DOMAIN].get(f"{entry.entry_id}_radar_{product}")
        if coordinator:
            entities.append(ImgwRadarCamera(coordinator, entry, product))

    async_add_entities(entities)


class ImgwRadarCamera(CoordinatorEntity[ImgwRadarCoordinator], Camera):
    """IMGW Radar composite camera entity."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_content_type = "image/png"

    def __init__(
        self,
        coordinator: ImgwRadarCoordinator,
        config_entry: ConfigEntry,
        product: str,
    ) -> None:
        """Initialize the radar camera."""
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._config_entry = config_entry
        self._product = product
        self._attr_unique_id = f"{DOMAIN}_radar_{product}_{config_entry.entry_id}"
        self._attr_name = PRODUCT_LABELS.get(product, product)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        location_name = self._config_entry.data.get(
            CONF_LOCATION_NAME, self._config_entry.title
        )
        return {
            "identifiers": {(DOMAIN, f"radar_{self._config_entry.entry_id}")},
            "name": f"IMGW Radar — {location_name}",
            "manufacturer": MANUFACTURER,
            "model": "Radar IMGW-PIB",
            "entry_type": "service",
            "configuration_url": "https://github.com/abnvle/ha-imgw-pib-monitor",
        }

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the latest radar image bytes."""
        return self.coordinator.image_bytes

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the latest radar image bytes (async variant)."""
        return self.coordinator.image_bytes

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with location and image metadata."""
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
