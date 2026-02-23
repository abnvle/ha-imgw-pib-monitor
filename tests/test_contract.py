"""Contract tests — validate that real IMGW APIs return data matching expected schemas.

These tests hit **live endpoints** and verify the JSON structure that the
integration relies on. They do NOT check specific values (which change every
hour) - only that the required keys are present and numeric fields are
parsable.

Run selectively:
    pytest -m contract -v
"""

from __future__ import annotations

import aiohttp
from aiohttp.resolver import ThreadedResolver
import pytest

# ── Constants (duplicated from production code to keep tests self-contained) ──

IMGW_BASE = "https://danepubliczne.imgw.pl/api/data"
IMGW_PROXY = "https://imgw-api-proxy.evtlab.pl"
NOMINATIM = "https://nominatim.openstreetmap.org"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
async def http_session():
    """Provide an aiohttp session using the threaded DNS resolver."""
    connector = aiohttp.TCPConnector(resolver=ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as session:
        yield session


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_numeric_or_none(value) -> bool:
    """Return True if *value* can be parsed as float or is None / empty."""
    if value is None or value == "":
        return True
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


# ── IMGW Public API ──────────────────────────────────────────────────────────

@pytest.mark.contract
class TestImgwPublicApiContract:
    """Verify schemas of the IMGW danepubliczne.imgw.pl endpoints."""

    @pytest.mark.asyncio
    async def test_synop_response_schema(self, http_session):
        """GET /synop returns a list; each item has keys used by _parse_synop."""
        required_keys = {
            "id_stacji",
            "stacja",
            "data_pomiaru",
            "godzina_pomiaru",
            "temperatura",
            "predkosc_wiatru",
            "kierunek_wiatru",
            "wilgotnosc_wzgledna",
            "suma_opadu",
            "cisnienie",
        }
        numeric_keys = {
            "temperatura",
            "predkosc_wiatru",
            "kierunek_wiatru",
            "wilgotnosc_wzgledna",
            "suma_opadu",
            "cisnienie",
        }

        async with http_session.get(
            f"{IMGW_BASE}/synop", timeout=REQUEST_TIMEOUT
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()

        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        assert len(data) > 0, "Synop list is empty"

        for item in data[:5]:  # spot-check first 5 stations
            missing = required_keys - set(item.keys())
            assert not missing, f"Missing keys in synop item: {missing}"

            for key in numeric_keys:
                assert _is_numeric_or_none(item.get(key)), (
                    f"Synop key '{key}' is not numeric: {item.get(key)!r}"
                )

    @pytest.mark.asyncio
    async def test_hydro_response_schema(self, http_session):
        """GET /hydro returns a list; each item has keys used by _parse_hydro."""
        required_keys = {
            "id_stacji",
            "stacja",
            "rzeka",
            "wojewodztwo",
            "stan_wody",
            "stan_wody_data_pomiaru",
        }
        numeric_keys = {"stan_wody", "temperatura_wody", "przelyw", "lat", "lon"}

        async with http_session.get(
            f"{IMGW_BASE}/hydro", timeout=REQUEST_TIMEOUT
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()

        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        assert len(data) > 0, "Hydro list is empty"

        for item in data[:5]:
            missing = required_keys - set(item.keys())
            assert not missing, f"Missing keys in hydro item: {missing}"

            for key in numeric_keys:
                assert _is_numeric_or_none(item.get(key)), (
                    f"Hydro key '{key}' is not numeric: {item.get(key)!r}"
                )

    @pytest.mark.asyncio
    async def test_meteo_response_schema(self, http_session):
        """GET /meteo returns a list; each item has keys used by _parse_meteo."""
        required_keys = {
            "kod_stacji",
            "nazwa_stacji",
        }
        numeric_keys = {
            "lat",
            "lon",
            "temperatura_gruntu",
            "temperatura_powietrza",
            "wiatr_kierunek",
            "wiatr_srednia_predkosc",
            "wiatr_predkosc_maksymalna",
            "wilgotnosc_wzgledna",
            "wiatr_poryw_10min",
            "opad_10min",
        }

        async with http_session.get(
            f"{IMGW_BASE}/meteo", timeout=REQUEST_TIMEOUT
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()

        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        assert len(data) > 0, "Meteo list is empty"

        for item in data[:5]:
            missing = required_keys - set(item.keys())
            assert not missing, f"Missing keys in meteo item: {missing}"

            for key in numeric_keys:
                assert _is_numeric_or_none(item.get(key)), (
                    f"Meteo key '{key}' is not numeric: {item.get(key)!r}"
                )

    @pytest.mark.asyncio
    async def test_warnings_meteo_response_schema(self, http_session):
        """GET /warningsmeteo returns a list (possibly empty).

        When warnings exist, each item must have the keys used by
        _parse_warnings_meteo.
        """
        required_keys = {
            "nazwa_zdarzenia",
            "stopien",
            "prawdopodobienstwo",
            "obowiazuje_od",
            "obowiazuje_do",
            "tresc",
        }

        async with http_session.get(
            f"{IMGW_BASE}/warningsmeteo", timeout=REQUEST_TIMEOUT
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()

        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"

        if len(data) == 0:
            pytest.skip("No active meteorological warnings — schema cannot be verified")

        for item in data[:3]:
            missing = required_keys - set(item.keys())
            assert not missing, f"Missing keys in warnings_meteo item: {missing}"

            # teryt must be a list
            teryt = item.get("teryt")
            assert isinstance(teryt, list), (
                f"Expected 'teryt' to be a list, got {type(teryt).__name__}"
            )

    @pytest.mark.asyncio
    async def test_warnings_hydro_response_schema(self, http_session):
        """GET /warningshydro returns a list (possibly empty).

        When warnings exist, each item must have the keys used by
        _parse_warnings_hydro.
        """
        required_keys = {
            "numer",
            "zdarzenie",
            "prawdopodobienstwo",
            "data_od",
            "data_do",
            "przebieg",
            "obszary",
        }

        async with http_session.get(
            f"{IMGW_BASE}/warningshydro", timeout=REQUEST_TIMEOUT
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()

        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"

        if len(data) == 0:
            pytest.skip("No active hydrological warnings — schema cannot be verified")

        for item in data[:3]:
            missing = required_keys - set(item.keys())
            assert not missing, f"Missing keys in warnings_hydro item: {missing}"

            # obszary must be a list of dicts with 'opis'
            obszary = item.get("obszary")
            assert isinstance(obszary, list), (
                f"Expected 'obszary' to be a list, got {type(obszary).__name__}"
            )
            if obszary:
                assert "opis" in obszary[0], "obszary items must have 'opis' key"

            # level key — API uses 'stopień' (with Polish diacritic) or 'stopien'
            has_level = "stopień" in item or "stopien" in item
            assert has_level, "warnings_hydro item missing both 'stopień' and 'stopien'"


# ── IMGW API Proxy ───────────────────────────────────────────────────────────

@pytest.mark.contract
class TestImgwProxyApiContract:
    """Verify schemas of the IMGW API Proxy (imgw-api-proxy.evtlab.pl)."""

    @pytest.mark.asyncio
    async def test_search_response_schema(self, http_session):
        """GET /search?name=Warszawa returns a list of location results."""
        required_keys = {"name", "lat", "lon", "teryt", "province"}

        async with http_session.get(
            f"{IMGW_PROXY}/search",
            params={"name": "Warszawa"},
            headers={"User-Agent": "HomeAssistant-IMGW-PIB-Monitor/contract-test"},
            timeout=REQUEST_TIMEOUT,
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()

        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        assert len(data) > 0, "Search for 'Warszawa' returned no results"

        for item in data[:3]:
            missing = required_keys - set(item.keys())
            assert not missing, f"Missing keys in search result: {missing}"

            # lat/lon must be parsable as float
            assert _is_numeric_or_none(item.get("lat")), (
                f"Search lat not numeric: {item.get('lat')!r}"
            )
            assert _is_numeric_or_none(item.get("lon")), (
                f"Search lon not numeric: {item.get('lon')!r}"
            )

    @pytest.mark.asyncio
    async def test_forecast_response_schema(self, http_session):
        """GET /forecast?lat=52.23&lon=21.01 returns forecast data.

        The coordinator accepts both ``{"current": ...}`` and
        ``{"data": {"current": ...}}`` — we verify whichever form is returned.
        """
        async with http_session.get(
            f"{IMGW_PROXY}/forecast",
            params={"lat": "52.23", "lon": "21.01"},
            timeout=REQUEST_TIMEOUT,
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()

        assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"

        # Unwrap if needed (coordinator does the same)
        if "data" in data and isinstance(data["data"], dict):
            data = data["data"]

        # current
        assert "current" in data, "Forecast missing 'current' key"
        current = data["current"]
        assert isinstance(current, dict), "'current' should be a dict"
        for key in ("temp", "humidity", "pressure", "wind_speed", "cloud"):
            assert key in current, f"current missing '{key}'"

        # hourly
        assert "hourly" in data, "Forecast missing 'hourly' key"
        hourly = data["hourly"]
        assert isinstance(hourly, list), "'hourly' should be a list"
        if hourly:
            h0 = hourly[0]
            for key in ("date", "temp"):
                assert key in h0, f"hourly[0] missing '{key}'"

        # daily
        assert "daily" in data, "Forecast missing 'daily' key"
        daily = data["daily"]
        assert isinstance(daily, list), "'daily' should be a list"
        if daily:
            d0 = daily[0]
            for key in ("date", "temp_max", "temp_min"):
                assert key in d0, f"daily[0] missing '{key}'"

        # sun
        assert "sun" in data, "Forecast missing 'sun' key"
        sun = data["sun"]
        assert isinstance(sun, dict), "'sun' should be a dict"


# ── Nominatim ────────────────────────────────────────────────────────────────

@pytest.mark.contract
class TestNominatimContract:
    """Verify schema of Nominatim reverse geocode response."""

    @pytest.mark.asyncio
    async def test_reverse_geocode_response_schema(self, http_session):
        """Nominatim reverse geocode for Warsaw center returns address with city."""
        async with http_session.get(
            f"{NOMINATIM}/reverse",
            params={
                "lat": "52.2297",
                "lon": "21.0122",
                "format": "json",
                "accept-language": "pl",
                "zoom": "10",
            },
            headers={"User-Agent": "HomeAssistant-IMGW-PIB-Monitor/contract-test"},
            timeout=REQUEST_TIMEOUT,
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()

        assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"
        assert "error" not in data, f"Nominatim returned error: {data.get('error')}"

        # address block must exist
        assert "address" in data, "Missing 'address' key"
        address = data["address"]
        assert isinstance(address, dict), "'address' should be a dict"

        # At least one of city/town/village must be present
        has_place = any(
            address.get(k) for k in ("city", "town", "village")
        )
        assert has_place, (
            "address has none of 'city', 'town', 'village': "
            f"{list(address.keys())}"
        )
