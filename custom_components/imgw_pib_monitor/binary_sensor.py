"""Binary sensor platform for IMGW-PIB Monitor enhanced warnings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_AUTO_DETECT,
    CONF_ENABLE_ENHANCED_WARNINGS_METEO,
    CONF_POWIAT,
    CONF_POWIAT_NAME,
    CONF_USE_POWIAT_FOR_WARNINGS,
    CONF_VOIVODESHIP,
    DATA_TYPE_WARNINGS_METEO_ENHANCED,
    DOMAIN,
    MANUFACTURER,
    PHENOMENON_CODES,
    VOIVODESHIPS,
)
from .coordinator import ImgwDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class ImgwBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe an IMGW enhanced warning binary sensor entity."""

    is_on_fn: Callable[[dict[str, Any]], bool]
    extra_attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _phenomenon_attrs(
    data: dict[str, Any], code: str, detail_key: str
) -> dict[str, Any]:
    """Extract attributes for a specific phenomenon from warning data."""
    warnings = data.get(detail_key, {}).get(code, [])
    if not warnings:
        return {}
    attrs: dict[str, Any] = {"warnings_count": len(warnings)}
    # Include details of the most severe warning
    top = warnings[0]
    attrs["level"] = top.get("level")
    attrs["probability"] = top.get("probability")
    attrs["valid_from"] = top.get("valid_from")
    attrs["valid_to"] = top.get("valid_to")
    attrs["phenomenon_name"] = top.get("phenomenon_name")
    content = top.get("sms") or top.get("content", "")
    if content:
        attrs["content"] = content[:500]
    return attrs


def _build_enhanced_binary_sensors() -> tuple[ImgwBinarySensorEntityDescription, ...]:
    """Build all enhanced warning binary sensor descriptions."""
    sensors: list[ImgwBinarySensorEntityDescription] = []

    # Per-level binary sensors (present + active)
    for level in (1, 2, 3):
        for mode in ("present", "active"):
            sensors.append(
                ImgwBinarySensorEntityDescription(
                    key=f"enh_warning_level_{level}_{mode}",
                    translation_key=f"enh_warning_level_{level}_{mode}",
                    device_class=BinarySensorDeviceClass.SAFETY,
                    icon=f"mdi:numeric-{level}-box",
                    is_on_fn=lambda data, _l=level, _m=mode: any(
                        w["level"] >= _l
                        and (w["is_active"] if _m == "active" else True)
                        for w in data.get("warnings", [])
                    ),
                    extra_attrs_fn=lambda data, _l=level, _m=mode: {
                        "warnings_count": sum(
                            1
                            for w in data.get("warnings", [])
                            if w["level"] >= _l
                            and (w["is_active"] if _m == "active" else True)
                        )
                    },
                )
            )

    # Per-phenomenon binary sensors (present + active)
    for code, (_name, icon) in PHENOMENON_CODES.items():
        for mode in ("present", "active"):
            phenomena_key = f"{mode}_phenomena"
            detail_key = f"by_phenomenon_{mode}"
            sensors.append(
                ImgwBinarySensorEntityDescription(
                    key=f"enh_warning_{code.lower()}_{mode}",
                    translation_key=f"enh_warning_{code.lower()}_{mode}",
                    device_class=BinarySensorDeviceClass.SAFETY,
                    icon=icon,
                    is_on_fn=lambda data, _c=code, _pk=phenomena_key: _c
                    in data.get(_pk, []),
                    extra_attrs_fn=lambda data, _c=code, _dk=detail_key: _phenomenon_attrs(
                        data, _c, _dk
                    ),
                )
            )

    return tuple(sensors)


ENHANCED_BINARY_SENSORS = _build_enhanced_binary_sensors()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IMGW-PIB Monitor enhanced warning binary sensors."""
    if not entry.data.get(CONF_ENABLE_ENHANCED_WARNINGS_METEO):
        return

    coordinator: ImgwDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ImgwEnhancedBinarySensor(coordinator, description)
        for description in ENHANCED_BINARY_SENSORS
    ]
    async_add_entities(entities)


class ImgwEnhancedBinarySensor(
    CoordinatorEntity[ImgwDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor for IMGW-PIB enhanced meteorological warnings."""

    entity_description: ImgwBinarySensorEntityDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: ImgwDataUpdateCoordinator,
        description: ImgwBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        eid = coordinator.config_entry.entry_id
        # Stable ID regardless of filtering level
        self._attr_unique_id = f"{eid}_{description.key}"

    @property
    def translation_placeholders(self) -> dict[str, str]:
        """Return placeholders for entity name translation."""
        return {"station_suffix": ""}

    @property
    def _warning_data(self) -> dict[str, Any]:
        """Return enhanced warning data."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get(DATA_TYPE_WARNINGS_METEO_ENHANCED, {})

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self._warning_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.entity_description.extra_attrs_fn:
            return None
        attrs = self.entity_description.extra_attrs_fn(self._warning_data)
        # Truncate long strings
        for k, v in attrs.items():
            if isinstance(v, str) and len(v) > 500:
                attrs[k] = v[:500]
        return attrs or None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info — shared with enhanced sensor entities."""
        is_auto = self.coordinator.config_data.get(CONF_AUTO_DETECT, False)
        mode_label = "autodiscovery" if is_auto else "manual"
        eid = self.coordinator.config_entry.entry_id

        voiv_code = self.coordinator.config_data.get(CONF_VOIVODESHIP, "")
        powiat_code = self.coordinator.config_data.get(CONF_POWIAT)
        use_powiat = self.coordinator.config_data.get(
            CONF_USE_POWIAT_FOR_WARNINGS, False
        )

        warning_type_label = "meteo (rozszerzone)"

        # Stable identifier regardless of filtering level
        identifier = f"{DATA_TYPE_WARNINGS_METEO_ENHANCED}_{eid}"

        if use_powiat and powiat_code and powiat_code != "all":
            powiat_name = self.coordinator.config_data.get(
                CONF_POWIAT_NAME, powiat_code
            )
            name = f"Ostrzeżenia {warning_type_label} — {powiat_name}"
        else:
            voiv_name = VOIVODESHIPS.get(voiv_code, voiv_code)
            name = f"Ostrzeżenia {warning_type_label} — {voiv_name}"

        return {
            "identifiers": {(DOMAIN, identifier)},
            "name": name,
            "manufacturer": MANUFACTURER,
            "model": f"Ostrzeżenia - tryb: {mode_label} | Dane z API meteo.imgw.pl",
            "entry_type": "service",
            "configuration_url": "https://github.com/abnvle/ha-imgw-pib-monitor",
        }
