"""Utility functions for IMGW-PIB Monitor."""

from __future__ import annotations

import math
from typing import Any

import aiohttp


async def reverse_geocode(
    session: aiohttp.ClientSession, lat: float, lon: float, voivodeship_capitals: dict[str, tuple[float, float]] | None = None
) -> dict[str, Any] | None:
    """Reverse geocode coordinates using IMGW API Proxy.

    Args:
        session: aiohttp client session
        lat: Latitude
        lon: Longitude
        voivodeship_capitals: Dictionary of voivodeship codes to (lat, lon) tuples

    Returns:
        Location details dictionary with keys: teryt, province, district, commune, name
        or None if not found
    """
    # Find nearest voivodeship capital to narrow down search
    search_query = ""
    if voivodeship_capitals:
        min_dist = float("inf")
        for capital_lat, capital_lon in voivodeship_capitals.values():
            dist = haversine(lat, lon, capital_lat, capital_lon)
            if dist < min_dist:
                min_dist = dist

    # Try searching with empty query to get broad results
    # The API returns locations sorted by rank, we'll find the nearest one
    url = "https://imgw-api-proxy.evtlab.pl/search"
    params = {
        "name": "",  # Empty search to get many results
    }
    headers = {
        "User-Agent": "HomeAssistant-IMGW-PIB-Monitor/1.1.0",
    }

    try:
        # If empty search doesn't work, we'll try a few common city names
        search_attempts = ["", "Warszawa", "Kraków", "Poznań"]

        for attempt in search_attempts:
            params["name"] = attempt
            async with session.get(
                url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    continue

                data = await resp.json()
                if not data or not isinstance(data, list) or len(data) == 0:
                    continue

                # Find the closest location
                closest_location = None
                min_distance = float("inf")

                for location in data:
                    try:
                        loc_lat = float(location.get("lat", 0))
                        loc_lon = float(location.get("lon", 0))

                        if not loc_lat or not loc_lon:
                            continue

                        dist = haversine(lat, lon, loc_lat, loc_lon)

                        # Only consider locations within 50km
                        if dist < min_distance and dist < 50:
                            min_distance = dist
                            closest_location = location

                    except (ValueError, TypeError):
                        continue

                if closest_location:
                    # Return location details in the same format as geocode_location
                    return {
                        "teryt": closest_location.get("teryt"),
                        "province": closest_location.get("province"),
                        "district": closest_location.get("district"),
                        "commune": closest_location.get("commune"),
                        "name": closest_location.get("name"),
                        "synoptic": closest_location.get("synoptic", False),
                    }

        return None

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
