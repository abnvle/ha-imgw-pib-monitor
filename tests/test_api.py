"""Tests for the IMGW API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.imgw_pib_monitor.api import (
    ImgwApiClient,
    ImgwApiConnectionError,
    ImgwApiError,
)

from .conftest import SAMPLE_HYDRO_DATA, SAMPLE_SYNOP_DATA, SAMPLE_METEO_DATA


def _make_mock_session(response_data, status=200):
    """Create a mock aiohttp session with a given response."""
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=response_data)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.get = MagicMock(return_value=mock_response)
    return session


class TestImgwApiClientFetch:
    """Tests for the low-level _fetch method."""

    @pytest.mark.asyncio
    async def test_raises_on_non_200(self):
        session = _make_mock_session({}, status=500)
        client = ImgwApiClient(session)

        with pytest.raises(ImgwApiError, match="status 500"):
            await client._fetch("https://example.com/api")

    @pytest.mark.asyncio
    async def test_raises_connection_error_on_client_error(self):
        session = MagicMock(spec=aiohttp.ClientSession)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("timeout"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        session.get = MagicMock(return_value=mock_cm)

        client = ImgwApiClient(session)
        with pytest.raises(ImgwApiConnectionError, match="Connection error"):
            await client._fetch("https://example.com/api")


class TestImgwApiClientSynop:
    """Tests for synoptic data methods."""

    @pytest.mark.asyncio
    async def test_get_all_synop_data(self):
        session = _make_mock_session(SAMPLE_SYNOP_DATA)
        client = ImgwApiClient(session)

        result = await client.get_all_synop_data()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["stacja"] == "Warszawa"

    @pytest.mark.asyncio
    async def test_get_all_synop_data_returns_empty_on_dict(self):
        """If API returns a dict instead of list, return empty list."""
        session = _make_mock_session({"error": "not found"})
        client = ImgwApiClient(session)

        result = await client.get_all_synop_data()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_synop_stations(self):
        session = _make_mock_session(SAMPLE_SYNOP_DATA)
        client = ImgwApiClient(session)

        result = await client.get_synop_stations()
        assert isinstance(result, dict)
        assert result["12375"] == "Warszawa"
        assert result["12566"] == "Kraków"


class TestImgwApiClientHydro:
    """Tests for hydrological data methods."""

    @pytest.mark.asyncio
    async def test_get_all_hydro_data(self):
        session = _make_mock_session(SAMPLE_HYDRO_DATA)
        client = ImgwApiClient(session)

        result = await client.get_all_hydro_data()
        assert len(result) == 1
        assert result[0]["stacja"] == "Warszawa"

    @pytest.mark.asyncio
    async def test_get_hydro_stations_includes_river(self):
        session = _make_mock_session(SAMPLE_HYDRO_DATA)
        client = ImgwApiClient(session)

        result = await client.get_hydro_stations()
        assert "150190370" in result
        assert "Wisła" in result["150190370"]
        assert "Warszawa" in result["150190370"]


class TestImgwApiClientMeteo:
    """Tests for meteorological data methods."""

    @pytest.mark.asyncio
    async def test_get_all_meteo_data(self):
        session = _make_mock_session(SAMPLE_METEO_DATA)
        client = ImgwApiClient(session)

        result = await client.get_all_meteo_data()
        assert len(result) == 1
        assert result[0]["nazwa_stacji"] == "Warszawa"

    @pytest.mark.asyncio
    async def test_get_meteo_stations(self):
        session = _make_mock_session(SAMPLE_METEO_DATA)
        client = ImgwApiClient(session)

        result = await client.get_meteo_stations()
        assert result["249200080"] == "Warszawa"


class TestImgwApiClientWarnings:
    """Tests for warning data methods."""

    @pytest.mark.asyncio
    async def test_get_warnings_meteo(self):
        session = _make_mock_session([{"test": "data"}])
        client = ImgwApiClient(session)

        result = await client.get_warnings_meteo()
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_warnings_hydro(self):
        session = _make_mock_session([{"test": "data"}])
        client = ImgwApiClient(session)

        result = await client.get_warnings_hydro()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_warnings_returns_empty_on_dict_response(self):
        session = _make_mock_session({"status": "no warnings"})
        client = ImgwApiClient(session)

        result = await client.get_warnings_meteo()
        assert result == []
