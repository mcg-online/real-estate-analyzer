"""
Tests for cursor-based pagination on GET /api/properties.

Covers:
  - Correct response shape when cursor param is present
  - First-page request (cursor='')
  - Cursor with custom limit
  - Invalid cursor format returns 400
  - Empty result set with cursor (has_more=False, next_cursor=None)
  - has_more=True when result count equals limit
  - has_more=False when result count is less than limit
  - next_cursor reflects the _id of the last item in the page
  - Existing offset/limit pagination is unaffected (backward compat)
  - Filters are forwarded correctly in cursor mode
  - Partial page (fewer results than limit) clears next_cursor
  - Cursor param present but empty string hits first-page path
"""

from __future__ import annotations

import sys
import types
from datetime import datetime
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_VALID_OID_A = "aaaaaaaaaaaaaaaaaaaaaaaa"  # 24 hex chars — valid ObjectId
_VALID_OID_B = "bbbbbbbbbbbbbbbbbbbbbbbb"
_VALID_OID_C = "cccccccccccccccccccccccc"


def _make_property_dict(oid: str = _VALID_OID_A, **overrides: Any) -> dict[str, Any]:
    """Return a minimal property document dict."""
    base: dict[str, Any] = {
        "_id": oid,
        "address": "1 Cursor Lane",
        "city": "Portland",
        "state": "OR",
        "zip_code": "97201",
        "price": 400000,
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 1500,
        "year_built": 2010,
        "property_type": "single_family",
        "lot_size": 5000,
        "listing_url": f"http://example.com/{oid}",
        "source": "test",
        "latitude": 45.5,
        "longitude": -122.6,
        "images": [],
        "description": "Test property",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metrics": {},
        "score": None,
        "user_id": None,
    }
    base.update(overrides)
    return base


def _make_mock_property(oid: str = _VALID_OID_A, **overrides: Any) -> MagicMock:
    """Return a MagicMock that behaves like a Property instance."""
    prop_dict = _make_property_dict(oid=oid, **overrides)
    mock = MagicMock()
    # to_dict() returns everything except the raw _id key (route adds it)
    mock.to_dict.return_value = {k: v for k, v in prop_dict.items() if k != "_id"}
    mock._id = ObjectId(oid)
    mock.user_id = None
    return mock


# ---------------------------------------------------------------------------
# Application fixture  (module-scoped for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app() -> Generator[Any, None, None]:
    """
    Import the Flask application with all database I/O mocked.

    This mirrors the pattern used in test_routes.py so that the scheduler
    and MongoDB are never actually contacted.
    """
    # Clear cached imports so this module gets a clean application instance.
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith(("app", "routes", "models", "utils", "services")):
            del sys.modules[mod_name]

    # Stub the scheduler to prevent background-thread setup.
    stub_scheduler = types.ModuleType("services.scheduler")
    stub_scheduler.update_property_data = MagicMock()  # type: ignore[attr-defined]
    stub_scheduler.update_market_data = MagicMock()  # type: ignore[attr-defined]
    sys.modules["services.scheduler"] = stub_scheduler

    mock_db_instance = MagicMock()

    with (
        patch("utils.database.init_db", return_value=mock_db_instance),
        patch("utils.database.get_db", return_value=mock_db_instance),
        patch("utils.database.close_db", return_value=None),
    ):
        import app as flask_app_module

        flask_app = flask_app_module.app
        flask_app.config.update(
            {
                "TESTING": True,
                "JWT_SECRET_KEY": "test-secret-cursor-pagination",
                "SECRET_KEY": "test-secret-cursor-pagination",
                "CACHE_TYPE": "SimpleCache",
                "RATELIMIT_ENABLED": False,
            }
        )
        yield flask_app


@pytest.fixture()
def client(app: Any) -> Any:
    return app.test_client()


# ---------------------------------------------------------------------------
# Helper: build a mock db whose count_documents returns a fixed count.
# ---------------------------------------------------------------------------

def _mock_db(count: int = 0) -> MagicMock:
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = count
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    return mock_db


# ===========================================================================
# Tests: cursor-based pagination response shape
# ===========================================================================

class TestCursorResponseShape:
    """GET /api/properties?cursor=<oid> must return the cursor envelope."""

    def test_cursor_mode_returns_200(self, client: Any) -> None:
        """Providing a valid cursor produces HTTP 200."""
        mock_prop = _make_mock_property(oid=_VALID_OID_B)
        with patch("models.property.Property.find_all", return_value=[mock_prop]):
            response = client.get(f"/api/properties?cursor={_VALID_OID_A}&limit=10")
        assert response.status_code == 200

    def test_cursor_mode_returns_data_key(self, client: Any) -> None:
        """Response must contain a 'data' list."""
        mock_prop = _make_mock_property(oid=_VALID_OID_B)
        with patch("models.property.Property.find_all", return_value=[mock_prop]):
            response = client.get(f"/api/properties?cursor={_VALID_OID_A}")
        body = response.get_json()
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_cursor_mode_returns_has_more_key(self, client: Any) -> None:
        """Response must contain a boolean 'has_more' key."""
        with patch("models.property.Property.find_all", return_value=[]):
            response = client.get(f"/api/properties?cursor={_VALID_OID_A}")
        body = response.get_json()
        assert "has_more" in body
        assert isinstance(body["has_more"], bool)

    def test_cursor_mode_returns_next_cursor_key(self, client: Any) -> None:
        """Response must contain a 'next_cursor' key (string or None)."""
        with patch("models.property.Property.find_all", return_value=[]):
            response = client.get(f"/api/properties?cursor={_VALID_OID_A}")
        body = response.get_json()
        assert "next_cursor" in body

    def test_cursor_mode_returns_limit_key(self, client: Any) -> None:
        """Response must include the effective 'limit' value."""
        with patch("models.property.Property.find_all", return_value=[]):
            response = client.get(f"/api/properties?cursor={_VALID_OID_A}&limit=25")
        body = response.get_json()
        assert body.get("limit") == 25

    def test_cursor_mode_does_not_return_offset_fields(self, client: Any) -> None:
        """Cursor response must NOT contain offset-mode fields (total, page, pages)."""
        with patch("models.property.Property.find_all", return_value=[]):
            response = client.get(f"/api/properties?cursor={_VALID_OID_A}")
        body = response.get_json()
        for field in ("total", "page", "pages"):
            assert field not in body, f"Unexpected field '{field}' in cursor response"


# ===========================================================================
# Tests: first-page cursor (empty string)
# ===========================================================================

class TestCursorFirstPage:
    """cursor='' means 'first page' — no _id lower-bound should be applied."""

    def test_empty_cursor_returns_200(self, client: Any) -> None:
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_all", return_value=[mock_prop]):
            response = client.get("/api/properties?cursor=")
        assert response.status_code == 200

    def test_empty_cursor_calls_find_all_with_none_cursor(self, client: Any) -> None:
        """find_all() must be called with cursor=None for an empty cursor string."""
        with patch("models.property.Property.find_all", return_value=[]) as mock_find:
            client.get("/api/properties?cursor=")
        _args, kwargs = mock_find.call_args
        assert kwargs.get("cursor") is None

    def test_empty_cursor_has_more_false_when_empty(self, client: Any) -> None:
        with patch("models.property.Property.find_all", return_value=[]):
            response = client.get("/api/properties?cursor=")
        body = response.get_json()
        assert body["has_more"] is False
        assert body["next_cursor"] is None


# ===========================================================================
# Tests: cursor with explicit limit
# ===========================================================================

class TestCursorWithLimit:
    """The limit parameter is respected in cursor mode."""

    def test_limit_clamped_to_100(self, client: Any) -> None:
        with patch("models.property.Property.find_all", return_value=[]) as mock_find:
            client.get(f"/api/properties?cursor={_VALID_OID_A}&limit=999")
        _args, kwargs = mock_find.call_args
        assert kwargs.get("limit") == 100

    def test_limit_minimum_is_1(self, client: Any) -> None:
        with patch("models.property.Property.find_all", return_value=[]) as mock_find:
            client.get(f"/api/properties?cursor={_VALID_OID_A}&limit=0")
        _args, kwargs = mock_find.call_args
        assert kwargs.get("limit") == 1

    def test_custom_limit_forwarded(self, client: Any) -> None:
        with patch("models.property.Property.find_all", return_value=[]) as mock_find:
            client.get(f"/api/properties?cursor={_VALID_OID_A}&limit=7")
        _args, kwargs = mock_find.call_args
        assert kwargs.get("limit") == 7


# ===========================================================================
# Tests: invalid cursor format returns 400
# ===========================================================================

class TestInvalidCursorFormat:
    """Non-ObjectId cursor values must return HTTP 400."""

    def test_invalid_cursor_returns_400(self, client: Any) -> None:
        response = client.get("/api/properties?cursor=not-an-objectid")
        assert response.status_code == 400

    def test_invalid_cursor_error_code(self, client: Any) -> None:
        response = client.get("/api/properties?cursor=not-an-objectid")
        body = response.get_json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_cursor_too_short(self, client: Any) -> None:
        """A 23-char hex string is not a valid ObjectId."""
        response = client.get("/api/properties?cursor=aaaaaaaaaaaaaaaaaaaaaaa")
        assert response.status_code == 400

    def test_invalid_cursor_non_hex(self, client: Any) -> None:
        """24 chars but containing non-hex characters."""
        response = client.get("/api/properties?cursor=zzzzzzzzzzzzzzzzzzzzzzzz")
        assert response.status_code == 400


# ===========================================================================
# Tests: has_more and next_cursor semantics
# ===========================================================================

class TestCursorHasMore:
    """has_more and next_cursor are set correctly based on result count vs limit."""

    def test_has_more_true_when_result_count_equals_limit(self, client: Any) -> None:
        """If we get exactly `limit` results, assume there may be more."""
        props = [_make_mock_property(oid=_VALID_OID_A), _make_mock_property(oid=_VALID_OID_B)]
        with patch("models.property.Property.find_all", return_value=props):
            response = client.get("/api/properties?cursor=&limit=2")
        body = response.get_json()
        assert body["has_more"] is True

    def test_has_more_false_when_fewer_than_limit_results(self, client: Any) -> None:
        """One result against a limit of 10 — no more pages."""
        props = [_make_mock_property(oid=_VALID_OID_A)]
        with patch("models.property.Property.find_all", return_value=props):
            response = client.get("/api/properties?cursor=&limit=10")
        body = response.get_json()
        assert body["has_more"] is False

    def test_next_cursor_is_last_item_id_when_has_more(self, client: Any) -> None:
        """next_cursor must equal the _id of the last item when has_more=True."""
        props = [_make_mock_property(oid=_VALID_OID_A), _make_mock_property(oid=_VALID_OID_B)]
        with patch("models.property.Property.find_all", return_value=props):
            response = client.get("/api/properties?cursor=&limit=2")
        body = response.get_json()
        assert body["next_cursor"] == _VALID_OID_B

    def test_next_cursor_is_none_when_no_more_results(self, client: Any) -> None:
        """next_cursor must be None when result count is below limit."""
        props = [_make_mock_property(oid=_VALID_OID_A)]
        with patch("models.property.Property.find_all", return_value=props):
            response = client.get("/api/properties?cursor=&limit=10")
        body = response.get_json()
        assert body["next_cursor"] is None

    def test_empty_result_set_has_more_false(self, client: Any) -> None:
        """Zero results always means has_more=False and next_cursor=None."""
        with patch("models.property.Property.find_all", return_value=[]):
            response = client.get(f"/api/properties?cursor={_VALID_OID_A}")
        body = response.get_json()
        assert body["has_more"] is False
        assert body["next_cursor"] is None


# ===========================================================================
# Tests: find_all called correctly in cursor mode
# ===========================================================================

class TestCursorCallsModel:
    """Verify that find_all() is invoked with the correct cursor ObjectId."""

    def test_valid_cursor_forwarded_as_objectid(self, client: Any) -> None:
        """The cursor string must be converted to ObjectId before being passed."""
        with patch("models.property.Property.find_all", return_value=[]) as mock_find:
            client.get(f"/api/properties?cursor={_VALID_OID_A}")
        _args, kwargs = mock_find.call_args
        assert kwargs.get("cursor") == ObjectId(_VALID_OID_A)

    def test_cursor_mode_does_not_pass_skip(self, client: Any) -> None:
        """In cursor mode find_all() is called without a non-zero skip."""
        with patch("models.property.Property.find_all", return_value=[]) as mock_find:
            client.get(f"/api/properties?cursor={_VALID_OID_A}")
        _args, kwargs = mock_find.call_args
        # skip should be absent or its default value (0), never a calculated offset.
        assert kwargs.get("skip", 0) == 0


# ===========================================================================
# Tests: backward compatibility — offset/limit mode unchanged
# ===========================================================================

class TestOffsetLimitBackwardCompat:
    """Without a cursor param the original offset/limit mode must still work."""

    def _mock_db(self, count: int) -> MagicMock:
        mock_col = MagicMock()
        mock_col.count_documents.return_value = count
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_col
        return mock_db

    def test_no_cursor_returns_offset_envelope(self, client: Any) -> None:
        """Without cursor the response must have total/page/pages keys."""
        mock_db = self._mock_db(count=1)
        mock_prop = _make_mock_property()
        with (
            patch("models.property.Property.find_all", return_value=[mock_prop]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties")
        body = response.get_json()
        assert response.status_code == 200
        for field in ("total", "page", "pages", "limit", "data"):
            assert field in body, f"Missing expected field '{field}' in offset response"

    def test_no_cursor_total_reflects_count(self, client: Any) -> None:
        mock_db = self._mock_db(count=42)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties?page=1&limit=10")
        body = response.get_json()
        assert body["total"] == 42
        assert body["page"] == 1
        assert body["pages"] == 5  # ceil(42/10)

    def test_no_cursor_does_not_contain_cursor_fields(self, client: Any) -> None:
        mock_db = self._mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties")
        body = response.get_json()
        for field in ("next_cursor", "has_more"):
            assert field not in body, f"Unexpected cursor field '{field}' in offset response"


# ===========================================================================
# Tests: filters are forwarded in cursor mode
# ===========================================================================

class TestCursorWithFilters:
    """Query-string filters must be applied in cursor mode."""

    def test_state_filter_forwarded(self, client: Any) -> None:
        with patch("models.property.Property.find_all", return_value=[]) as mock_find:
            client.get("/api/properties?cursor=&state=TX")
        _args, kwargs = mock_find.call_args
        assert kwargs.get("filters", {}).get("state") == "TX"

    def test_price_range_filter_forwarded(self, client: Any) -> None:
        with patch("models.property.Property.find_all", return_value=[]) as mock_find:
            client.get("/api/properties?cursor=&minPrice=100000&maxPrice=500000")
        _args, kwargs = mock_find.call_args
        price_filter = kwargs.get("filters", {}).get("price", {})
        assert price_filter.get("$gte") == 100000
        assert price_filter.get("$lte") == 500000
