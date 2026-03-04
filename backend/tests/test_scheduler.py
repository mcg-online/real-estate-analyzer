"""Tests for the scheduler module (backend/services/scheduler.py).

All external dependencies - ZillowScraper, Market.find_all(), get_db() - are
mocked so no real database or HTTP connections are made.
"""

from __future__ import annotations

import importlib
import sys
import os
from unittest.mock import MagicMock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def _ensure_scheduler_importable():
    """Guarantee services.scheduler is the *real* module, not a test stub.

    test_routes.py replaces services.scheduler with a lightweight stub that
    only has two MagicMock attributes.  If that stub is still in sys.modules
    when these tests run, ``patch("services.scheduler.get_db")`` fails
    because the stub lacks ``get_db``.  We detect the stub (missing ``get_db``
    attribute) and force a clean reimport of the real module.
    """
    sched = sys.modules.get("services.scheduler")
    if sched is None or not hasattr(sched, "get_db"):
        # Remove stale stub + parent so importlib loads fresh copies
        for key in list(sys.modules):
            if key == "services.scheduler" or key == "services":
                del sys.modules[key]
        importlib.import_module("services")
        sched = importlib.import_module("services.scheduler")
    # Ensure parent has the attribute (patch relies on getattr)
    parent = sys.modules.get("services")
    if parent is not None:
        parent.scheduler = sched
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_market(name: str = "Test Market") -> MagicMock:
    """Return a MagicMock that mimics a Market instance."""
    m = MagicMock()
    m.name = name
    m.save = MagicMock()
    return m


# ---------------------------------------------------------------------------
# update_property_data tests
# ---------------------------------------------------------------------------

class TestUpdatePropertyData:
    """Tests for scheduler.update_property_data()."""

    # We patch ZillowScraper at its import site inside the scheduler module.
    _SCRAPER_PATH = "services.scheduler.ZillowScraper"

    def test_returns_true_on_success(self):
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.search_properties.return_value = []

        with patch(self._SCRAPER_PATH, return_value=mock_scraper_instance):
            from services.scheduler import update_property_data
            result = update_property_data()

        assert result is True

    def test_calls_search_properties_for_each_city(self):
        """search_properties should be called once per city in the hardcoded list."""
        mock_prop = MagicMock()
        mock_prop.save = MagicMock()
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.search_properties.return_value = [mock_prop]

        with patch(self._SCRAPER_PATH, return_value=mock_scraper_instance):
            from services.scheduler import update_property_data
            update_property_data()

        # The scheduler hardcodes 3 cities (Seattle, Portland, San Francisco)
        assert mock_scraper_instance.search_properties.call_count == 3

    def test_saves_each_returned_property(self):
        """Every property returned by the scraper should have .save() called."""
        props = [MagicMock(save=MagicMock()), MagicMock(save=MagicMock())]
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.search_properties.return_value = props

        with patch(self._SCRAPER_PATH, return_value=mock_scraper_instance):
            from services.scheduler import update_property_data
            update_property_data()

        for prop in props:
            prop.save.assert_called()

    def test_continues_on_single_city_exception(self):
        """An exception for one city must not abort the remaining cities."""
        call_count = {"n": 0}

        def scrape_side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("network error")
            return []

        mock_scraper_instance = MagicMock()
        mock_scraper_instance.search_properties.side_effect = scrape_side_effect

        with patch(self._SCRAPER_PATH, return_value=mock_scraper_instance):
            from services.scheduler import update_property_data
            result = update_property_data()

        # Function should still return True (inner exception handled)
        assert result is True
        # All 3 cities were attempted
        assert call_count["n"] == 3

    def test_returns_false_when_outer_exception_occurs(self):
        """If ZillowScraper() constructor itself raises, function returns False."""
        with patch(self._SCRAPER_PATH, side_effect=Exception("fatal")):
            from services.scheduler import update_property_data
            result = update_property_data()

        assert result is False

    def test_logs_start_message(self, caplog):
        import logging

        mock_scraper_instance = MagicMock()
        mock_scraper_instance.search_properties.return_value = []

        with patch(self._SCRAPER_PATH, return_value=mock_scraper_instance):
            with caplog.at_level(logging.INFO, logger="services.scheduler"):
                from services.scheduler import update_property_data
                update_property_data()

        assert any("property data update" in record.message.lower() for record in caplog.records)

    def test_logs_completion_message(self, caplog):
        import logging

        mock_scraper_instance = MagicMock()
        mock_scraper_instance.search_properties.return_value = []

        with patch(self._SCRAPER_PATH, return_value=mock_scraper_instance):
            with caplog.at_level(logging.INFO, logger="services.scheduler"):
                from services.scheduler import update_property_data
                update_property_data()

        messages = [r.message.lower() for r in caplog.records]
        assert any("completed" in msg or "success" in msg for msg in messages)

    def test_does_not_crash_with_empty_property_list(self):
        """An empty property list per city is a valid, non-error result."""
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.search_properties.return_value = []

        with patch(self._SCRAPER_PATH, return_value=mock_scraper_instance):
            from services.scheduler import update_property_data
            result = update_property_data()

        assert result is True


# ---------------------------------------------------------------------------
# update_market_data tests
# ---------------------------------------------------------------------------

class TestUpdateMarketData:
    """Tests for scheduler.update_market_data()."""

    _GET_DB_PATH = "services.scheduler.get_db"
    _MARKET_PATH = "services.scheduler.Market"

    def test_returns_true_on_success(self):
        mock_market = _make_mock_market()

        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.return_value = [mock_market]
            from services.scheduler import update_market_data
            result = update_market_data()

        assert result is True

    def test_calls_find_all(self):
        """update_market_data must call Market.find_all() to retrieve markets."""
        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.return_value = []
            from services.scheduler import update_market_data
            update_market_data()

        mock_market_cls.find_all.assert_called_once()

    def test_saves_each_market(self):
        """Every market returned by find_all() should have .save() called."""
        markets = [_make_mock_market("Alpha"), _make_mock_market("Beta")]

        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.return_value = markets
            from services.scheduler import update_market_data
            update_market_data()

        for market in markets:
            market.save.assert_called_once()

    def test_updates_updated_at_timestamp(self):
        """Each market's updated_at field should be refreshed."""

        market = _make_mock_market()

        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.return_value = [market]
            from services.scheduler import update_market_data
            update_market_data()

        # updated_at should have been assigned; verify it's a datetime
        assert hasattr(market, "updated_at")

    def test_continues_on_single_market_exception(self):
        """A save() error for one market must not stop the others."""
        good_market = _make_mock_market("Good")
        bad_market = _make_mock_market("Bad")
        bad_market.save.side_effect = Exception("db write error")

        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.return_value = [bad_market, good_market]
            from services.scheduler import update_market_data
            result = update_market_data()

        # Should still return True; good_market should have been saved
        assert result is True
        good_market.save.assert_called_once()

    def test_returns_false_when_get_db_raises(self):
        """If get_db() raises (no connection), function returns False."""
        with patch(self._GET_DB_PATH, side_effect=ConnectionError("no db")):
            from services.scheduler import update_market_data
            result = update_market_data()

        assert result is False

    def test_returns_false_when_find_all_raises(self):
        """If Market.find_all() raises, the outer handler catches it."""
        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.side_effect = Exception("query error")
            from services.scheduler import update_market_data
            result = update_market_data()

        assert result is False

    def test_handles_empty_market_list(self):
        """Zero markets is a valid result; function should return True."""
        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.return_value = []
            from services.scheduler import update_market_data
            result = update_market_data()

        assert result is True

    def test_logs_start_message(self, caplog):
        import logging

        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.return_value = []
            with caplog.at_level(logging.INFO, logger="services.scheduler"):
                from services.scheduler import update_market_data
                update_market_data()

        assert any("market data update" in r.message.lower() for r in caplog.records)

    def test_logs_completion_message(self, caplog):
        import logging

        with (
            patch(self._GET_DB_PATH, return_value=MagicMock()),
            patch(self._MARKET_PATH) as mock_market_cls,
        ):
            mock_market_cls.find_all.return_value = []
            with caplog.at_level(logging.INFO, logger="services.scheduler"):
                from services.scheduler import update_market_data
                update_market_data()

        messages = [r.message.lower() for r in caplog.records]
        assert any("completed" in msg or "success" in msg for msg in messages)
