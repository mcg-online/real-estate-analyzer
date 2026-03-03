import asyncio
import logging
from typing import Any

from services.data_collection.zillow_scraper import ZillowScraper

logger = logging.getLogger(__name__)


class DataCollectionError(Exception):
    """Raised when property data collection fails."""


class DataCollectionService:
    """Service responsible for collecting property data from available sources.

    Currently integrates with ZillowScraper as the sole data provider.
    Additional connectors can be registered by extending the ``_sources``
    mapping when they become available.

    Attributes:
        scraper: The ZillowScraper instance used for all Zillow requests.
    """

    def __init__(self) -> None:
        self.scraper = ZillowScraper()

    async def collect_properties(self, search_params: dict[str, Any]) -> list:
        """Collect property listings from Zillow for the given search parameters.

        Args:
            search_params: A dict containing:
                - ``city`` (str): The target city name.
                - ``state`` (str): The two-letter state abbreviation or full name.
                - ``max_pages`` (int, optional): Maximum result pages to fetch.
                  Defaults to 3.

        Returns:
            A list of :class:`models.property.Property` instances found for the
            search location.  Returns an empty list when the scraper encounters
            an error so callers always receive an iterable.

        Raises:
            DataCollectionError: When ``city`` or ``state`` is missing from
                ``search_params``.
        """
        city: str | None = search_params.get("city")
        state: str | None = search_params.get("state")
        max_pages: int = int(search_params.get("max_pages", 3))

        if not city or not state:
            raise DataCollectionError(
                "search_params must include both 'city' and 'state' keys."
            )

        logger.info(
            "Collecting properties via Zillow: city=%s, state=%s, max_pages=%d",
            city,
            state,
            max_pages,
        )

        try:
            properties = await self.scraper.search_properties(
                city=city,
                state=state,
                max_pages=max_pages,
            )
            logger.info(
                "Zillow returned %d properties for %s, %s",
                len(properties),
                city,
                state,
            )
            return properties
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "Zillow collection failed for %s, %s: %s",
                city,
                state,
                exc,
                exc_info=True,
            )
            return []

    def collect_from_all_sources(self, search_params: dict[str, Any]) -> list:
        """Collect property data from all configured sources synchronously.

        This is the primary entry point for callers that operate outside an
        existing event loop (e.g. scheduled jobs, CLI scripts).  Internally it
        delegates to :meth:`collect_properties` via ``asyncio.run``.

        Args:
            search_params: Same dict accepted by :meth:`collect_properties`.

        Returns:
            A combined list of :class:`models.property.Property` instances
            from all sources.  Currently only Zillow is supported.
        """
        logger.info("collect_from_all_sources called with params: %s", search_params)
        try:
            return asyncio.run(self.collect_properties(search_params))
        except DataCollectionError:
            raise
        except RuntimeError as exc:
            # asyncio.run() raises RuntimeError when called from within a
            # running event loop (e.g. inside an async web framework).
            # Surface a clear message so the caller knows to await instead.
            logger.error(
                "collect_from_all_sources called from inside a running event loop. "
                "Use 'await collect_properties(search_params)' instead. Error: %s",
                exc,
            )
            raise DataCollectionError(
                "Cannot call collect_from_all_sources from within a running event loop. "
                "Await collect_properties() directly."
            ) from exc
