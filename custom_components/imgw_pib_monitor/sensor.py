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


# ── Weather sensors ────────────────────────────────────────────

SYNOP_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="temperature",
        translation_key="synop_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("temperature"),
    ),
    ImgwSensorEntityDescription(
        key="wind_speed",
        translation_key="synop_wind_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("wind_speed"),
    ),
    ImgwSensorEntityDescription(
        key="wind_direction",
        translation_key="synop_wind_direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("wind_direction"),
    ),
    ImgwSensorEntityDescription(
        key="humidity",
        translation_key="synop_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("humidity"),
    ),
    ImgwSensorEntityDescription(
        key="precipitation",
        translation_key="synop_precipitation",
        native_unit_of_measurement="mm",
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("precipitation"),
    ),
    ImgwSensorEntityDescription(
        key="pressure",
        translation_key="synop_pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("pressure"),
    ),
    ImgwSensorEntityDescription(
        key="station_id",
        translation_key="synop_station_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("station_id"),
    ),
    ImgwSensorEntityDescription(
        key="distance",
        translation_key="synop_distance",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("distance"),
    ),
)


# ── River Level sensors ───────────────────────────────────────

HYDRO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="water_level",
        translation_key="hydro_water_level",
        native_unit_of_measurement="cm",
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("water_level"),
    ),
    ImgwSensorEntityDescription(
        key="flow",
        translation_key="hydro_flow",
        native_unit_of_measurement="m³/s",
        icon="mdi:waves",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("flow"),
    ),
    ImgwSensorEntityDescription(
        key="water_temperature",
        translation_key="hydro_water_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("water_temperature"),
    ),
    ImgwSensorEntityDescription(
        key="ice_phenomenon",
        translation_key="hydro_ice_phenomenon",
        icon="mdi:snowflake",
        value_fn=lambda data: data.get("ice_phenomenon"),
    ),
    ImgwSensorEntityDescription(
        key="station_id",
        translation_key="hydro_station_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("station_id"),
    ),
    ImgwSensorEntityDescription(
        key="distance",
        translation_key="hydro_distance",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("distance"),
    ),
)


# ── Meteo sensors ─────────────────────────────────────

METEO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="air_temperature",
        translation_key="meteo_air_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("air_temperature"),
    ),
    ImgwSensorEntityDescription(
        key="ground_temperature",
        translation_key="meteo_ground_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-lines",
        value_fn=lambda data: data.get("ground_temperature"),
    ),
    ImgwSensorEntityDescription(
        key="wind_avg_speed",
        translation_key="meteo_wind_avg_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("wind_avg_speed"),
    ),
    ImgwSensorEntityDescription(
        key="wind_max_speed",
        translation_key="meteo_wind_max_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("wind_max_speed"),
    ),
    ImgwSensorEntityDescription(
        key="wind_gust",
        translation_key="meteo_wind_gust",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:weather-windy",
        value_fn=lambda data: data.get("wind_gust_10min"),
    ),
    ImgwSensorEntityDescription(
        key="wind_direction",
        translation_key="meteo_wind_direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("wind_direction"),
    ),
    ImgwSensorEntityDescription(
        key="humidity",
        translation_key="meteo_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("humidity"),
    ),
    ImgwSensorEntityDescription(
        key="precipitation_10min",
        translation_key="meteo_precipitation_10min",
        native_unit_of_measurement="mm",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:weather-rainy",
        value_fn=lambda data: data.get("precipitation_10min"),
    ),
    ImgwSensorEntityDescription(
        key="station_id",
        translation_key="meteo_station_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("station_code"),
    ),
    ImgwSensorEntityDescription(
        key="distance",
        translation_key="meteo_distance",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("distance"),
    ),
)


# ── Warning sensors ────────────────────────────────────────────

WARNINGS_METEO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="warnings_meteo_count",
        translation_key="warnings_meteo_count",
        icon="mdi:alert-circle",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("active_warnings_count", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_max_level",
        translation_key="warnings_meteo_max_level",
        icon="mdi:alert",
        value_fn=lambda data: data.get("max_level", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_latest",
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
        translation_key="warnings_hydro_count",
        icon="mdi:alert-circle",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("active_warnings_count", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_max_level",
        translation_key="warnings_hydro_max_level",
        icon="mdi:alert",
        value_fn=lambda data: data.get("max_level", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_latest",
        translation_key="warnings_hydro_latest",
        icon="mdi:water-alert",
        value_fn=lambda data: (
            data.get("latest_warning", {}).get("event") or
            (data.get("latest_warning", {}).get("description", "")[:80] + "..."
             if len(data.get("latest_warning", {}).get("description", "")) > 80
             else data.get("latest_warning", {}).get("description", ""))
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

    # Helper function to add sensors only if they have data
    def add_sensors(data_type: str, station_id: str | None, sensor_descs: tuple[ImgwSensorEntityDescription, ...]):
        if station_id == "auto":
            s_data = auto_data.get(data_type)
        else:
            s_data = coordinator.data.get(data_type, {}).get(station_id) if station_id else coordinator.data.get(data_type)

        if not s_data:
            return

        for desc in sensor_descs:
            if desc.value_fn(s_data) is not None:
                entities.append(ImgwSensorEntity(coordinator, desc, data_type, station_id))

    # 1. Weather (SYNOP)
    selected_synop = entry.data.get(CONF_SELECTED_SYNOP, [])
    if selected_synop:
        if is_auto:
            add_sensors(DATA_TYPE_SYNOP, "auto", SYNOP_SENSORS)
        else:
            for sid in selected_synop:
                add_sensors(DATA_TYPE_SYNOP, sid, SYNOP_SENSORS)

    # 2. Meteo (METEO)
    selected_meteo = entry.data.get(CONF_SELECTED_METEO, [])
    if selected_meteo:
        if is_auto:
            add_sensors(DATA_TYPE_METEO, "auto", METEO_SENSORS)
        else:
            for sid in selected_meteo:
                add_sensors(DATA_TYPE_METEO, sid, METEO_SENSORS)

    # 3. River (HYDRO)
    selected_hydro = entry.data.get(CONF_SELECTED_HYDRO, [])
    if selected_hydro:
        if is_auto:
            add_sensors(DATA_TYPE_HYDRO, "auto", HYDRO_SENSORS)
        else:
            for sid in selected_hydro:
                add_sensors(DATA_TYPE_HYDRO, sid, HYDRO_SENSORS)

    # 4. Warnings Meteo
    if entry.data.get(CONF_ENABLE_WARNINGS_METEO):
        add_sensors(DATA_TYPE_WARNINGS_METEO, None, WARNINGS_METEO_SENSORS)

    # 5. Warnings Hydro
    if entry.data.get(CONF_ENABLE_WARNINGS_HYDRO):
        add_sensors(DATA_TYPE_WARNINGS_HYDRO, None, WARNINGS_HYDRO_SENSORS)

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
            # For warnings - include powiat in unique ID if configured
            powiat = coordinator.config_data.get(CONF_POWIAT)
            use_powiat = coordinator.config_data.get(CONF_USE_POWIAT_FOR_WARNINGS, False)
            if use_powiat and powiat and powiat != "all":
                uid = f"{eid}_{powiat}_{description.key}"
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
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self.entity_description.icon:
            return self.entity_description.icon
        return None

    @property
    def translation_placeholders(self) -> dict[str, str]:
        """Return placeholders for entity name translation."""
        if self._station_id == "auto":
            sname = self._station_data.get("station_name", "")
            if sname:
                if self._data_type == DATA_TYPE_HYDRO and (river := self._station_data.get("river")):
                    return {"station_suffix": f" ({sname} - {river})"}
                return {"station_suffix": f" ({sname})"}
        return {"station_suffix": ""}

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        # Single device for Auto-Discovery mode
        if self.coordinator.config_data.get(CONF_AUTO_DETECT):
            return {
                "identifiers": {(DOMAIN, f"auto_{self.coordinator.config_entry.entry_id}")},
                "name": "IMGW-PIB Monitor",
                "manufacturer": MANUFACTURER,
                "model": "Tryb: autodiscovery | Dane z API IMGW-PIB",
                "entry_type": "service",
                "configuration_url": "https://evt.pl",
            }

        data = self._station_data
        if self._station_id:
            name = data.get("station_name") or self._station_id
            if self._data_type == DATA_TYPE_HYDRO and data.get("river"):
                name = f"{name} ({data.get('river')})"

            if self._data_type == DATA_TYPE_SYNOP:
                model = "Dane synop - tryb: manual | Dane z API IMGW-PIB"
            elif self._data_type == DATA_TYPE_METEO:
                model = "Dane meteo - tryb: manual | Dane z API IMGW-PIB"
            elif self._data_type == DATA_TYPE_HYDRO:
                model = "Dane hydro - tryb: manual | Dane z API IMGW-PIB"
            else:
                model = f"{self._data_type.replace('_', ' ').title()} - tryb: manual | Dane z API IMGW-PIB"

            identifier = f"{self._data_type}_{self._station_id}"
        else:
            # Warnings (Manual Mode)
            voiv_code = self.coordinator.config_data.get(CONF_VOIVODESHIP, "")
            powiat_code = self.coordinator.config_data.get(CONF_POWIAT)
            use_powiat = self.coordinator.config_data.get(CONF_USE_POWIAT_FOR_WARNINGS, False)

            # Determine name based on warning level
            if use_powiat and powiat_code and powiat_code != "all":
                powiat_name = self.coordinator.config_data.get(CONF_POWIAT_NAME, powiat_code)
                name = f"Ostrzeżenia — {powiat_name}"
                identifier = f"{self._data_type}_{powiat_code}"
            else:
                voiv_name = VOIVODESHIPS.get(voiv_code, voiv_code)
                name = f"Ostrzeżenia — {voiv_name}"
                identifier = f"{self._data_type}_{voiv_code}"

            model = "Ostrzeżenia - tryb: manual | Dane z API IMGW-PIB"

        return {
            "identifiers": {(DOMAIN, identifier)},
            "name": name,
            "manufacturer": MANUFACTURER,
            "model": model,
            "entry_type": "service",
            "configuration_url": "https://evt.pl",
        }

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        val = self.entity_description.value_fn(self._station_data)
        if val is None:
            return None
        # Round floats to avoid IEEE 754 precision artifacts (e.g. 7.599999 instead of 7.6)
        if isinstance(val, float) and self.entity_description.suggested_display_precision is not None:
            return round(val, self.entity_description.suggested_display_precision)
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

        # Add station name and ID for context in auto mode
        if self._station_id == "auto":
            if data.get("station_name"):
                attrs["station_name"] = data["station_name"]
            # Add station ID to verify correct station selection (especially for SYNOP where API has incorrect names)
            station_id_key = "station_id" if self._data_type != DATA_TYPE_METEO else "station_code"
            if data.get(station_id_key):
                attrs["station_id"] = data[station_id_key]
            # For hydro, add river name
            if self._data_type == DATA_TYPE_HYDRO and data.get("river"):
                attrs["river"] = data["river"]

        # Add coordinates if available
        if data.get("latitude") and data.get("longitude"):
            attrs["latitude"] = data.get("latitude")
            attrs["longitude"] = data.get("longitude")

        return attrs or None

def sid_to_uid(station_id: Any) -> str:
    """Convert station ID to a safe unique ID part."""
    return str(station_id).replace("-", "_").lower()
