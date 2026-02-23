"""Utility functions for IMGW-PIB Monitor."""

from __future__ import annotations

import math
from typing import Any

import aiohttp


async def nominatim_reverse_geocode(
    session: aiohttp.ClientSession,
    lat: float,
    lon: float,
) -> str | None:
    """Reverse geocode coordinates to a city/village name using Nominatim.

    Used in autodiscovery mode where only GPS coordinates are available.
    Should be called once during config flow setup.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": str(lat),
        "lon": str(lon),
        "format": "json",
        "accept-language": "pl",
        "zoom": "10",
    }
    headers = {"User-Agent": "HomeAssistant-IMGW-PIB-Monitor/2.0.0"}

    try:
        async with session.get(
            url,
            params=params,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if not data or "error" in data:
                return None

            address = data.get("address", {})
            return (
                address.get("city")
                or address.get("town")
                or address.get("village")
                or data.get("name")
            )
    except (aiohttp.ClientError, ValueError, KeyError):
        return None


async def reverse_geocode(
    session: aiohttp.ClientSession,
    lat: float,
    lon: float,
    search_hints: list[str] | None = None,
) -> dict[str, Any] | None:
    """Reverse geocode coordinates using IMGW API Proxy.

    Searches the IMGW location database using provided search hints
    (typically nearby station names) and returns the closest result
    within 50 km of the given coordinates.

    Args:
        session: aiohttp client session
        lat: Latitude
        lon: Longitude
        search_hints: List of place/station names to use as search terms.
                      Each name is queried; the closest overall result wins.

    Returns:
        Location details dictionary with keys: teryt, province, district,
        commune, name — or None if nothing found within 50 km.
    """
    if not search_hints:
        return None

    url = "https://imgw-api-proxy.evtlab.pl/search"
    headers = {"User-Agent": "HomeAssistant-IMGW-PIB-Monitor/1.1.0"}

    best_location = None
    best_distance = float("inf")

    try:
        for hint in search_hints:
            if not hint:
                continue
            async with session.get(
                url,
                params={"name": hint},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    continue

                data = await resp.json()
                if not data or not isinstance(data, list):
                    continue

                for location in data:
                    try:
                        loc_lat = float(location.get("lat", 0))
                        loc_lon = float(location.get("lon", 0))
                        if not loc_lat or not loc_lon:
                            continue

                        dist = haversine(lat, lon, loc_lat, loc_lon)
                        if dist < best_distance and dist < 50:
                            best_distance = dist
                            best_location = location
                    except (ValueError, TypeError):
                        continue

        if best_location:
            return {
                "teryt": best_location.get("teryt"),
                "province": best_location.get("province"),
                "district": best_location.get("district"),
                "commune": best_location.get("commune"),
                "name": best_location.get("name"),
                "synoptic": best_location.get("synoptic", False),
            }

    except (aiohttp.ClientError, ValueError, KeyError):
        pass

    return None


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance between two points in km."""
    r_earth = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r_earth * c

async def geocode_location(
    session: aiohttp.ClientSession, location_name: str, limit: int = 50
) -> list[tuple[float, float, dict[str, Any], str]] | None:
    """Geocode a location name to coordinates using IMGW API Proxy.

    Args:
        session: aiohttp client session
        location_name: Name of the location (city, town, address)
        limit: Maximum number of results to return

    Returns:
        List of tuples (latitude, longitude, location_details, display_name) or None if not found
        location_details contains: teryt, province, district, commune, name, synoptic
    """
    url = "https://imgw-api-proxy.evtlab.pl/search"
    params = {
        "name": location_name,
    }
    headers = {
        "User-Agent": "HomeAssistant-IMGW-PIB-Monitor/1.1.0",
    }

    try:
        async with session.get(
            url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                return None

            # Sort results by rank (higher is better) and take top results
            sorted_data = sorted(data, key=lambda x: int(x.get("rank", 0)), reverse=True)

            results = []
            for result in sorted_data[:limit]:
                try:
                    lat = float(result.get("lat", 0))
                    lon = float(result.get("lon", 0))

                    if not lat or not lon:
                        continue

                    # Build location details dictionary
                    location_details = {
                        "teryt": result.get("teryt"),
                        "province": result.get("province"),
                        "district": result.get("district"),
                        "commune": result.get("commune"),
                        "name": result.get("name"),
                        "synoptic": result.get("synoptic", False),
                        "rank": result.get("rank"),
                    }

                    # Build display name from identifier or construct it
                    display_name = result.get("identifier", "")
                    if not display_name:
                        parts = [result.get("name", "")]
                        if result.get("commune"):
                            parts.append(f"gm. {result['commune']}")
                        if result.get("district"):
                            parts.append(result["district"])
                        if result.get("province"):
                            parts.append(result["province"])
                        display_name = ", ".join(filter(None, parts))

                    results.append((lat, lon, location_details, display_name))

                except (ValueError, TypeError, KeyError):
                    continue

            return results if results else None

    except (aiohttp.ClientError, ValueError, KeyError):
        pass

    return None
