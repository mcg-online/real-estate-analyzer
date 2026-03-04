"""Zillow property scraper with circuit breaker protection.

Design notes
------------
- HTTP is performed with the ``requests`` library for all detail-page fetches.
- Search-page fetching uses ``aiohttp`` for concurrent page retrieval (existing
  async interface is preserved so that callers and tests that rely on the async
  API continue to work without modification).
- The circuit breaker wraps every outbound HTTP call.  After five consecutive
  failures the circuit opens and new requests are rejected immediately, giving
  Zillow time to recover.  The circuit automatically transitions to HALF_OPEN
  after the configured recovery timeout (default 5 minutes) and will close
  again on the first successful probe request.
- Rate-limiting delays are applied before each page fetch to avoid triggering
  Zillow's bot-detection.
- Random user-agent rotation is preserved on every request.
"""

from __future__ import annotations

import asyncio
import logging
import random

import aiohttp
import backoff
import requests
from bs4 import BeautifulSoup

from models.property import Property
from utils.circuit_breaker import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)


class ZillowScraper:
    """Scrapes property listings from Zillow.

    The scraper maintains one shared :class:`~utils.circuit_breaker.CircuitBreaker`
    instance so that repeated failures on either search pages or detail pages
    are counted against the same threshold.

    Parameters
    ----------
    failure_threshold:
        Consecutive failures required to open the circuit.  Defaults to 5.
    recovery_timeout:
        Seconds the circuit stays OPEN before moving to HALF_OPEN.
        Defaults to 300 (5 minutes).
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,
    ) -> None:
        self.base_url = "https://www.zillow.com"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        ]
        self._circuit_breaker: CircuitBreaker = CircuitBreaker(
            name="zillow",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=(
                requests.RequestException,
                aiohttp.ClientError,
                asyncio.TimeoutError,
                OSError,
            ),
        )

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def _get_headers(self) -> dict:
        """Return HTTP headers with a randomly selected user-agent string."""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    # ------------------------------------------------------------------
    # URL construction
    # ------------------------------------------------------------------

    def _get_search_url(self, city: str, state: str, page: int = 1) -> str:
        """Build a Zillow for-sale search URL for the given city/state/page."""
        city_state = f"{city}-{state}".lower().replace(" ", "-")
        if page == 1:
            return f"{self.base_url}/homes/{city_state}/for_sale/"
        return f"{self.base_url}/homes/{city_state}/for_sale/{page}_p/"

    # ------------------------------------------------------------------
    # Async page fetch (used by search_properties)
    # ------------------------------------------------------------------

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
    )
    async def _fetch_page(self, session: aiohttp.ClientSession, url: str) -> str | None:
        """Fetch a single search-results page, applying rate-limiting and retries.

        Parameters
        ----------
        session:
            An active :class:`aiohttp.ClientSession`.
        url:
            The URL to fetch.

        Returns
        -------
        str or None
            The response body as text, or *None* if the response status is not
            200 or the circuit breaker is open.
        """
        # Rate-limiting delay before every request.
        await asyncio.sleep(random.uniform(1.5, 3.5))

        headers = self._get_headers()

        # Wrap the actual I/O in the circuit breaker.  Because aiohttp is
        # async we cannot call ``self._circuit_breaker.call()`` directly (it
        # expects a synchronous callable).  Instead we perform the call inside
        # a try/except that mirrors what the circuit breaker does, then
        # delegate failure recording to the breaker's internal helpers.
        if self._circuit_breaker.state.value == "OPEN":
            logger.warning(
                "ZillowScraper: circuit is OPEN; skipping fetch for %s", url
            )
            return None

        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    logger.warning(
                        "Non-200 status %d for %s", response.status, url
                    )
                    # A non-200 is not a hard network failure; don't count it
                    # against the circuit breaker.
                    return None
                text = await response.text()
                # Successful response: reset the failure counter.
                self._circuit_breaker._on_success()
                return text
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
            logger.error("Network error fetching %s: %s", url, exc)
            self._circuit_breaker._on_failure()
            raise

    # ------------------------------------------------------------------
    # Listing extraction
    # ------------------------------------------------------------------

    def _extract_listings_from_page(self, soup: BeautifulSoup) -> list[dict]:
        """Extract listing URLs from a parsed search-results page.

        Parameters
        ----------
        soup:
            A :class:`bs4.BeautifulSoup` object representing the page DOM.

        Returns
        -------
        list[dict]
            Each element is a dict with a single ``"url"`` key.
        """
        listings: list[dict] = []
        property_cards = soup.select("article.list-card")
        for card in property_cards:
            url_elem = card.select_one("a.list-card-link")
            if url_elem and url_elem.get("href", "").startswith("http"):
                listings.append({"url": url_elem["href"]})
        return listings

    # ------------------------------------------------------------------
    # Detail-page parsing (synchronous, uses requests)
    # ------------------------------------------------------------------

    def _parse_property_details(self, property_url: str) -> dict | None:
        """Fetch and parse a Zillow property detail page.

        Uses the synchronous ``requests`` library so it can be called directly
        from both async and sync contexts without event-loop management.  The
        call is protected by the shared circuit breaker.

        Parameters
        ----------
        property_url:
            The full URL of the Zillow property detail page.

        Returns
        -------
        dict or None
            A property data dictionary on success, or *None* on network or
            parsing errors.
        """
        # Respect the circuit breaker before making the network call.
        if self._circuit_breaker.state.value == "OPEN":
            logger.warning(
                "ZillowScraper: circuit is OPEN; skipping detail fetch for %s",
                property_url,
            )
            return None

        try:
            headers = self._get_headers()
            response = self._circuit_breaker.call(
                requests.get,
                property_url,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            address_elem = soup.select_one(".ds-address-container")
            address = address_elem.text.strip() if address_elem else "Unknown Address"

            price_elem = soup.select_one('[data-testid="price"]')
            price_str = (
                price_elem.text.replace("$", "").replace(",", "")
                if price_elem
                else "0"
            )
            price = int(price_str) if price_str.isdigit() else 0

            beds_elem = soup.select_one(
                '[data-testid="bed-bath-beyond"] span:nth-child(1)'
            )
            bedrooms = (
                int(beds_elem.text.split()[0])
                if beds_elem and beds_elem.text.split()[0].isdigit()
                else 0
            )

            baths_elem = soup.select_one(
                '[data-testid="bed-bath-beyond"] span:nth-child(2)'
            )
            bathrooms = (
                float(baths_elem.text.split()[0])
                if baths_elem
                and baths_elem.text.split()[0].replace(".", "").isdigit()
                else 0
            )

            sqft_elem = soup.select_one(
                '[data-testid="bed-bath-beyond"] span:nth-child(3)'
            )
            sqft = (
                int(sqft_elem.text.split()[0].replace(",", ""))
                if sqft_elem
                and sqft_elem.text.split()[0].replace(",", "").isdigit()
                else 0
            )

            return {
                "address": address,
                "price": price,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sqft": sqft,
                "year_built": 0,
                "property_type": "Residential",
                "lot_size": 0,
                "listing_url": property_url,
                "source": "Zillow",
            }
        except CircuitOpenError:
            logger.warning(
                "ZillowScraper: circuit breaker rejected detail fetch for %s",
                property_url,
            )
            return None
        except requests.RequestException as exc:
            logger.error("Network error for %s: %s", property_url, exc)
            return None
        except (ValueError, AttributeError) as exc:
            logger.error("Parsing error for %s: %s", property_url, exc)
            return None

    # ------------------------------------------------------------------
    # Public search interface (async, preserves existing API contract)
    # ------------------------------------------------------------------

    async def search_properties(
        self, city: str, state: str, max_pages: int = 3
    ) -> list[Property]:
        """Search for property listings in the given city and state.

        Fetches up to *max_pages* search-results pages concurrently, then
        fetches the detail page for each listing found.

        Parameters
        ----------
        city:
            City name (e.g. ``"Seattle"``).
        state:
            Two-letter state abbreviation (e.g. ``"WA"``).
        max_pages:
            Maximum number of search-results pages to retrieve.

        Returns
        -------
        list[Property]
            A list of :class:`~models.property.Property` instances.  Returns
            an empty list when no listings are found or if the circuit is open.
        """
        # Short-circuit immediately if the breaker is already open.
        if self._circuit_breaker.state.value == "OPEN":
            logger.warning(
                "ZillowScraper: circuit is OPEN; aborting search for %s, %s",
                city,
                state,
            )
            return []

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_page(session, self._get_search_url(city, state, page))
                for page in range(1, max_pages + 1)
            ]
            pages = await asyncio.gather(*tasks, return_exceptions=False)

        properties: list[Property] = []
        for page_content in pages:
            if page_content is None:
                continue
            soup = BeautifulSoup(page_content, "html.parser")
            listings = self._extract_listings_from_page(soup)
            for listing in listings:
                prop_data = self._parse_property_details(listing["url"])
                if prop_data:
                    properties.append(Property(**prop_data))

        return properties
