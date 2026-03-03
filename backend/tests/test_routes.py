"""
Pytest tests for the Flask API routes defined in backend/app.py.

MongoDB is never contacted during these tests. All database interactions are
intercepted with unittest.mock.patch before the application module is imported,
which prevents the real init_db() call from executing.

Test coverage:
    - GET  /                          -> home endpoint
    - GET  /api/properties            -> list properties
    - GET  /api/properties/<id>       -> single property, not-found branch
    - POST /api/properties            -> create property (valid + missing field)
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
        assert data["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Test: GET /api/properties
# ---------------------------------------------------------------------------

class TestPropertyListGet:
    """Tests for GET /api/properties."""

    def test_list_properties_returns_200(self, client: Any) -> None:
        """GET /api/properties returns HTTP 200 and a list payload."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_all", return_value=[mock_prop]):
            response = client.get("/api/properties")
        assert response.status_code == 200

    def test_list_properties_returns_list(self, client: Any) -> None:
        """Response body is a JSON array."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_all", return_value=[mock_prop]):
            response = client.get("/api/properties")
        data = response.get_json()
        assert isinstance(data, list)

    def test_list_properties_empty_db_returns_empty_list(self, client: Any) -> None:
        """When no properties exist the endpoint returns an empty list."""
        with patch("models.property.Property.find_all", return_value=[]):
            response = client.get("/api/properties")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_properties_multiple_results(self, client: Any) -> None:
        """All mock properties are present in the response."""
        mocks = [
            _make_mock_property(listing_url="http://example.com/1"),
            _make_mock_property(listing_url="http://example.com/2"),
        ]
        with patch("models.property.Property.find_all", return_value=mocks):
            response = client.get("/api/properties")
        data = response.get_json()
        assert len(data) == 2


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
# Test: POST /api/properties
# ---------------------------------------------------------------------------

class TestPropertyCreate:
    """Tests for POST /api/properties."""

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
        "property_type": "Single Family",
        "lot_size": 8000,
        "listing_url": "http://example.com/listing/789",
        "source": "zillow",
    }

    def test_create_property_returns_201(self, client: Any) -> None:
        """A fully valid payload returns HTTP 201."""
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
            )
        assert response.status_code == 201

    def test_create_property_missing_required_field_returns_400(
        self, client: Any
    ) -> None:
        """Omitting a required field causes a 400 Bad Request."""
        incomplete = {k: v for k, v in self._valid_payload.items() if k != "price"}
        response = client.post(
            "/api/properties",
            json=incomplete,
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_create_property_missing_field_error_message(self, client: Any) -> None:
        """400 response body names the offending field."""
        incomplete = {
            k: v for k, v in self._valid_payload.items() if k != "listing_url"
        }
        response = client.post(
            "/api/properties",
            json=incomplete,
            content_type="application/json",
        )
        data = response.get_json()
        assert "error" in data
        assert "listing_url" in data["error"]

    def test_create_property_response_contains_address(self, client: Any) -> None:
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
                json={"username": "newuser", "password": "s3cr3t!"},
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
                json={"username": "newuser2", "password": "pass123"},
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
                json={"username": "existinguser", "password": "any"},
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
