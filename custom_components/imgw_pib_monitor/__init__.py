"""IMGW-PIB Monitor — comprehensive integration for IMGW-PIB data."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ImgwApiClient
from .const import (
    CONF_ENABLE_ENHANCED_WARNINGS_METEO,
    CONF_ENABLE_RADAR_CAMERA,
    CONF_ENABLE_WEATHER_FORECAST,
    CONF_RADAR_PRODUCTS,
    RADAR_OZE_UPDATE_INTERVAL,
    RADAR_SAT_UPDATE_INTERVAL,
    RADAR_UPDATE_INTERVAL,
    CONF_FORECAST_LAT,
    CONF_FORECAST_LON,
    CONF_LOCATION_NAME,
    CONF_POWIAT,
    CONF_POWIAT_NAME,
    CONF_UPDATE_INTERVAL,
    CONF_USE_POWIAT_FOR_WARNINGS,
    DATA_TYPE_WARNINGS_METEO_ENHANCED,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .utils import nominatim_reverse_geocode, reverse_geocode
from .coordinator import (
    ImgwDataUpdateCoordinator,
    ImgwForecastCoordinator,
    ImgwRadarAnimCoordinator,
    ImgwGlobalDataCoordinator,
    ImgwRadarCoordinator,
)

_LOGGER = logging.getLogger(__name__)


def _async_cleanup_forecast(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove forecast entity and device from registries when forecast is disabled."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "weather", DOMAIN, f"{DOMAIN}_weather_{entry.entry_id}"
    )
    if entity_id:
        ent_reg.async_remove(entity_id)
        _LOGGER.debug("Removed forecast entity: %s", entity_id)

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(
        identifiers={(DOMAIN, f"forecast_{entry.entry_id}")}
    )
    if device:
        dev_reg.async_remove_device(device.id)
        _LOGGER.debug("Removed forecast device: %s", device.name)


def _async_cleanup_enhanced_warnings(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove enhanced warning entities and device when feature is disabled."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        for domain, identifier in device.identifiers:
            if (
                domain == DOMAIN
                and identifier.startswith(DATA_TYPE_WARNINGS_METEO_ENHANCED)
            ):
                for entity in er.async_entries_for_device(
                    ent_reg, device.id, include_disabled_entities=True
                ):
                    ent_reg.async_remove(entity.entity_id)
                    _LOGGER.debug(
                        "Removed enhanced warning entity: %s", entity.entity_id
                    )
                dev_reg.async_remove_device(device.id)
                _LOGGER.debug("Removed enhanced warning device: %s", device.name)
                return


def _async_cleanup_radar(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove radar camera entities and device from registries when radar is disabled."""
    from .camera import ALL_KNOWN_PRODUCTS
    ent_reg = er.async_get(hass)
    for product in ALL_KNOWN_PRODUCTS:
        entity_id = ent_reg.async_get_entity_id(
            "camera", DOMAIN, f"{DOMAIN}_radar_{product}_{entry.entry_id}"
        )
        if entity_id:
            ent_reg.async_remove(entity_id)
            _LOGGER.debug("Removed radar camera entity: %s", entity_id)

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(
        identifiers={(DOMAIN, f"radar_{entry.entry_id}")}
    )
    if device:
        dev_reg.async_remove_device(device.id)
        _LOGGER.debug("Removed radar device: %s", device.name)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IMGW-PIB Monitor from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    # Initialize global coordinator if not already present
    if "global_coordinator" not in hass.data[DOMAIN]:
        session = async_get_clientsession(hass)
        api = ImgwApiClient(session)
        hass.data[DOMAIN]["global_coordinator"] = ImgwGlobalDataCoordinator(
            hass, api, update_interval
        )
    else:
        # Sync global coordinator interval to the shortest across all entries
        global_coord = hass.data[DOMAIN]["global_coordinator"]
        min_interval = update_interval
        for other_entry in hass.config_entries.async_entries(DOMAIN):
            if other_entry.entry_id != entry.entry_id:
                other_interval = other_entry.data.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                )
                min_interval = min(min_interval, other_interval)
        global_coord.update_interval = timedelta(minutes=min_interval)

    global_coordinator = hass.data[DOMAIN]["global_coordinator"]

    coordinator = ImgwDataUpdateCoordinator(
        hass=hass,
        global_coordinator=global_coordinator,
        entry=entry,
        update_interval=update_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Determine which platforms to load
    platforms = ["sensor"]

    # Enhanced warnings support (binary_sensor platform)
    if entry.data.get(CONF_ENABLE_ENHANCED_WARNINGS_METEO):
        platforms.append("binary_sensor")
        hass.data[DOMAIN][f"{entry.entry_id}_binary_sensor"] = True
    else:
        # Enhanced warnings disabled — clean up leftover entities/devices
        _async_cleanup_enhanced_warnings(hass, entry)

    # Forecast support (weather platform)
    if entry.data.get(CONF_ENABLE_WEATHER_FORECAST):
        try:
            lat = entry.data.get(CONF_FORECAST_LAT, hass.config.latitude)
            lon = entry.data.get(CONF_FORECAST_LON, hass.config.longitude)

            forecast_coordinator = ImgwForecastCoordinator(hass, lat, lon, update_interval)
            await forecast_coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN][f"{entry.entry_id}_forecast"] = forecast_coordinator
            platforms.append("weather")
        except Exception as err:
            _LOGGER.warning("Forecast unavailable at startup, skipping: %s", err)
    else:
        # Forecast disabled — clean up leftover entity/device from registry
        _async_cleanup_forecast(hass, entry)

    # Radar camera support (camera platform)
    radar_products = entry.data.get(CONF_RADAR_PRODUCTS, [])
    if entry.data.get(CONF_ENABLE_RADAR_CAMERA) and radar_products:
        from .camera import ANIM_PRODUCTS, SAT_PRODUCTS, OZE_PRODUCTS, ANIM_PRODUCT_SET, ALL_KNOWN_PRODUCTS

        lat = entry.data.get(CONF_FORECAST_LAT, hass.config.latitude)
        lon = entry.data.get(CONF_FORECAST_LON, hass.config.longitude)

        loaded_products = []
        for product in radar_products:
            try:
                if product in ANIM_PRODUCT_SET:
                    base_product = ANIM_PRODUCTS[product]
                    coordinator = ImgwRadarAnimCoordinator(hass, lat, lon, base_product, 24)
                elif product in OZE_PRODUCTS:
                    coordinator = ImgwRadarCoordinator(hass, lat, lon, product, RADAR_OZE_UPDATE_INTERVAL)
                elif product in SAT_PRODUCTS:
                    coordinator = ImgwRadarCoordinator(hass, lat, lon, product, RADAR_SAT_UPDATE_INTERVAL)
                else:
                    coordinator = ImgwRadarCoordinator(hass, lat, lon, product, RADAR_UPDATE_INTERVAL)
                await coordinator.async_config_entry_first_refresh()
                hass.data[DOMAIN][f"{entry.entry_id}_radar_{product}"] = coordinator
                loaded_products.append(product)
            except Exception as err:
                _LOGGER.warning("Radar %s unavailable at startup, skipping: %s", product, err)

        # Clean up products that are no longer selected
        ent_reg = er.async_get(hass)
        for product in ALL_KNOWN_PRODUCTS:
            if product not in radar_products:
                entity_id = ent_reg.async_get_entity_id(
                    "camera", DOMAIN, f"{DOMAIN}_radar_{product}_{entry.entry_id}"
                )
                if entity_id:
                    ent_reg.async_remove(entity_id)
                    _LOGGER.debug("Removed unused radar entity: %s", entity_id)

        if loaded_products:
            hass.data[DOMAIN][f"{entry.entry_id}_radar"] = True
            platforms.append("camera")
    else:
        _async_cleanup_radar(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to new version."""
    if config_entry.version < 8:
        _LOGGER.debug(
            "Migrating config entry %s from version %s to 8",
            config_entry.entry_id,
            config_entry.version,
        )
        new_data = {**config_entry.data}
        new_data.setdefault(CONF_ENABLE_WEATHER_FORECAST, False)
        new_data.setdefault(CONF_LOCATION_NAME, config_entry.title)
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=8
        )
    if config_entry.version < 9:
        _LOGGER.debug(
            "Migrating config entry %s from version %s to 9",
            config_entry.entry_id,
            config_entry.version,
        )
        new_data = {**config_entry.data}
        new_data.setdefault(CONF_ENABLE_ENHANCED_WARNINGS_METEO, False)
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=9
        )
    if config_entry.version < 10:
        _LOGGER.debug(
            "Migrating config entry %s from version %s to 10",
            config_entry.entry_id,
            config_entry.version,
        )
        new_data = {**config_entry.data}
        new_data.setdefault(CONF_USE_POWIAT_FOR_WARNINGS, False)

        # Detect powiat if not already set
        if not new_data.get(CONF_POWIAT):
            try:
                session = async_get_clientsession(hass)
                lat = new_data.get(CONF_FORECAST_LAT, hass.config.latitude)
                lon = new_data.get(CONF_FORECAST_LON, hass.config.longitude)
                if lat and lon:
                    nominatim_name = await nominatim_reverse_geocode(session, lat, lon)
                    if nominatim_name:
                        location_details = await reverse_geocode(
                            session, lat, lon, [nominatim_name]
                        )
                        if location_details:
                            teryt_code = location_details.get("teryt")
                            district_name = location_details.get("district")
                            if teryt_code and district_name:
                                new_data[CONF_POWIAT] = teryt_code
                                new_data[CONF_POWIAT_NAME] = district_name
                                _LOGGER.debug(
                                    "Migration v10: detected powiat %s (%s)",
                                    district_name,
                                    teryt_code,
                                )
            except Exception as e:
                _LOGGER.debug("Migration v10: powiat detection failed: %s", e)

        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=10
        )
    if config_entry.version < 11:
        _LOGGER.debug(
            "Migrating config entry %s from version %s to 11",
            config_entry.entry_id,
            config_entry.version,
        )
        new_data = {**config_entry.data}
        new_data.setdefault(CONF_ENABLE_RADAR_CAMERA, False)
        new_data.setdefault("radar_type", "none")
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=11
        )
    if config_entry.version < 12:
        _LOGGER.debug(
            "Migrating config entry %s from version %s to 12 (radar_type → radar_products)",
            config_entry.entry_id,
            config_entry.version,
        )
        new_data = {**config_entry.data}
        # Convert old radar_type string to radar_products list
        old_type = new_data.pop("radar_type", "none")
        products = _migrate_radar_type_to_products(old_type)
        new_data[CONF_RADAR_PRODUCTS] = products
        new_data[CONF_ENABLE_RADAR_CAMERA] = len(products) > 0
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=12
        )
    return True


def _migrate_radar_type_to_products(old_type: str) -> list[str]:
    """Convert legacy radar_type string to list of products."""
    MIGRATION_MAP = {
        "none": [],
        "cmax": ["cmax"],
        "sri": ["sri"],
        "pac": ["pac"],
        "natural_color": ["natural_color"],
        "infrared": ["infrared"],
        "water_vapor": ["water_vapor"],
        "cloud_type": ["cloud_type"],
        "oze_pv": ["oze_pv"],
        "oze_wind": ["oze_wind"],
        "oze_pv_anim": ["oze_pv_anim"],
        "oze_wind_anim": ["oze_wind_anim"],
        "both": ["cmax", "sri"],
        "all_radar": ["cmax", "sri", "pac"],
        "all_sat": ["natural_color", "infrared", "water_vapor", "cloud_type"],
        "all_oze": ["oze_pv", "oze_wind", "oze_pv_anim", "oze_wind_anim"],
        "all": ["cmax", "sri", "pac", "natural_color", "infrared", "water_vapor", "cloud_type", "oze_pv", "oze_wind", "oze_pv_anim", "oze_wind_anim"],
    }
    return MIGRATION_MAP.get(old_type, [])


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    platforms = ["sensor"]
    # Check what was actually loaded at runtime (not current config, which may
    # already be updated by the options flow before the reload triggers).
    if f"{entry.entry_id}_binary_sensor" in hass.data.get(DOMAIN, {}):
        platforms.append("binary_sensor")
    if f"{entry.entry_id}_forecast" in hass.data.get(DOMAIN, {}):
        platforms.append("weather")
    if f"{entry.entry_id}_radar" in hass.data.get(DOMAIN, {}):
        platforms.append("camera")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_forecast", None)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_binary_sensor", None)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_radar", None)
        from .camera import ALL_KNOWN_PRODUCTS
        for p in ALL_KNOWN_PRODUCTS:
            hass.data[DOMAIN].pop(f"{entry.entry_id}_radar_{p}", None)

        # Recalculate global coordinator interval based on remaining entries
        global_coord = hass.data[DOMAIN].get("global_coordinator")
        remaining_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        if global_coord and remaining_entries:
            min_interval = min(
                e.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                for e in remaining_entries
            )
            global_coord.update_interval = timedelta(minutes=min_interval)
        elif global_coord and not remaining_entries:
            # Last entry removed — close API sessions and clean up
            await global_coord.api.close()
            hass.data[DOMAIN].pop("global_coordinator", None)

    return unload_ok
