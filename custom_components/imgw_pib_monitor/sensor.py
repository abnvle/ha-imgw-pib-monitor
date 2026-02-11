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
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_DATA_TYPE,
    CONF_POWIAT,
    CONF_STATION_ID,
    CONF_STATION_NAME,
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
from .teryt import POWIATY


@dataclass(frozen=True, kw_only=True)
class ImgwSensorEntityDescription(SensorEntityDescription):
    """Describe an IMGW sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]
    extra_attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


# ── Synoptic sensors ────────────────────────────────────────────

SYNOP_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="synop_temperature",
        translation_key="synop_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("temperature"),
    ),
    ImgwSensorEntityDescription(
        key="synop_wind_speed",
        translation_key="synop_wind_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_speed"),
    ),
    ImgwSensorEntityDescription(
        key="synop_wind_direction",
        translation_key="synop_wind_direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_direction"),
    ),
    ImgwSensorEntityDescription(
        key="synop_humidity",
        translation_key="synop_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("humidity"),
    ),
    ImgwSensorEntityDescription(
        key="synop_precipitation",
        translation_key="synop_precipitation",
        native_unit_of_measurement="mm",
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("precipitation"),
    ),
    ImgwSensorEntityDescription(
        key="synop_pressure",
        translation_key="synop_pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("pressure"),
    ),
)


# ── Hydrological sensors ───────────────────────────────────────

HYDRO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="hydro_water_level",
        translation_key="hydro_water_level",
        native_unit_of_measurement="cm",
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("water_level"),
        extra_attrs_fn=lambda data: {
            "river": data.get("river"),
            "measurement_date": data.get("water_level_date"),
        },
    ),
    ImgwSensorEntityDescription(
        key="hydro_flow",
        translation_key="hydro_flow",
        native_unit_of_measurement="m³/s",
        icon="mdi:waves",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("flow"),
        extra_attrs_fn=lambda data: {
            "measurement_date": data.get("flow_date"),
        },
    ),
    ImgwSensorEntityDescription(
        key="hydro_water_temperature",
        translation_key="hydro_water_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("water_temperature"),
        extra_attrs_fn=lambda data: {
            "measurement_date": data.get("water_temperature_date"),
        },
    ),
    ImgwSensorEntityDescription(
        key="hydro_ice_phenomenon",
        translation_key="hydro_ice_phenomenon",
        icon="mdi:snowflake",
        value_fn=lambda data: data.get("ice_phenomenon"),
        extra_attrs_fn=lambda data: {
            "measurement_date": data.get("ice_phenomenon_date"),
        },
    ),
)


# ── Meteorological sensors ─────────────────────────────────────

METEO_SENSORS: tuple[ImgwSensorEntityDescription, ...] = (
    ImgwSensorEntityDescription(
        key="meteo_air_temperature",
        translation_key="meteo_air_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("air_temperature"),
        extra_attrs_fn=lambda data: {
            "measurement_date": data.get("air_temperature_date"),
        },
    ),
    ImgwSensorEntityDescription(
        key="meteo_ground_temperature",
        translation_key="meteo_ground_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-lines",
        value_fn=lambda data: data.get("ground_temperature"),
        extra_attrs_fn=lambda data: {
            "measurement_date": data.get("ground_temperature_date"),
        },
    ),
    ImgwSensorEntityDescription(
        key="meteo_wind_avg_speed",
        translation_key="meteo_wind_avg_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_avg_speed"),
    ),
    ImgwSensorEntityDescription(
        key="meteo_wind_max_speed",
        translation_key="meteo_wind_max_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_max_speed"),
    ),
    ImgwSensorEntityDescription(
        key="meteo_wind_gust",
        translation_key="meteo_wind_gust",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-windy",
        value_fn=lambda data: data.get("wind_gust_10min"),
    ),
    ImgwSensorEntityDescription(
        key="meteo_wind_direction",
        translation_key="meteo_wind_direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_direction"),
    ),
    ImgwSensorEntityDescription(
        key="meteo_humidity",
        translation_key="meteo_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("humidity"),
    ),
    ImgwSensorEntityDescription(
        key="meteo_precipitation_10min",
        translation_key="meteo_precipitation_10min",
        native_unit_of_measurement="mm",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-rainy",
        value_fn=lambda data: data.get("precipitation_10min"),
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
            data.get("latest_warning", {}).get("event", "Brak")
            if data.get("latest_warning")
            else "Brak"
        ),
        extra_attrs_fn=lambda data: (
            {
                "level": data["latest_warning"]["level"],
                "probability": data["latest_warning"]["probability"],
                "valid_from": data["latest_warning"]["valid_from"],
                "valid_to": data["latest_warning"]["valid_to"],
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
        icon="mdi:flood",
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
            data.get("latest_warning", {}).get("event", "Brak")
            if data.get("latest_warning")
            else "Brak"
        ),
        extra_attrs_fn=lambda data: (
            {
                "level": data["latest_warning"]["level"],
                "probability": data["latest_warning"]["probability"],
                "valid_from": data["latest_warning"]["valid_from"],
                "valid_to": data["latest_warning"]["valid_to"],
                "description": data["latest_warning"]["description"],
                "areas": data["latest_warning"]["areas"],
            }
            if data.get("latest_warning")
            else {}
        ),
    ),
)


SENSORS_BY_TYPE: dict[str, tuple[ImgwSensorEntityDescription, ...]] = {
    DATA_TYPE_SYNOP: SYNOP_SENSORS,
    DATA_TYPE_HYDRO: HYDRO_SENSORS,
    DATA_TYPE_METEO: METEO_SENSORS,
    DATA_TYPE_WARNINGS_METEO: WARNINGS_METEO_SENSORS,
    DATA_TYPE_WARNINGS_HYDRO: WARNINGS_HYDRO_SENSORS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IMGW-PIB Monitor sensors based on a config entry."""
    coordinator: ImgwDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    data_type = entry.data[CONF_DATA_TYPE]

    sensor_descriptions = SENSORS_BY_TYPE.get(data_type, ())

    entities = [
        ImgwSensorEntity(coordinator, description, entry)
        for description in sensor_descriptions
    ]

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
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        data_type = entry.data[CONF_DATA_TYPE]
        station_or_voiv = entry.data.get(CONF_STATION_ID) or entry.data.get(CONF_VOIVODESHIP)

        self._attr_unique_id = f"{data_type}_{station_or_voiv}_{description.key}"

        # Device info
        device_name = entry.data.get(CONF_STATION_NAME)
        if not device_name:
            voiv_code = entry.data.get(CONF_VOIVODESHIP, "")
            voiv_name = VOIVODESHIPS.get(voiv_code, voiv_code)
            powiat_code = entry.data.get(CONF_POWIAT)
            if powiat_code and powiat_code != "all":
                powiaty = POWIATY.get(voiv_code, {})
                powiat_name = powiaty.get(powiat_code, powiat_code)
                device_name = f"Ostrzeżenia — {voiv_name} — pow. {powiat_name}"
            else:
                device_name = f"Ostrzeżenia — {voiv_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{data_type}_{station_or_voiv}")},
            "name": device_name,
            "manufacturer": MANUFACTURER,
            "model": data_type.replace("_", " ").title(),
            "entry_type": "service",
        }

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if (
            self.coordinator.data is None
            or self.entity_description.extra_attrs_fn is None
        ):
            return None
        return self.entity_description.extra_attrs_fn(self.coordinator.data)