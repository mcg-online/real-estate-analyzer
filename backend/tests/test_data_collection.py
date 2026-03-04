"""Tests for ZillowScraper and DataCollectionService.

All HTTP I/O is mocked: no real network calls are made during this suite.
Async tests use pytest-asyncio via asyncio.run() wrappers so the suite stays
compatible with a plain pytest invocation (no asyncio mode configuration
required).
"""

from __future__ import annotations

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers shared across both test classes
# ---------------------------------------------------------------------------

def _minimal_html(num_listings: int = 2) -> str:
    """Return an HTML snippet containing ``num_listings`` Zillow-style cards."""
    cards = ""
    for i in range(num_listings):
        cards += (
            f'<article class="list-card">'
            f'<a class="list-card-link" href="https://www.zillow.com/homedetails/{i}/">'
            f"Property {i}"
            f"</a></article>"
        )
    return f"<html><body>{cards}</body></html>"


def _minimal_detail_html(
    address: str = "123 Main St",
    price: str = "350000",
    beds: str = "3 bd",
    baths: str = "2 ba",
    sqft: str = "1500 sqft",
) -> str:
    """Return a minimal detail-page HTML snippet."""
    return f"""
    <html><body>
      <div class="ds-address-container">{address}</div>
      <span data-testid="price">${price}</span>
      <div data-testid="bed-bath-beyond">
        <span>{beds}</span>
        <span>{baths}</span>
        <span>{sqft}</span>
      </div>
    </body></html>
    """


# ---------------------------------------------------------------------------
# ZillowScraper tests
# ---------------------------------------------------------------------------

class TestZillowScraperGetHeaders:
    """Unit tests for ZillowScraper._get_headers()."""

    def setup_method(self):
        from services.data_collection.zillow_scraper import ZillowScraper
        self.scraper = ZillowScraper()

    def test_returns_dict_with_user_agent(self):
        headers = self.scraper._get_headers()
        assert isinstance(headers, dict)
        assert "User-Agent" in headers

    def test_user_agent_is_one_of_known_agents(self):
        headers = self.scraper._get_headers()
        assert headers["User-Agent"] in self.scraper.user_agents

    def test_user_agent_rotation_across_calls(self):
        """With enough calls at least two distinct user-agents should appear."""
        seen: set[str] = set()
        for _ in range(50):
            seen.add(self.scraper._get_headers()["User-Agent"])
            if len(seen) > 1:
                break
        assert len(seen) > 1, (
            "Expected multiple distinct user-agents across 50 calls; got only one."
        )

    def test_contains_required_fields(self):
        headers = self.scraper._get_headers()
        for field in ("Accept-Language", "Accept-Encoding", "Connection"):
            assert field in headers, f"Missing header field: {field}"


class TestZillowScraperGetSearchUrl:
    """Unit tests for ZillowScraper._get_search_url()."""

    def setup_method(self):
        from services.data_collection.zillow_scraper import ZillowScraper
        self.scraper = ZillowScraper()

    def test_page_one_url_has_no_page_number(self):
        url = self.scraper._get_search_url("Seattle", "WA", page=1)
        assert "for_sale/" in url
        assert "_p/" not in url

    def test_page_two_url_contains_page_suffix(self):
        url = self.scraper._get_search_url("Seattle", "WA", page=2)
        assert "2_p/" in url

    def test_city_state_slugified(self):
        url = self.scraper._get_search_url("San Francisco", "CA", page=1)
        assert "san-francisco-ca" in url

    def test_base_url_is_zillow(self):
        url = self.scraper._get_search_url("Seattle", "WA", page=1)
        assert url.startswith("https://www.zillow.com")


class TestZillowScraperExtractListings:
    """Unit tests for ZillowScraper._extract_listings_from_page()."""

    def setup_method(self):
        from services.data_collection.zillow_scraper import ZillowScraper
        from bs4 import BeautifulSoup
        self.scraper = ZillowScraper()
        self.BeautifulSoup = BeautifulSoup

    def test_returns_list(self):
        soup = self.BeautifulSoup("<html></html>", "html.parser")
        result = self.scraper._extract_listings_from_page(soup)
        assert isinstance(result, list)

    def test_extracts_correct_count(self):
        html = _minimal_html(num_listings=3)
        soup = self.BeautifulSoup(html, "html.parser")
        listings = self.scraper._extract_listings_from_page(soup)
        assert len(listings) == 3

    def test_each_listing_has_url_key(self):
        html = _minimal_html(num_listings=2)
        soup = self.BeautifulSoup(html, "html.parser")
        for listing in self.scraper._extract_listings_from_page(soup):
            assert "url" in listing

    def test_urls_start_with_https(self):
        html = _minimal_html(num_listings=2)
        soup = self.BeautifulSoup(html, "html.parser")
        for listing in self.scraper._extract_listings_from_page(soup):
            assert listing["url"].startswith("https://")

    def test_empty_page_returns_empty_list(self):
        soup = self.BeautifulSoup("<html><body></body></html>", "html.parser")
        assert self.scraper._extract_listings_from_page(soup) == []


class TestZillowScraperParsePropertyDetails:
    """Unit tests for ZillowScraper._parse_property_details()."""

    def setup_method(self):
        from services.data_collection.zillow_scraper import ZillowScraper
        self.scraper = ZillowScraper()

    def test_returns_dict_on_success(self):

        html = _minimal_detail_html()
        mock_response = MagicMock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = self.scraper._parse_property_details(
                "https://www.zillow.com/homedetails/1/"
            )

        assert isinstance(result, dict)

    def test_result_contains_required_keys(self):

        html = _minimal_detail_html()
        mock_response = MagicMock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = self.scraper._parse_property_details(
                "https://www.zillow.com/homedetails/1/"
            )

        required = {"address", "price", "bedrooms", "bathrooms", "sqft", "source"}
        assert required.issubset(result.keys())

    def test_source_is_zillow(self):

        html = _minimal_detail_html()
        mock_response = MagicMock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = self.scraper._parse_property_details(
                "https://www.zillow.com/homedetails/1/"
            )

        assert result["source"] == "Zillow"

    def test_returns_none_on_network_error(self):
        import requests

        with patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("timeout"),
        ):
            result = self.scraper._parse_property_details(
                "https://www.zillow.com/homedetails/bad/"
            )

        assert result is None

    def test_returns_none_on_http_error(self):
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("404")
        )

        with patch("requests.get", return_value=mock_response):
            result = self.scraper._parse_property_details(
                "https://www.zillow.com/homedetails/missing/"
            )

        assert result is None


class TestZillowScraperFetchPage:
    """Unit tests for ZillowScraper._fetch_page() async method."""

    def setup_method(self):
        from services.data_collection.zillow_scraper import ZillowScraper
        self.scraper = ZillowScraper()

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_returns_text_on_200(self):
        """_fetch_page should return the response body as a string."""
        mock_response = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>ok</html>")

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        # Patch asyncio.sleep to skip the rate-limit delay
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = self._run(
                self.scraper._fetch_page(
                    mock_session, "https://www.zillow.com/homes/seattle-wa/for_sale/"
                )
            )

        assert result == "<html>ok</html>"

    def test_returns_none_on_non_200(self):
        """Non-200 status code should yield None (no retry exhaustion needed)."""
        mock_response = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        mock_response.status = 403
        mock_response.text = AsyncMock(return_value="Forbidden")

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = self._run(
                self.scraper._fetch_page(
                    mock_session, "https://www.zillow.com/homes/seattle-wa/for_sale/"
                )
            )

        assert result is None


class TestZillowScraperSearchProperties:
    """Integration-style unit tests for ZillowScraper.search_properties()."""

    def setup_method(self):
        from services.data_collection.zillow_scraper import ZillowScraper
        self.scraper = ZillowScraper()

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_returns_list(self):
        """search_properties always returns a list."""
        with (
            patch.object(self.scraper, "_fetch_page", new_callable=AsyncMock, return_value=None),
            patch("aiohttp.ClientSession") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            result = self._run(
                self.scraper.search_properties("Seattle", "WA", max_pages=1)
            )

        assert isinstance(result, list)

    def test_returns_empty_list_when_all_pages_fail(self):
        """All None page content should produce an empty list."""
        with (
            patch.object(self.scraper, "_fetch_page", new_callable=AsyncMock, return_value=None),
            patch("aiohttp.ClientSession") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            result = self._run(
                self.scraper.search_properties("Detroit", "MI", max_pages=2)
            )

        assert result == []

    def test_properties_created_from_parsed_data(self):
        """When parse succeeds, Property objects are created and returned."""
        from models.property import Property

        search_html = _minimal_html(num_listings=1)
        detail_html = _minimal_detail_html(price="400000")


        mock_req_response = MagicMock()
        mock_req_response.content = detail_html.encode()
        mock_req_response.raise_for_status = MagicMock()

        with (
            patch.object(
                self.scraper, "_fetch_page", new_callable=AsyncMock, return_value=search_html
            ),
            patch("aiohttp.ClientSession") as mock_session_cls,
            patch("requests.get", return_value=mock_req_response),
        ):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            result = self._run(
                self.scraper.search_properties("Seattle", "WA", max_pages=1)
            )

        assert len(result) == 1
        assert isinstance(result[0], Property)

    def test_skips_listings_with_parse_failure(self):
        """Listings whose detail page fails to parse should be silently skipped."""
        import requests

        search_html = _minimal_html(num_listings=2)

        with (
            patch.object(
                self.scraper, "_fetch_page", new_callable=AsyncMock, return_value=search_html
            ),
            patch("aiohttp.ClientSession") as mock_session_cls,
            patch(
                "requests.get",
                side_effect=requests.exceptions.ConnectionError("down"),
            ),
        ):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            result = self._run(
                self.scraper.search_properties("Seattle", "WA", max_pages=1)
            )

        assert result == []


# ---------------------------------------------------------------------------
# DataCollectionService tests
# ---------------------------------------------------------------------------

class TestDataCollectionServiceCollectProperties:
    """Tests for DataCollectionService.collect_properties()."""

    def setup_method(self):
        from services.data_collection.data_collection_service import DataCollectionService
        self.service = DataCollectionService()

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_raises_on_missing_city(self):
        from services.data_collection.data_collection_service import DataCollectionError

        with pytest.raises(DataCollectionError, match="city"):
            self._run(self.service.collect_properties({"state": "WA"}))

    def test_raises_on_missing_state(self):
        from services.data_collection.data_collection_service import DataCollectionError

        with pytest.raises(DataCollectionError, match="state"):
            self._run(self.service.collect_properties({"city": "Seattle"}))

    def test_raises_on_empty_params(self):
        from services.data_collection.data_collection_service import DataCollectionError

        with pytest.raises(DataCollectionError):
            self._run(self.service.collect_properties({}))

    def test_delegates_to_scraper(self):
        """collect_properties should call scraper.search_properties with the right args."""
        mock_props = [MagicMock(), MagicMock()]

        with patch.object(
            self.service.scraper,
            "search_properties",
            new_callable=AsyncMock,
            return_value=mock_props,
        ) as mock_search:
            result = self._run(
                self.service.collect_properties(
                    {"city": "Portland", "state": "OR", "max_pages": 2}
                )
            )

        mock_search.assert_called_once_with(city="Portland", state="OR", max_pages=2)
        assert result == mock_props

    def test_defaults_max_pages_to_3(self):
        """When max_pages is not in search_params, default of 3 is used."""
        with patch.object(
            self.service.scraper,
            "search_properties",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_search:
            self._run(
                self.service.collect_properties({"city": "Seattle", "state": "WA"})
            )

        _, kwargs = mock_search.call_args
        assert kwargs["max_pages"] == 3

    def test_returns_empty_list_on_scraper_exception(self):
        """If the scraper raises an unexpected error, an empty list is returned."""
        with patch.object(
            self.service.scraper,
            "search_properties",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected"),
        ):
            result = self._run(
                self.service.collect_properties({"city": "Boston", "state": "MA"})
            )

        assert result == []

    def test_returns_list_type(self):
        with patch.object(
            self.service.scraper,
            "search_properties",
            new_callable=AsyncMock,
            return_value=[MagicMock()],
        ):
            result = self._run(
                self.service.collect_properties({"city": "Austin", "state": "TX"})
            )

        assert isinstance(result, list)


class TestDataCollectionServiceCollectFromAllSources:
    """Tests for DataCollectionService.collect_from_all_sources()."""

    def setup_method(self):
        from services.data_collection.data_collection_service import DataCollectionService
        self.service = DataCollectionService()

    def test_returns_list_synchronously(self):
        mock_props = [MagicMock()]

        with patch.object(
            self.service.scraper,
            "search_properties",
            new_callable=AsyncMock,
            return_value=mock_props,
        ):
            result = self.service.collect_from_all_sources(
                {"city": "Seattle", "state": "WA"}
            )

        assert isinstance(result, list)
        assert result == mock_props

    def test_propagates_data_collection_error(self):
        """Missing city/state should propagate DataCollectionError, not be swallowed."""
        from services.data_collection.data_collection_service import DataCollectionError

        with pytest.raises(DataCollectionError):
            self.service.collect_from_all_sources({"city": "Seattle"})

    def test_handles_scraper_error_gracefully(self):
        """Unexpected scraper exceptions should be converted to empty list."""
        with patch.object(
            self.service.scraper,
            "search_properties",
            new_callable=AsyncMock,
            side_effect=ValueError("bad data"),
        ):
            result = self.service.collect_from_all_sources(
                {"city": "Miami", "state": "FL"}
            )

        assert result == []
