"""Sensor platform for IMGW-PIB Monitor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_AUTO_DETECT,
    CONF_ENABLE_WARNINGS_HYDRO,
    CONF_ENABLE_WARNINGS_METEO,
    CONF_SELECTED_HYDRO,
    CONF_SELECTED_METEO,
    CONF_SELECTED_SYNOP,
    CONF_VOIVODESHIP,
    DATA_TYPE_HYDRO,
    DATA_TYPE_METEO,
    DATA_TYPE_SYNOP,
    DATA_TYPE_WARNINGS_HYDRO,
    DATA_TYPE_WARNINGS_METEO,
    DOMAIN,
    MANUFACTURER,
    VOIVODESHIPS,
)
from .coordinator import ImgwDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class ImgwSensorEntityDescription(SensorEntityDescription):
    """Describe an IMGW sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]
    extra_attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    label_pl: str


# ── Weather sensors ────────────────────────────────────────────

SYNOP_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="temperature",
        label_pl="Temperatura",
        translation_key="synop_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("temperature"),
    ),
    ImgwSensorEntityDescription(
        key="wind_speed",
        label_pl="Prędkość wiatru",
        translation_key="synop_wind_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_speed"),
    ),
    ImgwSensorEntityDescription(
        key="wind_direction",
        label_pl="Kierunek wiatru",
        translation_key="synop_wind_direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_direction"),
    ),
    ImgwSensorEntityDescription(
        key="humidity",
        label_pl="Wilgotność",
        translation_key="synop_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("humidity"),
    ),
    ImgwSensorEntityDescription(
        key="precipitation",
        label_pl="Suma opadu",
        translation_key="synop_precipitation",
        native_unit_of_measurement="mm",
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("precipitation"),
    ),
    ImgwSensorEntityDescription(
        key="pressure",
        label_pl="Ciśnienie",
        translation_key="synop_pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("pressure"),
    ),
    ImgwSensorEntityDescription(
        key="station_id",
        label_pl="ID stacji",
        translation_key="station_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("station_id"),
    ),
    ImgwSensorEntityDescription(
        key="distance",
        label_pl="Odległość",
        translation_key="distance",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("distance"),
    ),
)


# ── River Level sensors ───────────────────────────────────────

HYDRO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="water_level",
        label_pl="Poziom wody",
        translation_key="hydro_water_level",
        native_unit_of_measurement="cm",
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("water_level"),
    ),
    ImgwSensorEntityDescription(
        key="flow",
        label_pl="Przepływ",
        translation_key="hydro_flow",
        native_unit_of_measurement="m³/s",
        icon="mdi:waves",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("flow"),
    ),
    ImgwSensorEntityDescription(
        key="water_temperature",
        label_pl="Temperatura wody",
        translation_key="hydro_water_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("water_temperature"),
    ),
    ImgwSensorEntityDescription(
        key="ice_phenomenon",
        label_pl="Zjawisko lodowe",
        translation_key="hydro_ice_phenomenon",
        icon="mdi:snowflake",
        value_fn=lambda data: data.get("ice_phenomenon"),
    ),
    ImgwSensorEntityDescription(
        key="station_id",
        label_pl="ID stacji",
        translation_key="station_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("station_id"),
    ),
    ImgwSensorEntityDescription(
        key="distance",
        label_pl="Odległość",
        translation_key="distance",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("distance"),
    ),
)


# ── Meteo sensors ─────────────────────────────────────

METEO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="air_temperature",
        label_pl="Temperatura powietrza",
        translation_key="meteo_air_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("air_temperature"),
    ),
    ImgwSensorEntityDescription(
        key="ground_temperature",
        label_pl="Temperatura gruntu",
        translation_key="meteo_ground_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-lines",
        value_fn=lambda data: data.get("ground_temperature"),
    ),
    ImgwSensorEntityDescription(
        key="wind_avg_speed",
        label_pl="Średnia prędkość wiatru",
        translation_key="meteo_wind_avg_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_avg_speed"),
    ),
    ImgwSensorEntityDescription(
        key="wind_max_speed",
        label_pl="Maksymalna prędkość wiatru",
        translation_key="meteo_wind_max_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_max_speed"),
    ),
    ImgwSensorEntityDescription(
        key="wind_gust",
        label_pl="Porywy wiatru",
        translation_key="meteo_wind_gust",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-windy",
        value_fn=lambda data: data.get("wind_gust_10min"),
    ),
    ImgwSensorEntityDescription(
        key="wind_direction",
        label_pl="Kierunek wiatru",
        translation_key="meteo_wind_direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_direction"),
    ),
    ImgwSensorEntityDescription(
        key="humidity",
        label_pl="Wilgotność",
        translation_key="meteo_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("humidity"),
    ),
    ImgwSensorEntityDescription(
        key="precipitation_10min",
        label_pl="Opad",
        translation_key="meteo_precipitation_10min",
        native_unit_of_measurement="mm",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-rainy",
        value_fn=lambda data: data.get("precipitation_10min"),
    ),
    ImgwSensorEntityDescription(
        key="station_id",
        label_pl="ID stacji",
        translation_key="station_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("station_code"),
    ),
    ImgwSensorEntityDescription(
        key="distance",
        label_pl="Odległość",
        translation_key="distance",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("distance"),
    ),
)


# ── Warning sensors ────────────────────────────────────────────

WARNINGS_METEO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="warnings_meteo_count",
        label_pl="Aktywne ostrzeżenia pogodowe",
        translation_key="warnings_meteo_count",
        icon="mdi:alert-circle",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("active_warnings_count", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_max_level",
        label_pl="Najwyższy stopień ostrzeżenia",
        translation_key="warnings_meteo_max_level",
        icon="mdi:alert",
        value_fn=lambda data: data.get("max_level", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_latest",
        label_pl="Ostatnie ostrzeżenie",
        translation_key="warnings_meteo_latest",
        icon="mdi:weather-lightning",
        value_fn=lambda data: (
            data.get("latest_warning", {}).get("event")
            if data.get("latest_warning")
            else None
        ),
        extra_attrs_fn=lambda data: (
            {
                "level": data["latest_warning"]["level"],
                "probability": data["latest_warning"]["probability"],
                "valid_from": data["latest_warning"]["valid_from"],
                "valid_to": data["latest_warning"]["valid_to"],
            }
            if data.get("latest_warning")
            else {}
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_details",
        label_pl="Szczegóły ostrzeżenia",
        translation_key="warnings_meteo_details",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: "Details" if data.get("latest_warning") else None,
        extra_attrs_fn=lambda data: (
            {
                "content": data["latest_warning"]["content"],
                "comment": data["latest_warning"]["comment"],
            }
            if data.get("latest_warning")
            else {}
        ),
    ),
)

WARNINGS_HYDRO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="warnings_hydro_count",
        label_pl="Aktywne ostrzeżenia rzeczne",
        translation_key="warnings_hydro_count",
        icon="mdi:flood",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("active_warnings_count", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_max_level",
        label_pl="Najwyższy stopień ostrzeżenia rz.",
        translation_key="warnings_hydro_max_level",
        icon="mdi:alert",
        value_fn=lambda data: data.get("max_level", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_latest",
        label_pl="Ostatnie ostrzeżenie rzeczne",
        translation_key="warnings_hydro_latest",
        icon="mdi:water-alert",
        value_fn=lambda data: (
            data.get("latest_warning", {}).get("event")
            if data.get("latest_warning")
            else None
        ),
        extra_attrs_fn=lambda data: (
            {
                "level": data["latest_warning"]["level"],
                "probability": data["latest_warning"]["probability"],
                "valid_from": data["latest_warning"]["valid_from"],
                "valid_to": data["latest_warning"]["valid_to"],
            }
            if data.get("latest_warning")
            else {}
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_details",
        label_pl="Szczegóły ostrzeżenia rzecznego",
        translation_key="warnings_hydro_details",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: "Details" if data.get("latest_warning") else None,
        extra_attrs_fn=lambda data: (
            {
                "description": data["latest_warning"]["description"],
                "areas": data["latest_warning"]["areas"],
            }
            if data.get("latest_warning")
            else {}
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IMGW-PIB Monitor sensors based on a config entry."""
    coordinator: ImgwDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ImgwSensorEntity] = []

    is_auto = entry.data.get(CONF_AUTO_DETECT, False)
    auto_data = coordinator.data.get("auto", {})

    # 1. Weather (SYNOP)
    if is_auto:
        if auto_data.get(DATA_TYPE_SYNOP):
            for desc in SYNOP_SENSORS:
                entities.append(ImgwSensorEntity(coordinator, desc, DATA_TYPE_SYNOP, "auto"))
    else:
        for sid in entry.data.get(CONF_SELECTED_SYNOP, []):
            for desc in SYNOP_SENSORS:
                entities.append(ImgwSensorEntity(coordinator, desc, DATA_TYPE_SYNOP, sid))

    # 2. River (HYDRO)
    if is_auto:
        if auto_data.get(DATA_TYPE_HYDRO):
            for desc in HYDRO_SENSORS:
                entities.append(ImgwSensorEntity(coordinator, desc, DATA_TYPE_HYDRO, "auto"))
    else:
        for sid in entry.data.get(CONF_SELECTED_HYDRO, []):
            for desc in HYDRO_SENSORS:
                entities.append(ImgwSensorEntity(coordinator, desc, DATA_TYPE_HYDRO, sid))

    # 3. Meteo (METEO)
    if is_auto:
        if auto_data.get(DATA_TYPE_METEO):
            for desc in METEO_SENSORS:
                entities.append(ImgwSensorEntity(coordinator, desc, DATA_TYPE_METEO, "auto"))
    else:
        for sid in entry.data.get(CONF_SELECTED_METEO, []):
            for desc in METEO_SENSORS:
                entities.append(ImgwSensorEntity(coordinator, desc, DATA_TYPE_METEO, sid))

    # 4. Warnings Meteo
    if entry.data.get(CONF_ENABLE_WARNINGS_METEO):
        for desc in WARNINGS_METEO_SENSORS:
            entities.append(ImgwSensorEntity(coordinator, desc, DATA_TYPE_WARNINGS_METEO))

    # 5. Warnings Hydro
    if entry.data.get(CONF_ENABLE_WARNINGS_HYDRO):
        for desc in WARNINGS_HYDRO_SENSORS:
            entities.append(ImgwSensorEntity(coordinator, desc, DATA_TYPE_WARNINGS_HYDRO))

    async_add_entities(entities)


class ImgwSensorEntity(CoordinatorEntity[ImgwDataUpdateCoordinator], SensorEntity):
    """Representation of an IMGW-PIB sensor."""

    entity_description: ImgwSensorEntityDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: ImgwDataUpdateCoordinator,
        description: ImgwSensorEntityDescription,
        data_type: str,
        station_id: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._data_type = data_type
        self._station_id = station_id

        # Unique ID - stable and scoped to entry, station, and sensor key
        eid = coordinator.config_entry.entry_id
        if station_id == "auto":
            # Avoid collisions for common sensors in auto mode
            uid = f"{eid}_{data_type}_auto_{description.key}"
        elif station_id:
            uid = f"{eid}_{sid_to_uid(station_id)}_{description.key}"
        else:
            voiv = coordinator.config_data.get(CONF_VOIVODESHIP, "global")
            uid = f"{eid}_{voiv}_{description.key}"
        self._attr_unique_id = uid

    @property
    def _station_data(self) -> dict[str, Any]:
        """Return data for this specific station/type."""
        if not self.coordinator.data:
            return {}
        
        if self._station_id == "auto":
            auto_data = self.coordinator.data.get("auto", {})
            return auto_data.get(self._data_type, {})
            
        type_data = self.coordinator.data.get(self._data_type, {})
        if self._station_id:
            return type_data.get(self._station_id, {})
        return type_data

    @property
    def name(self) -> str | None:
        """Return the name of the entity with station name in auto mode."""
        if self._station_id == "auto" and (sname := self._station_data.get("station_name")):
            # Fallback label from description + station name
            return f"{self.entity_description.label_pl} ({sname})"
        return super().name

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        # Single device for Auto-Discovery mode
        if self.coordinator.config_data.get(CONF_AUTO_DETECT):
            return {
                "identifiers": {(DOMAIN, f"auto_{self.coordinator.config_entry.entry_id}")},
                "name": "IMGW Auto-Discovery",
                "manufacturer": MANUFACTURER,
                "model": "Aggregated Multi-Station",
                "entry_type": "service",
                "configuration_url": "https://danepubliczne.imgw.pl/",
            }

        data = self._station_data
        if self._station_id:
            name = data.get("station_name") or self._station_id
            if self._data_type == DATA_TYPE_HYDRO and data.get("river"):
                name = f"{name} ({data.get('river')})"
            
            if self._data_type in (DATA_TYPE_SYNOP, DATA_TYPE_METEO):
                model = "Weather Station"
            elif self._data_type == DATA_TYPE_HYDRO:
                model = "River Level"
            else:
                model = self._data_type.replace("_", " ").title()
                
            identifier = f"{self._data_type}_{self._station_id}"
        else:
            # Warnings (Manual Mode)
            voiv_code = self.coordinator.config_data.get(CONF_VOIVODESHIP, "")
            voiv_name = VOIVODESHIPS.get(voiv_code, voiv_code)
            name = f"Ostrzeżenia — {voiv_name}"
            identifier = f"{self._data_type}_{voiv_code}"
            model = "Weather Alerts"

        return {
            "identifiers": {(DOMAIN, identifier)},
            "name": name,
            "manufacturer": MANUFACTURER,
            "model": model,
            "entry_type": "service",
            "configuration_url": "https://danepubliczne.imgw.pl/",
        }

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        val = self.entity_description.value_fn(self._station_data)
        if val is None:
            return None
        return val

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes with truncation to prevent database bloat."""
        data = self._station_data
        attrs = {}
        if self.entity_description.extra_attrs_fn:
            raw_attrs = self.entity_description.extra_attrs_fn(data)
            for k, v in raw_attrs.items():
                if isinstance(v, str):
                    attrs[k] = v[:500]  # Truncate long strings to 500 chars
                else:
                    attrs[k] = v
        
        # Add station name for context in auto mode
        if self._station_id == "auto" and data.get("station_name"):
            attrs["station_name"] = data["station_name"]

        # Add coordinates if available
        if data.get("latitude") and data.get("longitude"):
            attrs["latitude"] = data.get("latitude")
            attrs["longitude"] = data.get("longitude")
            
        return attrs or None

def sid_to_uid(station_id: Any) -> str:
    """Convert station ID to a safe unique ID part."""
    return str(station_id).replace("-", "_").lower()
