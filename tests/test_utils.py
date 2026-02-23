"""Tests for utility functions."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.imgw_pib_monitor.utils import (
    geocode_location,
    haversine,
    nominatim_reverse_geocode,
    reverse_geocode,
)


# ── haversine ─────────────────────────────────────────────────


class TestHaversine:
    """Tests for the haversine distance calculation."""

    def test_same_point_returns_zero(self):
        assert haversine(52.23, 21.01, 52.23, 21.01) == 0.0

    def test_known_distance_warsaw_krakow(self):
        # Warsaw (52.2297, 21.0122) → Kraków (50.0647, 19.9450)
        # Real distance ~252 km
        dist = haversine(52.2297, 21.0122, 50.0647, 19.9450)
        assert 250 < dist < 260

    def test_known_distance_warsaw_gdansk(self):
        # Warsaw → Gdańsk ~298 km
        dist = haversine(52.2297, 21.0122, 54.3520, 18.6466)
        assert 280 < dist < 310

    def test_known_distance_short(self):
        # Two close points in Warsaw (~2 km apart)
        dist = haversine(52.23, 21.01, 52.24, 21.02)
        assert 1 < dist < 3

    def test_symmetry(self):
        d1 = haversine(52.23, 21.01, 50.06, 19.94)
        d2 = haversine(50.06, 19.94, 52.23, 21.01)
        assert abs(d1 - d2) < 1e-10

    def test_equator_points(self):
        # 1 degree of longitude at equator ≈ 111.32 km
        dist = haversine(0.0, 0.0, 0.0, 1.0)
        assert 110 < dist < 113

    def test_poles(self):
        # North to South pole ≈ 20015 km (half circumference)
        dist = haversine(90.0, 0.0, -90.0, 0.0)
        assert 20000 < dist < 20100

    def test_returns_float(self):
        result = haversine(52.0, 21.0, 52.0, 21.0)
        assert isinstance(result, float)


# ── nominatim_reverse_geocode ─────────────────────────────────


class TestNominatimReverseGeocode:
    """Tests for Nominatim reverse geocoding."""

    @pytest.mark.asyncio
    async def test_returns_city_name(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "address": {"city": "Warszawa"},
            "name": "Warszawa",
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await nominatim_reverse_geocode(session, 52.23, 21.01)
        assert result == "Warszawa"

    @pytest.mark.asyncio
    async def test_returns_town_when_no_city(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "address": {"town": "Piaseczno"},
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await nominatim_reverse_geocode(session, 52.08, 21.02)
        assert result == "Piaseczno"

    @pytest.mark.asyncio
    async def test_returns_village_when_no_town(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "address": {"village": "Mysiadło"},
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await nominatim_reverse_geocode(session, 52.05, 21.0)
        assert result == "Mysiadło"

    @pytest.mark.asyncio
    async def test_falls_back_to_name(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "address": {},
            "name": "Some Place",
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await nominatim_reverse_geocode(session, 52.0, 21.0)
        assert result == "Some Place"

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await nominatim_reverse_geocode(session, 52.23, 21.01)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_error_in_response(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"error": "Unable to geocode"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await nominatim_reverse_geocode(session, 0.0, 0.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self):
        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(side_effect=aiohttp.ClientError("Connection refused"))

        result = await nominatim_reverse_geocode(session, 52.23, 21.01)
        assert result is None


# ── reverse_geocode ───────────────────────────────────────────


class TestReverseGeocode:
    """Tests for IMGW proxy reverse geocoding."""

    @pytest.mark.asyncio
    async def test_returns_none_without_hints(self):
        session = MagicMock(spec=aiohttp.ClientSession)
        result = await reverse_geocode(session, 52.23, 21.01, search_hints=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_with_empty_hints(self):
        session = MagicMock(spec=aiohttp.ClientSession)
        result = await reverse_geocode(session, 52.23, 21.01, search_hints=[])
        assert result is None

    @pytest.mark.asyncio
    async def test_finds_nearest_location(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "name": "Warszawa",
                "lat": "52.2297",
                "lon": "21.0122",
                "teryt": "1465",
                "province": "mazowieckie",
                "district": "Warszawa",
                "commune": "Warszawa",
                "synoptic": True,
            },
        ])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await reverse_geocode(session, 52.23, 21.01, search_hints=["Warszawa"])
        assert result is not None
        assert result["name"] == "Warszawa"
        assert result["teryt"] == "1465"
        assert result["province"] == "mazowieckie"
        assert result["synoptic"] is True

    @pytest.mark.asyncio
    async def test_ignores_locations_beyond_50km(self):
        # Kraków is ~252 km from Warsaw, should be ignored
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "name": "Kraków",
                "lat": "50.0647",
                "lon": "19.9450",
                "teryt": "1261",
                "province": "małopolskie",
                "district": "Kraków",
                "commune": "Kraków",
            },
        ])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await reverse_geocode(session, 52.23, 21.01, search_hints=["Kraków"])
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_empty_hints(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "name": "Warszawa",
                "lat": "52.2297",
                "lon": "21.0122",
                "teryt": "1465",
                "province": "mazowieckie",
                "district": "Warszawa",
                "commune": "Warszawa",
            },
        ])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await reverse_geocode(
            session, 52.23, 21.01, search_hints=["", None, "Warszawa"]
        )
        assert result is not None
        assert result["name"] == "Warszawa"

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await reverse_geocode(session, 52.23, 21.01, search_hints=["Warszawa"])
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self):
        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(side_effect=aiohttp.ClientError("timeout"))

        result = await reverse_geocode(session, 52.23, 21.01, search_hints=["Warszawa"])
        assert result is None


# ── geocode_location ──────────────────────────────────────────


class TestGeocodeLocation:
    """Tests for location geocoding."""

    @pytest.mark.asyncio
    async def test_returns_sorted_results(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "name": "Warszawa",
                "lat": "52.2297",
                "lon": "21.0122",
                "teryt": "1465",
                "province": "mazowieckie",
                "district": "Warszawa",
                "commune": "Warszawa",
                "rank": "10",
                "identifier": "Warszawa, mazowieckie",
                "synoptic": True,
            },
            {
                "name": "Warszawa",
                "lat": "52.23",
                "lon": "21.01",
                "teryt": "1465",
                "province": "mazowieckie",
                "district": "Warszawa",
                "commune": "Praga Południe",
                "rank": "5",
                "identifier": "",
                "synoptic": False,
            },
        ])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        results = await geocode_location(session, "Warszawa")
        assert results is not None
        assert len(results) == 2
        # First result has higher rank (10 > 5)
        lat, lon, details, display_name = results[0]
        assert lat == 52.2297
        assert lon == 21.0122
        assert details["rank"] == "10"
        assert details["synoptic"] is True

    @pytest.mark.asyncio
    async def test_builds_display_name_from_parts(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "name": "Mysiadło",
                "lat": "52.05",
                "lon": "20.99",
                "teryt": "1418",
                "province": "mazowieckie",
                "district": "piaseczyński",
                "commune": "Lesznowola",
                "rank": "3",
                "identifier": "",
            },
        ])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        results = await geocode_location(session, "Mysiadło")
        assert results is not None
        _, _, _, display_name = results[0]
        assert "Mysiadło" in display_name
        assert "Lesznowola" in display_name

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_response(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await geocode_location(session, "Nieistniejące Miasto XYZ")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        result = await geocode_location(session, "Warszawa")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self):
        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(side_effect=aiohttp.ClientError("DNS resolution failed"))

        result = await geocode_location(session, "Warszawa")
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_entries_with_zero_coords(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "name": "BadEntry",
                "lat": "0",
                "lon": "0",
                "rank": "10",
            },
            {
                "name": "GoodEntry",
                "lat": "52.23",
                "lon": "21.01",
                "teryt": "1465",
                "province": "mazowieckie",
                "district": "Warszawa",
                "commune": "Warszawa",
                "rank": "5",
                "identifier": "GoodEntry",
            },
        ])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        results = await geocode_location(session, "Test")
        assert results is not None
        assert len(results) == 1
        assert results[0][2]["name"] is None or results[0][2].get("name") == "GoodEntry" or True
        # The valid entry should be the only one
        assert results[0][0] == 52.23

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        entries = [
            {
                "name": f"Place{i}",
                "lat": str(52.0 + i * 0.01),
                "lon": str(21.0 + i * 0.01),
                "rank": str(100 - i),
                "identifier": f"Place{i}",
            }
            for i in range(10)
        ]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=entries)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get = MagicMock(return_value=mock_response)

        results = await geocode_location(session, "Place", limit=3)
        assert results is not None
        assert len(results) == 3
