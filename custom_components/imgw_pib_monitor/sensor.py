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
    UnitOfLength,
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
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
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
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
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
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
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
        extra_attrs_fn=lambda data: {"warnings": data.get("warnings", [])},
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_max_level",
        translation_key="warnings_meteo_max_level",
        icon="mdi:alert",
        value_fn=lambda data: data.get("max_level", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_latest_event",
        translation_key="warnings_meteo_latest_event",
        icon="mdi:weather-lightning",
        value_fn=lambda data: (
            data["latest_warning"]["event"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_latest_level",
        translation_key="warnings_meteo_latest_level",
        icon="mdi:alert",
        value_fn=lambda data: (
            data["latest_warning"]["level"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_latest_probability",
        translation_key="warnings_meteo_latest_probability",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: (
            data["latest_warning"]["probability"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_latest_valid_from",
        translation_key="warnings_meteo_latest_valid_from",
        icon="mdi:clock-start",
        value_fn=lambda data: (
            data["latest_warning"]["valid_from"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_latest_valid_to",
        translation_key="warnings_meteo_latest_valid_to",
        icon="mdi:clock-end",
        value_fn=lambda data: (
            data["latest_warning"]["valid_to"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_meteo_latest_content",
        translation_key="warnings_meteo_latest_content",
        icon="mdi:text-box-outline",
        value_fn=lambda data: (
            (data["latest_warning"]["content"] or "")[:255]
            if data.get("latest_warning")
            else None
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
        extra_attrs_fn=lambda data: {"warnings": data.get("warnings", [])},
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_max_level",
        translation_key="warnings_hydro_max_level",
        icon="mdi:alert",
        value_fn=lambda data: data.get("max_level", 0),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_latest_event",
        translation_key="warnings_hydro_latest_event",
        icon="mdi:water-alert",
        value_fn=lambda data: (
            (data["latest_warning"]["event"] or data["latest_warning"].get("description", "")[:80])
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_latest_level",
        translation_key="warnings_hydro_latest_level",
        icon="mdi:alert",
        value_fn=lambda data: (
            data["latest_warning"]["level"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_latest_probability",
        translation_key="warnings_hydro_latest_probability",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: (
            data["latest_warning"]["probability"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_latest_valid_from",
        translation_key="warnings_hydro_latest_valid_from",
        icon="mdi:clock-start",
        value_fn=lambda data: (
            data["latest_warning"]["valid_from"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_latest_valid_to",
        translation_key="warnings_hydro_latest_valid_to",
        icon="mdi:clock-end",
        value_fn=lambda data: (
            data["latest_warning"]["valid_to"]
            if data.get("latest_warning")
            else None
        ),
    ),
    ImgwSensorEntityDescription(
        key="warnings_hydro_latest_description",
        translation_key="warnings_hydro_latest_description",
        icon="mdi:text-box-outline",
        value_fn=lambda data: (
            (data["latest_warning"].get("description") or "")[:255]
            if data.get("latest_warning")
            else None
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

    # Helper function to add sensors only if they have data
    def add_sensors(data_type: str, station_id: str | None, sensor_descs: tuple[ImgwSensorEntityDescription, ...]):
        s_data = coordinator.data.get(data_type, {}).get(station_id) if station_id else coordinator.data.get(data_type)

        if not s_data:
            return

        for desc in sensor_descs:
            if desc.value_fn(s_data) is not None:
                entities.append(ImgwSensorEntity(coordinator, desc, data_type, station_id))

    # 1. Weather (SYNOP)
    for sid in entry.data.get(CONF_SELECTED_SYNOP, []):
        add_sensors(DATA_TYPE_SYNOP, sid, SYNOP_SENSORS)

    # 2. Meteo (METEO)
    for sid in entry.data.get(CONF_SELECTED_METEO, []):
        add_sensors(DATA_TYPE_METEO, sid, METEO_SENSORS)

    # 3. River (HYDRO)
    for sid in entry.data.get(CONF_SELECTED_HYDRO, []):
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
    _attr_force_update = True

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

        # Unique ID - scoped to entry + station to keep entries independent
        eid = coordinator.config_entry.entry_id
        if station_id:
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
        return {"station_suffix": ""}

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        is_auto = self.coordinator.config_data.get(CONF_AUTO_DETECT, False)
        mode_label = "autodiscovery" if is_auto else "manual"
        eid = self.coordinator.config_entry.entry_id

        data = self._station_data
        if self._station_id:
            station_name = data.get("station_name") or self._station_id
            if self._data_type == DATA_TYPE_HYDRO and data.get("river"):
                station_name = f"{station_name} ({data.get('river')})"

            name = station_name

            if self._data_type == DATA_TYPE_SYNOP:
                model = f"Dane synop - tryb: {mode_label} | Dane z API IMGW-PIB"
            elif self._data_type == DATA_TYPE_METEO:
                model = f"Dane meteo - tryb: {mode_label} | Dane z API IMGW-PIB"
            elif self._data_type == DATA_TYPE_HYDRO:
                model = f"Dane hydro - tryb: {mode_label} | Dane z API IMGW-PIB"
            else:
                model = f"{self._data_type.replace('_', ' ').title()} - tryb: {mode_label} | Dane z API IMGW-PIB"

            identifier = f"{self._data_type}_{self._station_id}_{eid}"
        else:
            # Warnings — distinguish meteo from hydro in name
            voiv_code = self.coordinator.config_data.get(CONF_VOIVODESHIP, "")
            powiat_code = self.coordinator.config_data.get(CONF_POWIAT)
            use_powiat = self.coordinator.config_data.get(CONF_USE_POWIAT_FOR_WARNINGS, False)

            if self._data_type == DATA_TYPE_WARNINGS_METEO:
                warning_type_label = "meteo"
            elif self._data_type == DATA_TYPE_WARNINGS_HYDRO:
                warning_type_label = "hydro"
            else:
                warning_type_label = self._data_type

            if use_powiat and powiat_code and powiat_code != "all":
                powiat_name = self.coordinator.config_data.get(CONF_POWIAT_NAME, powiat_code)
                name = f"Ostrzeżenia {warning_type_label} — {powiat_name}"
                identifier = f"{self._data_type}_{powiat_code}_{eid}"
            else:
                voiv_name = VOIVODESHIPS.get(voiv_code, voiv_code)
                name = f"Ostrzeżenia {warning_type_label} — {voiv_name}"
                identifier = f"{self._data_type}_{voiv_code}_{eid}"

            model = f"Ostrzeżenia - tryb: {mode_label} | Dane z API IMGW-PIB"

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

        # Add coordinates if available
        if data.get("latitude") and data.get("longitude"):
            attrs["latitude"] = data.get("latitude")
            attrs["longitude"] = data.get("longitude")

        return attrs or None

def sid_to_uid(station_id: Any) -> str:
    """Convert station ID to a safe unique ID part."""
    return str(station_id).replace("-", "_").lower()
