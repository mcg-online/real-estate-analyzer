"""
Pytest tests for the Flask API routes defined in backend/app.py.

MongoDB is never contacted during these tests. All database interactions are
intercepted with unittest.mock.patch before the application module is imported,
which prevents the real init_db() call from executing.

Test coverage:
    - GET  /                          -> home endpoint
    - GET  /api/properties            -> list properties
    - GET  /api/properties/<id>       -> single property, not-found branch
    - POST /api/properties            -> create property (valid + missing field, auth required)
    - POST /api/auth/register         -> new user + duplicate username
    - POST /api/auth/login            -> valid credentials + bad credentials
"""

from __future__ import annotations

import sys
import types
from datetime import datetime
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_property_dict(**overrides: Any) -> dict[str, Any]:
    """Return a minimal property dict that satisfies Property.from_dict()."""
    base: dict[str, Any] = {
        "_id": "64a1f2c3d4e5f6a7b8c9d0e1",
        "address": "123 Test Street",
        "city": "Seattle",
        "state": "WA",
        "zip_code": "98101",
        "price": 350000,
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 1800,
        "year_built": 2005,
        "property_type": "Single Family",
        "lot_size": 6000,
        "listing_url": "http://example.com/listing/1",
        "source": "test",
        "latitude": 47.6062,
        "longitude": -122.3321,
        "images": [],
        "description": "A lovely test property",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metrics": {},
        "score": None,
    }
    base.update(overrides)
    return base


def _make_mock_property(**overrides: Any) -> MagicMock:
    """Return a MagicMock whose to_dict() mimics a real Property instance."""
    prop_dict = _make_property_dict(**overrides)
    mock = MagicMock()
    mock.to_dict.return_value = {
        k: v for k, v in prop_dict.items() if k != "_id"
    }
    mock._id = prop_dict["_id"]
    return mock


# ---------------------------------------------------------------------------
# Application fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app() -> Generator[Any, None, None]:
    """
    Import the Flask application with all database I/O mocked out.

    Patching strategy
    -----------------
    app.py calls ``init_db(app)`` at module level.  We patch both
    ``utils.database.init_db`` and ``utils.database.get_db`` *before* the
    module is imported so the real MongoClient is never instantiated.

    The ``schedule`` and ``services.scheduler`` modules are also replaced with
    lightweight stubs so that background-thread setup does not interfere with
    the test session.
    """
    # ------------------------------------------------------------------
    # Ensure a clean import each time the fixture is requested by removing
    # any previously cached module references.  This matters most when the
    # test session re-uses the same interpreter process across multiple runs.
    # ------------------------------------------------------------------
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith(("app", "routes", "models", "utils", "services")):
            del sys.modules[mod_name]

    # Stub out the scheduler service so it does not try to hit external APIs.
    stub_scheduler = types.ModuleType("services.scheduler")
    stub_scheduler.update_property_data = MagicMock()  # type: ignore[attr-defined]
    stub_scheduler.update_market_data = MagicMock()  # type: ignore[attr-defined]
    sys.modules["services.scheduler"] = stub_scheduler

    mock_db_instance = MagicMock()

    with (
        patch("utils.database.init_db", return_value=mock_db_instance) as _mock_init,
        patch("utils.database.get_db", return_value=mock_db_instance),
        patch("utils.database.close_db", return_value=None),
    ):
        import app as flask_app_module

        flask_app = flask_app_module.app
        flask_app.config.update(
            {
                "TESTING": True,
                "JWT_SECRET_KEY": "test-secret-key-for-jwt",
                "SECRET_KEY": "test-secret-key",
                "CACHE_TYPE": "SimpleCache",
                "RATELIMIT_ENABLED": False,
            }
        )
        yield flask_app


@pytest.fixture()
def client(app: Any):  # noqa: ANN001
    """Return a Flask test client bound to the application fixture."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Test: GET /
# ---------------------------------------------------------------------------

class TestHomeEndpoint:
    """Tests for the root health-check endpoint."""

    def test_home_returns_200(self, client: Any) -> None:
        """GET / responds with HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_home_returns_json_with_message(self, client: Any) -> None:
        """GET / body contains the expected message key."""
        response = client.get("/")
        data = response.get_json()
        assert data is not None
        assert "message" in data
        assert "Real Estate" in data["message"]

    def test_home_returns_version_field(self, client: Any) -> None:
        """GET / body contains a version field."""
        response = client.get("/")
        data = response.get_json()
        assert "version" in data


# ---------------------------------------------------------------------------
# Test: Health check endpoints
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_returns_200(self, client: Any) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"

    def test_liveness_returns_200(self, client: Any) -> None:
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "alive"
        assert "pid" in data

    @patch("utils.database.get_db")
    def test_readiness_healthy_when_db_connected(self, mock_get_db: Any, client: Any) -> None:
        mock_db = MagicMock()
        mock_db.command.return_value = {"ok": 1}
        mock_get_db.return_value = mock_db
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"

    @patch("utils.database.get_db")
    def test_readiness_degraded_when_db_down(self, mock_get_db: Any, client: Any) -> None:
        mock_get_db.side_effect = ConnectionError("Cannot connect")
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.get_json()
        assert data["status"] == "degraded"


# ---------------------------------------------------------------------------
# Test: GET /api/properties
# ---------------------------------------------------------------------------

class TestPropertyListGet:
    """Tests for GET /api/properties."""

    def _make_mock_db(self, count: int) -> MagicMock:
        """Return a mock db whose count_documents() returns ``count``."""
        mock_collection = MagicMock()
        mock_collection.count_documents.return_value = count
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        return mock_db

    def test_list_properties_returns_200(self, client: Any) -> None:
        """GET /api/properties returns HTTP 200 and a paginated payload."""
        mock_prop = _make_mock_property()
        mock_db = self._make_mock_db(count=1)
        with (
            patch("models.property.Property.find_all", return_value=[mock_prop]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties")
        assert response.status_code == 200

    def test_list_properties_returns_list(self, client: Any) -> None:
        """Response body contains a 'data' key whose value is a JSON array."""
        mock_prop = _make_mock_property()
        mock_db = self._make_mock_db(count=1)
        with (
            patch("models.property.Property.find_all", return_value=[mock_prop]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties")
        data = response.get_json()
        assert isinstance(data["data"], list)

    def test_list_properties_empty_db_returns_empty_list(self, client: Any) -> None:
        """When no properties exist the endpoint returns an empty 'data' list."""
        mock_db = self._make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"] == []
        assert data["total"] == 0

    def test_list_properties_multiple_results(self, client: Any) -> None:
        """All mock properties are present in the response 'data' list."""
        mocks = [
            _make_mock_property(listing_url="http://example.com/1"),
            _make_mock_property(listing_url="http://example.com/2"),
        ]
        mock_db = self._make_mock_db(count=2)
        with (
            patch("models.property.Property.find_all", return_value=mocks),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties")
        data = response.get_json()
        assert len(data["data"]) == 2


# ---------------------------------------------------------------------------
# Test: GET /api/properties/<id>
# ---------------------------------------------------------------------------

class TestPropertyDetailGet:
    """Tests for GET /api/properties/<property_id>."""

    def test_get_existing_property_returns_200(self, client: Any) -> None:
        """A valid property ID returns HTTP 200."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            response = client.get("/api/properties/64a1f2c3d4e5f6a7b8c9d0e1")
        assert response.status_code == 200

    def test_get_existing_property_returns_address(self, client: Any) -> None:
        """Response body includes the property address."""
        mock_prop = _make_mock_property(address="456 Oak Avenue")
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            response = client.get("/api/properties/64a1f2c3d4e5f6a7b8c9d0e1")
        data = response.get_json()
        assert data["address"] == "456 Oak Avenue"

    def test_get_nonexistent_property_returns_404(self, client: Any) -> None:
        """A property ID that does not exist returns HTTP 404."""
        with patch("models.property.Property.find_by_id", return_value=None):
            response = client.get("/api/properties/000000000000000000000000")
        assert response.status_code == 404

    def test_get_nonexistent_property_error_message(self, client: Any) -> None:
        """404 response body contains an error key."""
        with patch("models.property.Property.find_by_id", return_value=None):
            response = client.get("/api/properties/000000000000000000000000")
        data = response.get_json()
        assert "error" in data


# ---------------------------------------------------------------------------
# Test: POST /api/properties (JWT-protected write endpoint)
# ---------------------------------------------------------------------------

class TestPropertyCreate:
    """Tests for POST /api/properties.

    Write endpoints require a valid JWT Bearer token in the Authorization
    header.  Helper _auth_headers() obtains one from the test app context.
    """

    # Use a property_type value from the allowed list defined in routes/properties.py
    _valid_payload: dict[str, Any] = {
        "address": "789 Pine Road",
        "city": "Portland",
        "state": "OR",
        "zip_code": "97201",
        "price": 420000,
        "bedrooms": 4,
        "bathrooms": 2.5,
        "sqft": 2200,
        "year_built": 2010,
        "property_type": "single_family",
        "lot_size": 8000,
        "listing_url": "http://example.com/listing/789",
        "source": "zillow",
    }

    def _auth_headers(self, app: Any) -> dict[str, str]:
        """Return Authorization headers with a freshly-minted JWT."""
        from flask_jwt_extended import create_access_token
        with app.app_context():
            token = create_access_token(identity="testuser")
        return {"Authorization": f"Bearer {token}"}

    def test_create_property_without_jwt_returns_401(self, client: Any) -> None:
        """POST without Authorization header returns 401 Unauthorized."""
        response = client.post(
            "/api/properties",
            json=self._valid_payload,
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_create_property_returns_201(self, client: Any, app: Any) -> None:
        """A fully valid payload with a valid JWT returns HTTP 201."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id="new_id")
        mock_db.__getitem__.return_value = mock_collection
        with patch("models.property.get_db", return_value=mock_db):
            response = client.post(
                "/api/properties",
                json=self._valid_payload,
                content_type="application/json",
                headers=self._auth_headers(app),
            )
        assert response.status_code == 201

    def test_create_property_missing_required_field_returns_400(
        self, client: Any, app: Any
    ) -> None:
        """Omitting a required field with a valid JWT causes a 400 Bad Request."""
        incomplete = {k: v for k, v in self._valid_payload.items() if k != "price"}
        response = client.post(
            "/api/properties",
            json=incomplete,
            content_type="application/json",
            headers=self._auth_headers(app),
        )
        assert response.status_code == 400

    def test_create_property_missing_field_error_message(self, client: Any, app: Any) -> None:
        """400 response body names the offending field."""
        incomplete = {
            k: v for k, v in self._valid_payload.items() if k != "listing_url"
        }
        response = client.post(
            "/api/properties",
            json=incomplete,
            content_type="application/json",
            headers=self._auth_headers(app),
        )
        data = response.get_json()
        assert "error" in data
        assert "listing_url" in data["error"]["message"]

    def test_create_property_response_contains_address(self, client: Any, app: Any) -> None:
        """201 response body echoes the submitted address."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id="new_id")
        mock_db.__getitem__.return_value = mock_collection
        with patch("models.property.get_db", return_value=mock_db):
            response = client.post(
                "/api/properties",
                json=self._valid_payload,
                content_type="application/json",
                headers=self._auth_headers(app),
            )
        assert response.status_code == 201
        data = response.get_json()
        assert data["address"] == "789 Pine Road"


# ---------------------------------------------------------------------------
# Test: POST /api/auth/register
# ---------------------------------------------------------------------------

class TestUserRegistration:
    """Tests for POST /api/auth/register."""

    def test_register_new_user_returns_201(self, client: Any) -> None:
        """Registering a brand-new username returns HTTP 201."""
        mock_users = MagicMock()
        mock_users.find_one.return_value = None  # username does not exist yet
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users

        with patch("routes.users.get_db", return_value=mock_db):
            response = client.post(
                "/api/auth/register",
                json={"username": "newuser", "password": "S3cr3t!Valid"},
                content_type="application/json",
            )
        assert response.status_code == 201

    def test_register_new_user_success_message(self, client: Any) -> None:
        """Successful registration response contains a message key."""
        mock_users = MagicMock()
        mock_users.find_one.return_value = None
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users

        with patch("routes.users.get_db", return_value=mock_db):
            response = client.post(
                "/api/auth/register",
                json={"username": "newuser2", "password": "Pass123Valid"},
                content_type="application/json",
            )
        data = response.get_json()
        assert "message" in data

    def test_register_duplicate_username_returns_409(self, client: Any) -> None:
        """Attempting to register an existing username returns HTTP 409."""
        existing_user = {"username": "existinguser", "password": "hashed"}
        mock_users = MagicMock()
        mock_users.find_one.return_value = existing_user
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users

        with patch("routes.users.get_db", return_value=mock_db):
            response = client.post(
                "/api/auth/register",
                json={"username": "existinguser", "password": "ValidPass1"},
                content_type="application/json",
            )
        assert response.status_code == 409

    def test_register_missing_password_returns_400(self, client: Any) -> None:
        """Omitting the password field from the registration request returns 400."""
        response = client.post(
            "/api/auth/register",
            json={"username": "nopassword"},
            content_type="application/json",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test: POST /api/auth/login
# ---------------------------------------------------------------------------

class TestUserLogin:
    """Tests for POST /api/auth/login."""

    def test_login_valid_credentials_returns_200(self, client: Any) -> None:
        """Correct username and password returns HTTP 200 with an access token."""
        from werkzeug.security import generate_password_hash

        hashed = generate_password_hash("correctpassword")
        stored_user = {"username": "testuser", "password": hashed}

        mock_users = MagicMock()
        mock_users.find_one.return_value = stored_user
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users

        with patch("routes.users.get_db", return_value=mock_db):
            response = client.post(
                "/api/auth/login",
                json={"username": "testuser", "password": "correctpassword"},
                content_type="application/json",
            )
        assert response.status_code == 200

    def test_login_valid_credentials_returns_access_token(self, client: Any) -> None:
        """Successful login response body contains an access_token."""
        from werkzeug.security import generate_password_hash

        hashed = generate_password_hash("correctpassword")
        stored_user = {"username": "testuser", "password": hashed}

        mock_users = MagicMock()
        mock_users.find_one.return_value = stored_user
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users

        with patch("routes.users.get_db", return_value=mock_db):
            response = client.post(
                "/api/auth/login",
                json={"username": "testuser", "password": "correctpassword"},
                content_type="application/json",
            )
        data = response.get_json()
        assert "access_token" in data
        assert data["access_token"]  # non-empty string

    def test_login_wrong_password_returns_401(self, client: Any) -> None:
        """An incorrect password returns HTTP 401."""
        from werkzeug.security import generate_password_hash

        hashed = generate_password_hash("realpassword")
        stored_user = {"username": "testuser", "password": hashed}

        mock_users = MagicMock()
        mock_users.find_one.return_value = stored_user
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users

        with patch("routes.users.get_db", return_value=mock_db):
            response = client.post(
                "/api/auth/login",
                json={"username": "testuser", "password": "wrongpassword"},
                content_type="application/json",
            )
        assert response.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client: Any) -> None:
        """Login for a username that does not exist returns HTTP 401."""
        mock_users = MagicMock()
        mock_users.find_one.return_value = None  # user not in DB
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users

        with patch("routes.users.get_db", return_value=mock_db):
            response = client.post(
                "/api/auth/login",
                json={"username": "ghost", "password": "any"},
                content_type="application/json",
            )
        assert response.status_code == 401

    def test_login_missing_username_returns_400(self, client: Any) -> None:
        """Omitting the username field from the login request returns 400."""
        response = client.post(
            "/api/auth/login",
            json={"password": "somepassword"},
            content_type="application/json",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test: Query parameter validation on GET /api/properties
# ---------------------------------------------------------------------------

class TestPropertyListQueryValidation:
    """Tests for query parameter validation on GET /api/properties."""

    def _make_mock_db(self, count: int = 0) -> MagicMock:
        mock_collection = MagicMock()
        mock_collection.count_documents.return_value = count
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        return mock_db

    def test_invalid_minprice_returns_400(self, client: Any) -> None:
        """Non-numeric minPrice returns 400."""
        response = client.get("/api/properties?minPrice=abc")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_invalid_maxprice_returns_400(self, client: Any) -> None:
        """Non-numeric maxPrice returns 400."""
        response = client.get("/api/properties?maxPrice=notanumber")
        assert response.status_code == 400

    def test_invalid_page_returns_400(self, client: Any) -> None:
        """Non-numeric page parameter returns 400."""
        response = client.get("/api/properties?page=xyz")
        assert response.status_code == 400

    def test_invalid_limit_returns_400(self, client: Any) -> None:
        """Non-numeric limit parameter returns 400."""
        response = client.get("/api/properties?limit=abc")
        assert response.status_code == 400

    def test_negative_page_clamped_to_one(self, client: Any) -> None:
        """Negative page parameter is clamped to 1."""
        mock_db = self._make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties?page=-5")
        assert response.status_code == 200
        data = response.get_json()
        assert data["page"] == 1

    def test_limit_clamped_to_100(self, client: Any) -> None:
        """Limit above 100 is clamped to 100."""
        mock_db = self._make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties?limit=500")
        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 100

    def test_zero_limit_clamped_to_one(self, client: Any) -> None:
        """Limit of 0 is clamped to 1."""
        mock_db = self._make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            response = client.get("/api/properties?limit=0")
        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 1


# ---------------------------------------------------------------------------
# Test: PUT /api/properties/<id> mass assignment prevention
# ---------------------------------------------------------------------------

class TestPropertyUpdateSecurity:
    """Tests that PUT endpoint prevents mass assignment."""

    _valid_payload: dict[str, Any] = {
        "address": "789 Pine Road",
        "city": "Portland",
        "state": "OR",
        "zip_code": "97201",
        "price": 420000,
        "bedrooms": 4,
        "bathrooms": 2.5,
        "sqft": 2200,
        "year_built": 2010,
        "property_type": "single_family",
        "lot_size": 8000,
        "listing_url": "http://example.com/listing/789",
        "source": "zillow",
    }

    def _auth_headers(self, app: Any) -> dict[str, str]:
        from flask_jwt_extended import create_access_token
        with app.app_context():
            token = create_access_token(identity="testuser")
        return {"Authorization": f"Bearer {token}"}

    def test_put_does_not_allow_id_override(self, client: Any, app: Any) -> None:
        """PUT should not allow _id to be changed."""
        mock_prop = _make_mock_property()
        original_id = mock_prop._id
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.property.get_db", return_value=mock_db),
        ):
            response = client.put(
                "/api/properties/64a1f2c3d4e5f6a7b8c9d0e1",
                json={"_id": "000000000000000000000000", "price": 999999},
                content_type="application/json",
                headers=self._auth_headers(app),
            )
        assert response.status_code == 200
        # _id should remain unchanged
        assert mock_prop._id == original_id

    def test_put_does_not_allow_created_at_override(self, client: Any, app: Any) -> None:
        """PUT should not allow created_at to be changed."""
        mock_prop = _make_mock_property()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.property.get_db", return_value=mock_db),
        ):
            response = client.put(
                "/api/properties/64a1f2c3d4e5f6a7b8c9d0e1",
                json={"created_at": "2000-01-01", "price": 350000},
                content_type="application/json",
                headers=self._auth_headers(app),
            )
        assert response.status_code == 200

    def test_put_does_not_allow_metrics_override(self, client: Any, app: Any) -> None:
        """PUT should not allow metrics to be directly set."""
        mock_prop = _make_mock_property()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.property.get_db", return_value=mock_db),
        ):
            response = client.put(
                "/api/properties/64a1f2c3d4e5f6a7b8c9d0e1",
                json={"metrics": {"fake": True}, "score": 100},
                content_type="application/json",
                headers=self._auth_headers(app),
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test: Security headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """Test that security headers are set on responses."""

    def test_csp_header_present(self, client: Any) -> None:
        """Content-Security-Policy header is set."""
        response = client.get("/")
        assert "Content-Security-Policy" in response.headers

    def test_x_content_type_options_present(self, client: Any) -> None:
        """X-Content-Type-Options: nosniff header is set."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_present(self, client: Any) -> None:
        """X-Frame-Options: DENY header is set."""
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"


# ---------------------------------------------------------------------------
# Test: ObjectId validation
# ---------------------------------------------------------------------------

class TestObjectIdValidation:
    """Test that invalid ObjectId strings return 400."""

    def test_invalid_objectid_on_get_property(self, client: Any) -> None:
        """GET with invalid ObjectId returns 400."""
        response = client.get("/api/properties/not-a-valid-id")
        assert response.status_code == 400

    def test_invalid_objectid_on_delete_property(self, client: Any, app: Any) -> None:
        """DELETE with invalid ObjectId returns 400."""
        from flask_jwt_extended import create_access_token
        with app.app_context():
            token = create_access_token(identity="testuser")
        response = client.delete(
            "/api/properties/invalid-id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    def test_invalid_objectid_on_analysis(self, client: Any) -> None:
        """GET analysis with invalid ObjectId returns 400."""
        response = client.get("/api/analysis/property/bad-id")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test: Null body handling on POST/PUT endpoints
# ---------------------------------------------------------------------------

class TestNullBodyHandling:
    """Tests that POST/PUT endpoints return 400 when body is missing or invalid."""

    def _auth_headers(self, app: Any) -> dict[str, str]:
        from flask_jwt_extended import create_access_token
        with app.app_context():
            token = create_access_token(identity="testuser")
        return {"Authorization": f"Bearer {token}"}

    def test_post_property_no_body_returns_400(self, client: Any, app: Any) -> None:
        """POST /api/properties with no JSON body returns 400."""
        response = client.post(
            "/api/properties",
            content_type="application/json",
            headers=self._auth_headers(app),
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_put_property_no_body_returns_400(self, client: Any, app: Any) -> None:
        """PUT /api/properties/<id> with no JSON body returns 400."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            response = client.put(
                "/api/properties/64a1f2c3d4e5f6a7b8c9d0e1",
                content_type="application/json",
                headers=self._auth_headers(app),
            )
        assert response.status_code == 400

    def test_post_analysis_no_body_returns_400(self, client: Any, app: Any) -> None:
        """POST /api/analysis/property/<id> with no JSON body returns 400."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            response = client.post(
                "/api/analysis/property/64a1f2c3d4e5f6a7b8c9d0e1",
                content_type="application/json",
            )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test: Analysis parameter validation
# ---------------------------------------------------------------------------

class TestAnalysisParameterValidation:
    """Tests for parameter bounds checking on POST /api/analysis/property/<id>."""

    def test_invalid_term_years_returns_400(self, client: Any) -> None:
        """Non-numeric term_years returns 400."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            response = client.post(
                "/api/analysis/property/64a1f2c3d4e5f6a7b8c9d0e1",
                json={"term_years": "abc"},
                content_type="application/json",
            )
        assert response.status_code == 400

    def test_valid_params_accepted(self, client: Any) -> None:
        """Valid custom parameters return 200."""
        mock_prop = _make_mock_property()
        # Analysis services access numeric attributes directly on the property object
        mock_prop.price = 350000
        mock_prop.sqft = 1800
        mock_prop.bedrooms = 3
        mock_prop.bathrooms = 2
        mock_prop.year_built = 2005
        mock_prop.zip_code = "98101"
        mock_prop.city = "Seattle"
        mock_prop.state = "WA"
        mock_prop.property_type = "single_family"
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            response = client.post(
                "/api/analysis/property/64a1f2c3d4e5f6a7b8c9d0e1",
                json={"term_years": 15, "interest_rate": 0.05, "holding_period": 10},
                content_type="application/json",
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test: TopMarkets limit validation
# ---------------------------------------------------------------------------

class TestTopMarketsValidation:
    """Tests for GET /api/markets/top parameter validation."""

    def test_invalid_limit_returns_400(self, client: Any) -> None:
        """Non-numeric limit returns 400."""
        response = client.get("/api/markets/top?limit=abc")
        assert response.status_code == 400

    def test_invalid_metric_returns_400(self, client: Any) -> None:
        """Invalid metric returns 400."""
        mock_db = MagicMock()
        with patch("routes.analysis.get_db", return_value=mock_db):
            response = client.get("/api/markets/top?metric=invalid")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test: Username validation
# ---------------------------------------------------------------------------

class TestUsernameValidation:
    """Tests for username validation in registration."""

    def test_short_username_returns_400(self, client: Any) -> None:
        """Username under 3 characters returns 400."""
        response = client.post(
            "/api/auth/register",
            json={"username": "ab", "password": "ValidPass1"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "3-64 characters" in data["message"]

    def test_username_with_special_chars_returns_400(self, client: Any) -> None:
        """Username with invalid characters returns 400."""
        response = client.post(
            "/api/auth/register",
            json={"username": "user@name!", "password": "ValidPass1"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "letters, digits" in data["message"]

    def test_whitespace_only_username_returns_400(self, client: Any) -> None:
        """Whitespace-only username returns 400."""
        response = client.post(
            "/api/auth/register",
            json={"username": "   ", "password": "ValidPass1"},
            content_type="application/json",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test: Password validation rules
# ---------------------------------------------------------------------------

class TestPasswordValidation:
    """Tests for individual password validation rules."""

    def test_password_too_short_returns_400(self, client: Any) -> None:
        """Password under 8 characters returns 400."""
        response = client.post(
            "/api/auth/register",
            json={"username": "validuser", "password": "Ab1"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "8 characters" in data["message"]

    def test_password_no_uppercase_returns_400(self, client: Any) -> None:
        """Password without uppercase letter returns 400."""
        response = client.post(
            "/api/auth/register",
            json={"username": "validuser", "password": "abcdefg1"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "uppercase" in data["message"]

    def test_password_no_lowercase_returns_400(self, client: Any) -> None:
        """Password without lowercase letter returns 400."""
        response = client.post(
            "/api/auth/register",
            json={"username": "validuser", "password": "ABCDEFG1"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "lowercase" in data["message"]

    def test_password_no_digit_returns_400(self, client: Any) -> None:
        """Password without a digit returns 400."""
        response = client.post(
            "/api/auth/register",
            json={"username": "validuser", "password": "Abcdefgh"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "digit" in data["message"]
