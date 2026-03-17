"""
Contract tests: verify that every backend API response matches the shape
that the React frontend's api.js client expects.

These tests exercise the Flask application through the test client and mock
all MongoDB / Redis / external-service calls.  No live infrastructure is
required.

Contracts verified
------------------
1.  Property list envelope    GET  /api/v1/properties
2.  Property object shape     GET  /api/v1/properties  (items in data array)
3.  Single property shape     GET  /api/v1/properties/<id>
4.  Analysis shape            GET  /api/v1/analysis/property/<id>
5.  Custom analysis shape     POST /api/v1/analysis/property/<id>
6.  Top markets shape         GET  /api/v1/markets/top
7.  Login contract            POST /api/v1/auth/login
8.  Register contract         POST /api/v1/auth/register
9.  Logout contract           POST /api/v1/auth/logout
10. Error response shape      various 4xx / 5xx endpoints
11. Pagination metadata       GET  /api/v1/properties  (with page/limit params)
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from flask_jwt_extended import create_access_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PROPERTY_ID = "64a1f2c3d4e5f6a7b8c9d0e1"
_VALID_MARKET_ID = "74b2e3d4e5f6a7b8c9d0e1f2"


def _make_property_dict(**overrides: Any) -> dict[str, Any]:
    """Return a full property dict whose shape matches Property.to_dict()."""
    base: dict[str, Any] = {
        "_id": _VALID_PROPERTY_ID,
        "address": "123 Contract Street",
        "city": "Seattle",
        "state": "WA",
        "zip_code": "98101",
        "price": 350_000,
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 1_800,
        "year_built": 2005,
        "property_type": "Single Family",
        "lot_size": 6_000,
        "listing_url": "http://example.com/listing/1",
        "source": "test",
        "latitude": 47.6062,
        "longitude": -122.3321,
        "images": [],
        "description": "Contract test property",
        "user_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {},
        "score": None,
    }
    base.update(overrides)
    return base


def _make_mock_property(**overrides: Any) -> MagicMock:
    """Return a MagicMock that behaves like a Property model instance."""
    prop_dict = _make_property_dict(**overrides)
    mock = MagicMock()
    # to_dict() must include _id as ObjectId so the route handler can stringify it
    mock.to_dict.return_value = dict(prop_dict)
    mock._id = prop_dict["_id"]
    mock.user_id = None
    # Attributes used by FinancialMetrics
    mock.price = prop_dict["price"]
    mock.sqft = prop_dict["sqft"]
    mock.bedrooms = prop_dict["bedrooms"]
    mock.bathrooms = prop_dict["bathrooms"]
    mock.city = prop_dict["city"]
    mock.state = prop_dict["state"]
    mock.zip_code = prop_dict["zip_code"]
    return mock


def _make_analysis_result() -> dict[str, Any]:
    """Return a realistic financial analysis result dict."""
    return {
        "monthly_rent": 1_944.44,
        "monthly_expenses": {
            "total": 680.0,
            "property_tax": 291.67,
            "insurance": 102.08,
            "maintenance": 291.67,
            "vacancy": 155.56,
            "management": 194.44,
            "hoa": 0.0,
        },
        "mortgage_payment": 1_419.47,
        "monthly_cash_flow": -155.03,
        "annual_cash_flow": -1_860.36,
        "cap_rate": 4.24,
        "cash_on_cash_return": -2.48,
        "roi": {
            "total_roi": 28.15,
            "annualized_roi": 5.08,
            "future_value": 405_990.94,
            "total_cash_flow": -9_301.8,
            "appreciation_profit": 55_990.94,
        },
        "break_even_point": 12.5,
        "price_to_rent_ratio": 15.0,
        "gross_yield": 6.67,
        "total_investment": 80_500.0,
    }


def _make_market_dict() -> dict[str, Any]:
    """Return a minimal market data dict used by analysis services."""
    return {
        "property_tax_rate": 0.01,
        "price_to_rent_ratio": 15,
        "vacancy_rate": 0.08,
        "appreciation_rate": 0.03,
        "avg_hoa_fee": 0,
        "tax_benefits": {},
        "financing_programs": [],
    }


# ---------------------------------------------------------------------------
# Application fixture  (module-scoped for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app() -> Generator[Any, None, None]:  # type: ignore[misc]
    """
    Import the Flask app with every external dependency mocked.

    The fixture:
    - Removes previously cached modules so imports are clean.
    - Replaces services.scheduler with a no-op stub.
    - Patches utils.database.{init_db, get_db, close_db}.
    - Configures the app for TESTING mode.
    """
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith(("app", "routes", "models", "utils", "services")):
            del sys.modules[mod_name]

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
        import app as flask_app_module  # noqa: PLC0415

        flask_app = flask_app_module.app
        flask_app.config.update(
            {
                "TESTING": True,
                "JWT_SECRET_KEY": "contract-test-secret",
                "SECRET_KEY": "contract-test-secret",
                "CACHE_TYPE": "SimpleCache",
                "RATELIMIT_ENABLED": False,
            }
        )
        yield flask_app


@pytest.fixture()
def client(app: Any) -> Any:
    """Return a Flask test client."""
    return app.test_client()


@pytest.fixture()
def auth_token(app: Any) -> str:
    """Return a valid JWT access token for authenticated endpoints."""
    with app.app_context():
        return create_access_token(identity="contract_test_user")


# ---------------------------------------------------------------------------
# CONTRACT 1 — Property list envelope
# ---------------------------------------------------------------------------

class TestPropertyListContract:
    """GET /api/v1/properties must return a pagination envelope."""

    def _mock_db(self, mock_prop: MagicMock) -> MagicMock:
        db = MagicMock()
        db["properties"].count_documents.return_value = 1
        return db

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_property_list_returns_200(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """GET /api/v1/properties responds with HTTP 200."""
        mock_prop = _make_mock_property()
        mock_find_all.return_value = [mock_prop]
        mock_get_db.return_value = self._mock_db(mock_prop)

        response = client.get("/api/v1/properties")
        assert response.status_code == 200

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_property_list_envelope_has_required_keys(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """Response envelope must contain: data, total, page, limit, pages."""
        mock_prop = _make_mock_property()
        mock_find_all.return_value = [mock_prop]
        mock_get_db.return_value = self._mock_db(mock_prop)

        response = client.get("/api/v1/properties")
        body = response.get_json()

        assert body is not None
        for key in ("data", "total", "page", "limit", "pages"):
            assert key in body, f"Missing envelope key: '{key}'"

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_property_list_data_is_array(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """The 'data' value must be a list."""
        mock_prop = _make_mock_property()
        mock_find_all.return_value = [mock_prop]
        mock_get_db.return_value = self._mock_db(mock_prop)

        body = client.get("/api/v1/properties").get_json()
        assert isinstance(body["data"], list)

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_property_list_pagination_types(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """total, page, limit, and pages must all be integers."""
        mock_prop = _make_mock_property()
        mock_find_all.return_value = [mock_prop]
        mock_get_db.return_value = self._mock_db(mock_prop)

        body = client.get("/api/v1/properties").get_json()
        assert isinstance(body["total"], int), "total must be int"
        assert isinstance(body["page"], int), "page must be int"
        assert isinstance(body["limit"], int), "limit must be int"
        assert isinstance(body["pages"], int), "pages must be int"


# ---------------------------------------------------------------------------
# CONTRACT 2 — Property object shape (items inside the data array)
# ---------------------------------------------------------------------------

class TestPropertyObjectContract:
    """Each item in data[] must expose the keys the frontend depends on."""

    REQUIRED_PROPERTY_KEYS = (
        "_id", "address", "city", "state", "zip_code", "price",
        "bedrooms", "bathrooms", "sqft", "year_built", "property_type",
        "lot_size", "listing_url", "source", "created_at", "updated_at",
    )

    def _mock_db(self) -> MagicMock:
        db = MagicMock()
        db["properties"].count_documents.return_value = 1
        return db

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_property_item_has_required_keys(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """Every property item must expose all fields the frontend accesses."""
        mock_prop = _make_mock_property()
        mock_find_all.return_value = [mock_prop]
        mock_get_db.return_value = self._mock_db()

        body = client.get("/api/v1/properties").get_json()
        assert body["data"], "data array must not be empty for this assertion"

        item = body["data"][0]
        for key in self.REQUIRED_PROPERTY_KEYS:
            assert key in item, f"Property item missing required key: '{key}'"

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_property_id_is_string(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """_id must be serialized as a string (ObjectId is not JSON-safe)."""
        mock_prop = _make_mock_property()
        mock_find_all.return_value = [mock_prop]
        mock_get_db.return_value = self._mock_db()

        body = client.get("/api/v1/properties").get_json()
        item = body["data"][0]
        assert isinstance(item["_id"], str), "_id must be a string"

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_property_numeric_fields_are_numbers(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """price, bedrooms, bathrooms, sqft must be numeric types."""
        mock_prop = _make_mock_property()
        mock_find_all.return_value = [mock_prop]
        mock_get_db.return_value = self._mock_db()

        body = client.get("/api/v1/properties").get_json()
        item = body["data"][0]
        for field in ("price", "bedrooms", "bathrooms", "sqft"):
            assert isinstance(item[field], (int, float)), (
                f"'{field}' must be numeric, got {type(item[field])}"
            )


# ---------------------------------------------------------------------------
# CONTRACT 3 — Single property shape
# ---------------------------------------------------------------------------

class TestSinglePropertyContract:
    """GET /api/v1/properties/<id> must return a property object."""

    REQUIRED_PROPERTY_KEYS = (
        "address", "city", "state", "zip_code", "price",
        "bedrooms", "bathrooms", "sqft", "year_built", "property_type",
        "lot_size", "listing_url", "source", "created_at", "updated_at",
    )

    @patch("routes.properties.Property.find_by_id")
    def test_single_property_returns_200(
        self, mock_find_by_id: Any, client: Any
    ) -> None:
        """GET /api/v1/properties/<valid-id> returns 200."""
        mock_find_by_id.return_value = _make_mock_property()
        response = client.get(f"/api/v1/properties/{_VALID_PROPERTY_ID}")
        assert response.status_code == 200

    @patch("routes.properties.Property.find_by_id")
    def test_single_property_has_required_keys(
        self, mock_find_by_id: Any, client: Any
    ) -> None:
        """Single property response must include all shape keys."""
        mock_find_by_id.return_value = _make_mock_property()
        body = client.get(f"/api/v1/properties/{_VALID_PROPERTY_ID}").get_json()

        for key in self.REQUIRED_PROPERTY_KEYS:
            assert key in body, f"Single property missing key: '{key}'"

    @patch("routes.properties.Property.find_by_id")
    def test_single_property_not_found_returns_404(
        self, mock_find_by_id: Any, client: Any
    ) -> None:
        """Missing property must return HTTP 404."""
        mock_find_by_id.return_value = None
        response = client.get(f"/api/v1/properties/{_VALID_PROPERTY_ID}")
        assert response.status_code == 404

    def test_invalid_property_id_returns_400(self, client: Any) -> None:
        """A non-ObjectId property_id must return HTTP 400."""
        response = client.get("/api/v1/properties/not-an-objectid")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# CONTRACT 4 — Analysis shape (GET)
# ---------------------------------------------------------------------------

class TestPropertyAnalysisContract:
    """GET /api/v1/analysis/property/<id> must return the analysis envelope."""

    REQUIRED_ANALYSIS_KEYS = (
        "property_id",
        "financial_analysis",
        "tax_benefits",
        "financing_options",
        "market_data",
    )

    REQUIRED_FINANCIAL_KEYS = (
        "cap_rate",
        "cash_on_cash_return",
        "monthly_cash_flow",
        "roi",
    )

    REQUIRED_ROI_KEYS = (
        "total_roi",
        "annualized_roi",
        "future_value",
        "total_cash_flow",
        "appreciation_profit",
    )

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_analysis_returns_200(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """GET analysis endpoint returns HTTP 200 for a valid property."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None  # fall back to defaults
        response = client.get(f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}")
        assert response.status_code == 200

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_analysis_has_required_envelope_keys(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """Analysis response must include the top-level envelope keys."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None
        body = client.get(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}"
        ).get_json()

        for key in self.REQUIRED_ANALYSIS_KEYS:
            assert key in body, f"Analysis envelope missing key: '{key}'"

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_analysis_financial_keys_present(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """financial_analysis sub-object must include core metric keys."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None
        body = client.get(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}"
        ).get_json()

        financial = body.get("financial_analysis", {})
        for key in self.REQUIRED_FINANCIAL_KEYS:
            assert key in financial, f"financial_analysis missing key: '{key}'"

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_analysis_roi_sub_keys_present(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """roi sub-object must contain all expected keys."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None
        body = client.get(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}"
        ).get_json()

        roi = body.get("financial_analysis", {}).get("roi", {})
        for key in self.REQUIRED_ROI_KEYS:
            assert key in roi, f"roi sub-object missing key: '{key}'"

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_analysis_property_id_is_string(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """property_id in analysis response must be a plain string."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None
        body = client.get(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}"
        ).get_json()

        assert isinstance(body["property_id"], str)

    @patch("routes.analysis.Property.find_by_id")
    def test_analysis_not_found_returns_404(
        self, mock_find: Any, client: Any
    ) -> None:
        """Analysis for a missing property must return 404."""
        mock_find.return_value = None
        response = client.get(f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# CONTRACT 5 — Custom analysis shape (POST)
# ---------------------------------------------------------------------------

class TestCustomAnalysisContract:
    """POST /api/v1/analysis/property/<id> must return the same envelope shape."""

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_custom_analysis_returns_200(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """POST custom analysis returns HTTP 200."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None
        response = client.post(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}",
            json={
                "down_payment_percentage": 0.20,
                "interest_rate": 0.045,
                "term_years": 30,
                "holding_period": 5,
                "appreciation_rate": 0.03,
                "tax_bracket": 0.22,
            },
        )
        assert response.status_code == 200

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_custom_analysis_has_same_envelope_as_get(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """POST analysis must return the same top-level keys as GET analysis."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None
        body = client.post(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}",
            json={"down_payment_percentage": 0.25},
        ).get_json()

        for key in (
            "property_id",
            "financial_analysis",
            "tax_benefits",
            "financing_options",
            "market_data",
        ):
            assert key in body, f"Custom analysis envelope missing key: '{key}'"

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_custom_analysis_includes_parameters_echo(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """POST analysis echoes the submitted parameters under 'parameters'."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None
        body = client.post(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}",
            json={"down_payment_percentage": 0.30},
        ).get_json()

        assert "parameters" in body, "Custom analysis must echo params under 'parameters'"

    @patch("routes.analysis.Market.find_by_location")
    @patch("routes.analysis.Property.find_by_id")
    def test_custom_analysis_financial_has_roi_keys(
        self, mock_find: Any, mock_market: Any, client: Any
    ) -> None:
        """financial_analysis.roi must contain the expected sub-keys."""
        mock_find.return_value = _make_mock_property()
        mock_market.return_value = None
        body = client.post(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}",
            json={"term_years": 30},
        ).get_json()

        roi = body.get("financial_analysis", {}).get("roi", {})
        for key in ("total_roi", "annualized_roi", "future_value"):
            assert key in roi, f"Custom analysis roi missing key: '{key}'"

    def test_custom_analysis_invalid_body_returns_400(self, client: Any) -> None:
        """POST with non-JSON body must return 400."""
        response = client.post(
            f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}",
            data="not json",
            content_type="text/plain",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# CONTRACT 6 — Top markets shape
# ---------------------------------------------------------------------------

class TestTopMarketsContract:
    """GET /api/v1/markets/top must return a list of market objects."""

    REQUIRED_MARKET_KEYS = ("state", "city", "avg_price", "avg_cap_rate", "avg_roi")

    @patch("routes.analysis.get_db")
    def test_top_markets_returns_200(self, mock_get_db: Any, client: Any) -> None:
        """GET /api/v1/markets/top returns HTTP 200."""
        db = MagicMock()
        db.properties.aggregate.return_value = iter([])
        mock_get_db.return_value = db
        response = client.get("/api/v1/markets/top")
        assert response.status_code == 200

    @patch("routes.analysis.get_db")
    def test_top_markets_returns_list(self, mock_get_db: Any, client: Any) -> None:
        """Response body must be a list (array)."""
        db = MagicMock()
        db.properties.aggregate.return_value = iter([])
        mock_get_db.return_value = db
        body = client.get("/api/v1/markets/top").get_json()
        assert isinstance(body, list)

    @patch("routes.analysis.get_db")
    def test_top_markets_items_have_required_keys(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """When markets are present each item must contain required keys."""
        db = MagicMock()
        db.properties.aggregate.return_value = iter(
            [
                {
                    "state": "WA",
                    "city": "Seattle",
                    "count": 10,
                    "avg_price": 500_000.0,
                    "avg_cap_rate": 5.2,
                    "avg_cash_flow": 200.0,
                    "avg_roi": 8.1,
                }
            ]
        )
        mock_get_db.return_value = db
        body = client.get("/api/v1/markets/top").get_json()

        assert len(body) > 0, "Expected at least one market item"
        item = body[0]
        for key in self.REQUIRED_MARKET_KEYS:
            assert key in item, f"Market item missing key: '{key}'"

    @patch("routes.analysis.get_db")
    def test_top_markets_invalid_metric_returns_400(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """Unknown metric parameter must return HTTP 400."""
        db = MagicMock()
        mock_get_db.return_value = db
        response = client.get("/api/v1/markets/top?metric=invalid")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# CONTRACT 7 — Login contract
# ---------------------------------------------------------------------------

class TestLoginContract:
    """POST /api/v1/auth/login must return {access_token: string}."""

    @patch("routes.users.get_db")
    def test_login_success_returns_200(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """Valid credentials return HTTP 200."""
        from werkzeug.security import generate_password_hash

        db = MagicMock()
        db.__getitem__.return_value.find_one.return_value = {
            "username": "testuser",
            "password": generate_password_hash("Password1", method="pbkdf2:sha256"),
        }
        mock_get_db.return_value = db

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "Password1"},
        )
        assert response.status_code == 200

    @patch("routes.users.get_db")
    def test_login_returns_access_token_key(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """Successful login body must contain 'access_token'."""
        from werkzeug.security import generate_password_hash

        db = MagicMock()
        db.__getitem__.return_value.find_one.return_value = {
            "username": "testuser",
            "password": generate_password_hash("Password1", method="pbkdf2:sha256"),
        }
        mock_get_db.return_value = db

        body = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "Password1"},
        ).get_json()

        assert "access_token" in body, "Login response must contain 'access_token'"

    @patch("routes.users.get_db")
    def test_login_access_token_is_string(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """access_token value must be a non-empty string."""
        from werkzeug.security import generate_password_hash

        db = MagicMock()
        db.__getitem__.return_value.find_one.return_value = {
            "username": "testuser",
            "password": generate_password_hash("Password1", method="pbkdf2:sha256"),
        }
        mock_get_db.return_value = db

        body = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "Password1"},
        ).get_json()

        token = body.get("access_token")
        assert isinstance(token, str) and len(token) > 0

    @patch("routes.users.get_db")
    def test_login_bad_credentials_returns_401(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """Wrong password must return 401."""
        db = MagicMock()
        db.__getitem__.return_value.find_one.return_value = None
        mock_get_db.return_value = db

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "wrongpass"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# CONTRACT 8 — Register contract
# ---------------------------------------------------------------------------

class TestRegisterContract:
    """POST /api/v1/auth/register must return {message: string}."""

    @patch("routes.users.get_db")
    def test_register_success_returns_201(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """New user registration returns HTTP 201."""
        db = MagicMock()
        db.__getitem__.return_value.find_one.return_value = None
        db.__getitem__.return_value.insert_one.return_value = MagicMock()
        mock_get_db.return_value = db

        response = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "password": "Securepass1"},
        )
        assert response.status_code == 201

    @patch("routes.users.get_db")
    def test_register_returns_message_key(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """Registration body must contain 'message'."""
        db = MagicMock()
        db.__getitem__.return_value.find_one.return_value = None
        db.__getitem__.return_value.insert_one.return_value = MagicMock()
        mock_get_db.return_value = db

        body = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser2", "password": "Securepass1"},
        ).get_json()

        assert "message" in body, "Register response must contain 'message'"

    @patch("routes.users.get_db")
    def test_register_message_is_string(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """message value must be a string."""
        db = MagicMock()
        db.__getitem__.return_value.find_one.return_value = None
        db.__getitem__.return_value.insert_one.return_value = MagicMock()
        mock_get_db.return_value = db

        body = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser3", "password": "Securepass1"},
        ).get_json()

        assert isinstance(body["message"], str)

    @patch("routes.users.get_db")
    def test_register_duplicate_returns_409(
        self, mock_get_db: Any, client: Any
    ) -> None:
        """Registering an existing username returns 409."""
        db = MagicMock()
        db.__getitem__.return_value.find_one.return_value = {"username": "existing"}
        mock_get_db.return_value = db

        response = client.post(
            "/api/v1/auth/register",
            json={"username": "existing", "password": "Securepass1"},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# CONTRACT 9 — Logout contract
# ---------------------------------------------------------------------------

class TestLogoutContract:
    """POST /api/v1/auth/logout must return {message: string} with a valid token."""

    def test_logout_without_token_returns_401(self, client: Any) -> None:
        """Logout without a JWT must be rejected with 401."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    def test_logout_with_valid_token_returns_200(
        self, client: Any, auth_token: str, app: Any
    ) -> None:
        """Logout with a valid Bearer token returns 200."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

    def test_logout_returns_message_key(
        self, client: Any, auth_token: str, app: Any
    ) -> None:
        """Logout response must contain 'message'."""
        # Use a fresh token so the blocklist from the previous test does not
        # interfere (each call gets its own jti via the fixture's token).
        with app.app_context():
            fresh_token = create_access_token(identity="logout_contract_user")

        body = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {fresh_token}"},
        ).get_json()

        assert "message" in body, "Logout response must contain 'message'"

    def test_logout_message_is_string(
        self, client: Any, app: Any
    ) -> None:
        """Logout message must be a string."""
        with app.app_context():
            fresh_token = create_access_token(identity="logout_contract_str")

        body = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {fresh_token}"},
        ).get_json()

        assert isinstance(body["message"], str)


# ---------------------------------------------------------------------------
# CONTRACT 10 — Error response shape
# ---------------------------------------------------------------------------

class TestErrorResponseContract:
    """All 4xx / 5xx responses must conform to {error: {code, message}}."""

    def _assert_error_shape(self, body: Any, status_code: int) -> None:
        assert body is not None, f"Error response body must not be None (status={status_code})"
        assert "error" in body, f"Error body must have 'error' key (status={status_code})"
        error = body["error"]
        assert isinstance(error, dict), "'error' must be a dict"
        assert "code" in error, "'error' must contain 'code'"
        assert "message" in error, "'error' must contain 'message'"
        assert isinstance(error["code"], str), "'error.code' must be a string"
        assert isinstance(error["message"], str), "'error.message' must be a string"

    def test_invalid_property_id_error_shape(self, client: Any) -> None:
        """400 for bad property ID uses the structured error format."""
        response = client.get("/api/v1/properties/bad-id")
        self._assert_error_shape(response.get_json(), response.status_code)

    @patch("routes.properties.Property.find_by_id")
    def test_property_not_found_error_shape(
        self, mock_find: Any, client: Any
    ) -> None:
        """404 for missing property uses the structured error format."""
        mock_find.return_value = None
        response = client.get(f"/api/v1/properties/{_VALID_PROPERTY_ID}")
        self._assert_error_shape(response.get_json(), response.status_code)

    def test_invalid_analysis_id_error_shape(self, client: Any) -> None:
        """400 for bad analysis property ID uses the structured error format."""
        response = client.get("/api/v1/analysis/property/bad-id")
        self._assert_error_shape(response.get_json(), response.status_code)

    @patch("routes.analysis.Property.find_by_id")
    def test_analysis_not_found_error_shape(
        self, mock_find: Any, client: Any
    ) -> None:
        """404 for missing analysis property uses the structured error format."""
        mock_find.return_value = None
        response = client.get(f"/api/v1/analysis/property/{_VALID_PROPERTY_ID}")
        self._assert_error_shape(response.get_json(), response.status_code)

    def test_markets_invalid_metric_error_shape(self, client: Any) -> None:
        """400 for unknown market metric uses the structured error format."""
        response = client.get("/api/v1/markets/top?metric=unknown")
        self._assert_error_shape(response.get_json(), response.status_code)

    def test_post_property_requires_auth_error_shape(self, client: Any) -> None:
        """401 for unauthenticated POST /properties uses the structured error format."""
        response = client.post("/api/v1/properties", json={"address": "test"})
        # Flask-JWT-Extended returns its own error format; we verify at minimum
        # that a non-2xx code is returned and a body exists.
        assert response.status_code in (401, 422)
        assert response.get_json() is not None


# ---------------------------------------------------------------------------
# CONTRACT 11 — Pagination contract
# ---------------------------------------------------------------------------

class TestPaginationContract:
    """Pagination metadata must reflect the query parameters sent by the client."""

    def _mock_db(self, total: int = 50) -> MagicMock:
        db = MagicMock()
        db["properties"].count_documents.return_value = total
        return db

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_pagination_page_reflects_query_param(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """Response 'page' must equal the ?page= query parameter."""
        mock_find_all.return_value = []
        mock_get_db.return_value = self._mock_db()

        body = client.get("/api/v1/properties?page=3&limit=10").get_json()
        assert body["page"] == 3

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_pagination_limit_reflects_query_param(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """Response 'limit' must equal the ?limit= query parameter."""
        mock_find_all.return_value = []
        mock_get_db.return_value = self._mock_db()

        body = client.get("/api/v1/properties?page=1&limit=20").get_json()
        assert body["limit"] == 20

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_pagination_pages_is_ceiling_of_total_over_limit(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """'pages' must equal ceil(total / limit)."""
        mock_find_all.return_value = []
        mock_get_db.return_value = self._mock_db(total=55)

        body = client.get("/api/v1/properties?limit=10").get_json()
        expected_pages = -(-55 // 10)  # ceiling division = 6
        assert body["pages"] == expected_pages

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_pagination_total_comes_from_db_count(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """'total' must reflect the count from the database, not len(data)."""
        mock_find_all.return_value = []
        mock_get_db.return_value = self._mock_db(total=200)

        body = client.get("/api/v1/properties?limit=10").get_json()
        assert body["total"] == 200

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_pagination_limit_clamped_at_max_100(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """Requesting limit > 100 must be clamped to 100 by the backend."""
        mock_find_all.return_value = []
        mock_get_db.return_value = self._mock_db()

        body = client.get("/api/v1/properties?limit=999").get_json()
        assert body["limit"] <= 100

    @patch("routes.properties.Property.find_all")
    @patch("routes.properties.get_db")
    def test_pagination_default_page_is_1(
        self, mock_get_db: Any, mock_find_all: Any, client: Any
    ) -> None:
        """When no ?page= is given the default page is 1."""
        mock_find_all.return_value = []
        mock_get_db.return_value = self._mock_db()

        body = client.get("/api/v1/properties").get_json()
        assert body["page"] == 1
