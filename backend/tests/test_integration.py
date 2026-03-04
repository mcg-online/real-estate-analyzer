"""
Integration tests for cross-endpoint API flows.

These tests verify that multiple endpoints work correctly in sequence,
simulating real-world usage patterns: authentication followed by CRUD
operations, ownership enforcement across users, filtered searches,
analysis pipelines, error cascades, API versioning parity, and rate-limit
header presence.

Design principles
-----------------
- No real MongoDB is contacted. All database calls are intercepted via
  unittest.mock.patch at the import site (routes.*) or on the model
  class methods.
- Flask test client is used for all HTTP interactions.
- JWT tokens are created programmatically with flask_jwt_extended inside
  the application context so the test never needs a running auth server.
- Each cross-endpoint flow lives in its own test class for isolation.
- pytest.approx() is used wherever floating-point equality is asserted.
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

VALID_OBJECT_ID = "64a1f2c3d4e5f6a7b8c9d0e1"
ANOTHER_OBJECT_ID = "64a1f2c3d4e5f6a7b8c9d0e2"
NONEXISTENT_OBJECT_ID = "000000000000000000000000"
INVALID_OBJECT_ID = "not-a-valid-objectid"


def _make_property_dict(**overrides: Any) -> dict[str, Any]:
    """Return a minimal property dict compatible with Property.from_dict()."""
    base: dict[str, Any] = {
        "_id": VALID_OBJECT_ID,
        "address": "123 Integration Ave",
        "city": "Seattle",
        "state": "WA",
        "zip_code": "98101",
        "price": 350000,
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 1800,
        "year_built": 2005,
        "property_type": "single_family",
        "lot_size": 6000,
        "listing_url": "http://example.com/listing/integration-1",
        "source": "test",
        "latitude": 47.6062,
        "longitude": -122.3321,
        "images": [],
        "description": "An integration test property",
        "user_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {},
        "score": None,
    }
    base.update(overrides)
    return base


def _make_mock_property(**overrides: Any) -> MagicMock:
    """Return a MagicMock that behaves like a Property instance."""
    prop_dict = _make_property_dict(**overrides)
    mock = MagicMock()
    # to_dict() should return everything except _id so the route can
    # stringfy it separately.
    mock.to_dict.return_value = {k: v for k, v in prop_dict.items() if k != "_id"}
    mock._id = prop_dict["_id"]
    # user_id must be an explicit attribute (not an auto-created MagicMock
    # attribute) so that the ownership check `if property_owner is not None`
    # works correctly.
    mock.user_id = prop_dict.get("user_id")
    # Copy other attributes that services may read directly.
    for attr in ("price", "sqft", "bedrooms", "bathrooms", "year_built",
                 "property_type", "city", "state", "zip_code", "address"):
        setattr(mock, attr, prop_dict.get(attr))
    return mock


def _make_mock_db(count: int = 0) -> MagicMock:
    """Return a mock db whose collection count_documents returns ``count``."""
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = count
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    return mock_db


def _make_user_db(username: str, hashed_password: str) -> MagicMock:
    """Return a mock users collection that contains exactly one user."""
    stored_user = {"username": username, "password": hashed_password}
    mock_users = MagicMock()
    mock_users.find_one.return_value = stored_user
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_users
    return mock_db


# ---------------------------------------------------------------------------
# Application fixture (shared across all integration test classes)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app() -> Generator[Any, None, None]:
    """
    Boot the Flask application once with all DB and scheduler calls mocked.

    The module cache is cleared first so this fixture always gets a fresh
    import even when the test session re-uses the same interpreter process.
    """
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith(("app", "routes", "models", "utils", "services")):
            del sys.modules[mod_name]

    # Stub out the scheduler so it does not try to reach external services.
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
                "JWT_SECRET_KEY": "integration-test-secret-key",
                "SECRET_KEY": "integration-test-secret-key",
                "CACHE_TYPE": "SimpleCache",
                "RATELIMIT_ENABLED": False,
            }
        )
        yield flask_app


@pytest.fixture()
def client(app: Any) -> Any:
    """Return a test client bound to the shared application."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Shared JWT helpers
# ---------------------------------------------------------------------------

def _token_for(app: Any, identity: str) -> str:
    """Create a JWT access token for ``identity`` using the app context."""
    from flask_jwt_extended import create_access_token
    with app.app_context():
        return create_access_token(identity=identity)


def _auth_headers(app: Any, identity: str = "testuser") -> dict[str, str]:
    """Return Authorization headers with a freshly-minted JWT."""
    return {"Authorization": f"Bearer {_token_for(app, identity)}"}


# ---------------------------------------------------------------------------
# Payload constants
# ---------------------------------------------------------------------------

_VALID_PROPERTY_PAYLOAD: dict[str, Any] = {
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


# ===========================================================================
# FLOW 1: User Lifecycle
# Register -> Login -> Use token -> Logout -> Verify token revoked
# ===========================================================================

class TestUserLifecycleFlow:
    """
    End-to-end user authentication flow across multiple endpoints.

    Step 1 - Register: POST /api/v1/auth/register creates a new account.
    Step 2 - Login: POST /api/v1/auth/login returns a JWT.
    Step 3 - Protected access: token grants access to JWT-protected routes.
    Step 4 - Logout: POST /api/v1/auth/logout revokes the token.
    Step 5 - Post-logout: the same token is now rejected (401).
    """

    def _register_user(self, client: Any, username: str, password: str) -> Any:
        mock_users = MagicMock()
        mock_users.find_one.return_value = None  # username not taken
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users
        with patch("routes.users.get_db", return_value=mock_db):
            return client.post(
                "/api/v1/auth/register",
                json={"username": username, "password": password},
                content_type="application/json",
            )

    def test_register_new_user_returns_201(self, client: Any) -> None:
        """Step 1: Registration of a new user must return 201 Created."""
        resp = self._register_user(client, "lifecycle_user", "Lifecycle1Pass!")
        assert resp.status_code == 201
        data = resp.get_json()
        assert "message" in data

    def test_login_after_register_returns_token(self, client: Any) -> None:
        """Step 2: Login with correct credentials must return an access_token."""
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash("Lifecycle1Pass!")
        mock_db = _make_user_db("lifecycle_user", hashed)
        with patch("routes.users.get_db", return_value=mock_db):
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": "lifecycle_user", "password": "Lifecycle1Pass!"},
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_token_grants_access_to_protected_endpoint(
        self, client: Any, app: Any
    ) -> None:
        """Step 3: A valid token allows POST /api/v1/properties (JWT-protected)."""
        mock_db = _make_mock_db(count=0)
        mock_collection = mock_db.__getitem__.return_value
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id="new_prop_id")
        with patch("models.property.get_db", return_value=mock_db):
            resp = client.post(
                "/api/v1/properties",
                json=_VALID_PROPERTY_PAYLOAD,
                content_type="application/json",
                headers=_auth_headers(app, "lifecycle_user"),
            )
        assert resp.status_code == 201

    def test_logout_revokes_token(self, client: Any, app: Any) -> None:
        """Step 4: POST /api/v1/auth/logout returns 200 and a confirmation message."""
        token = _token_for(app, "lifecycle_user")
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/v1/auth/logout", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data
        assert "logged out" in data["message"].lower()

    def test_revoked_token_rejected_on_protected_endpoint(
        self, client: Any, app: Any
    ) -> None:
        """Step 5: After logout the same token must be rejected with 401."""
        # Obtain a fresh token and immediately revoke it via logout.
        token = _token_for(app, "lifecycle_user_revoke")
        headers = {"Authorization": f"Bearer {token}"}
        # Logout - this adds the jti to the blocklist.
        client.post("/api/v1/auth/logout", headers=headers)
        # Using the same (now-revoked) token on a protected endpoint must fail.
        mock_db = _make_mock_db(count=0)
        mock_collection = mock_db.__getitem__.return_value
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id="x")
        with patch("models.property.get_db", return_value=mock_db):
            resp = client.post(
                "/api/v1/properties",
                json=_VALID_PROPERTY_PAYLOAD,
                content_type="application/json",
                headers=headers,
            )
        assert resp.status_code == 401

    def test_no_token_rejected_with_401(self, client: Any) -> None:
        """Requests without any Authorization header must return 401."""
        resp = client.post(
            "/api/v1/properties",
            json=_VALID_PROPERTY_PAYLOAD,
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_duplicate_registration_returns_409(self, client: Any) -> None:
        """Registering an already-existing username must return 409 Conflict."""
        mock_users = MagicMock()
        mock_users.find_one.return_value = {"username": "existing_user"}
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users
        with patch("routes.users.get_db", return_value=mock_db):
            resp = client.post(
                "/api/v1/auth/register",
                json={"username": "existing_user", "password": "ValidPass1!"},
                content_type="application/json",
            )
        assert resp.status_code == 409

    def test_login_wrong_password_returns_401(self, client: Any) -> None:
        """Login with a wrong password must return 401 Unauthorized."""
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash("CorrectPass1!")
        mock_db = _make_user_db("lifecycle_user", hashed)
        with patch("routes.users.get_db", return_value=mock_db):
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": "lifecycle_user", "password": "WrongPass1!"},
                content_type="application/json",
            )
        assert resp.status_code == 401


# ===========================================================================
# FLOW 2: Property CRUD Flow
# Create -> Get by ID -> Update -> Verify updated -> Delete -> Verify 404
# ===========================================================================

class TestPropertyCRUDFlow:
    """
    Full create/read/update/delete lifecycle for a single property.
    """

    def _make_insert_db(self, inserted_id: str = VALID_OBJECT_ID) -> MagicMock:
        """Mock DB that records a successful insert."""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None  # no duplicate listing_url
        mock_collection.insert_one.return_value = MagicMock(inserted_id=inserted_id)
        mock_collection.count_documents.return_value = 0
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        return mock_db

    def test_create_property_returns_201_with_address(
        self, client: Any, app: Any
    ) -> None:
        """POST /api/v1/properties returns 201 and echoes the address."""
        mock_db = self._make_insert_db()
        with patch("models.property.get_db", return_value=mock_db):
            resp = client.post(
                "/api/v1/properties",
                json=_VALID_PROPERTY_PAYLOAD,
                content_type="application/json",
                headers=_auth_headers(app),
            )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["address"] == _VALID_PROPERTY_PAYLOAD["address"]

    def test_get_property_by_id_returns_200(self, client: Any) -> None:
        """GET /api/v1/properties/<id> returns 200 for an existing property."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            resp = client.get(f"/api/v1/properties/{VALID_OBJECT_ID}")
        assert resp.status_code == 200

    def test_get_property_contains_expected_fields(self, client: Any) -> None:
        """GET by ID response body contains address, price, and bedrooms."""
        mock_prop = _make_mock_property(price=350000, bedrooms=3)
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            resp = client.get(f"/api/v1/properties/{VALID_OBJECT_ID}")
        body = resp.get_json()
        assert "address" in body
        assert "price" in body
        assert "bedrooms" in body

    def test_update_property_returns_200_with_new_price(
        self, client: Any, app: Any
    ) -> None:
        """PUT /api/v1/properties/<id> returns 200 and reflects updated price."""
        # Build a mock property that user owns (user_id matches token identity).
        mock_prop = _make_mock_property(user_id="testuser")
        updated_dict = _make_property_dict(price=399000, user_id="testuser")
        del updated_dict["_id"]
        mock_prop.to_dict.return_value = updated_dict

        mock_db = self._make_insert_db()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.property.get_db", return_value=mock_db),
        ):
            resp = client.put(
                f"/api/v1/properties/{VALID_OBJECT_ID}",
                json={"price": 399000},
                content_type="application/json",
                headers=_auth_headers(app, "testuser"),
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["price"] == 399000

    def test_delete_property_returns_200(
        self, client: Any, app: Any
    ) -> None:
        """DELETE /api/v1/properties/<id> returns 200 with a success message."""
        mock_prop = _make_mock_property(user_id="testuser")
        mock_db = self._make_insert_db()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.delete(
                f"/api/v1/properties/{VALID_OBJECT_ID}",
                headers=_auth_headers(app, "testuser"),
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "message" in body
        assert "deleted" in body["message"].lower()

    def test_get_deleted_property_returns_404(self, client: Any) -> None:
        """After deletion GET by the same ID returns 404 Not Found."""
        with patch("models.property.Property.find_by_id", return_value=None):
            resp = client.get(f"/api/v1/properties/{NONEXISTENT_OBJECT_ID}")
        assert resp.status_code == 404

    def test_update_nonexistent_property_returns_404(
        self, client: Any, app: Any
    ) -> None:
        """PUT on a property ID that does not exist returns 404."""
        with patch("models.property.Property.find_by_id", return_value=None):
            resp = client.put(
                f"/api/v1/properties/{NONEXISTENT_OBJECT_ID}",
                json={"price": 300000},
                content_type="application/json",
                headers=_auth_headers(app),
            )
        assert resp.status_code == 404

    def test_delete_nonexistent_property_returns_404(
        self, client: Any, app: Any
    ) -> None:
        """DELETE on a property ID that does not exist returns 404."""
        with patch("models.property.Property.find_by_id", return_value=None):
            resp = client.delete(
                f"/api/v1/properties/{NONEXISTENT_OBJECT_ID}",
                headers=_auth_headers(app),
            )
        assert resp.status_code == 404


# ===========================================================================
# FLOW 3: Ownership Enforcement
# User A creates property -> User B update attempt (403) -> User A succeeds
# ===========================================================================

class TestOwnershipEnforcementFlow:
    """
    Verify that only the property creator can modify or delete a property,
    and that other authenticated users are denied with 403 Forbidden.
    """

    def _prop_owned_by(self, owner: str) -> MagicMock:
        mock_prop = _make_mock_property(user_id=owner)
        updated_dict = _make_property_dict(user_id=owner)
        del updated_dict["_id"]
        mock_prop.to_dict.return_value = updated_dict
        return mock_prop

    def _insert_db(self) -> MagicMock:
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        return mock_db

    def test_owner_can_update_own_property(
        self, client: Any, app: Any
    ) -> None:
        """The owning user (User A) can successfully PUT their property."""
        mock_prop = self._prop_owned_by("user_a")
        mock_db = self._insert_db()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.property.get_db", return_value=mock_db),
        ):
            resp = client.put(
                f"/api/v1/properties/{VALID_OBJECT_ID}",
                json={"price": 410000},
                content_type="application/json",
                headers=_auth_headers(app, "user_a"),
            )
        assert resp.status_code == 200

    def test_non_owner_update_returns_403(
        self, client: Any, app: Any
    ) -> None:
        """User B attempting to PUT User A's property must receive 403 Forbidden."""
        mock_prop = self._prop_owned_by("user_a")
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            resp = client.put(
                f"/api/v1/properties/{VALID_OBJECT_ID}",
                json={"price": 410000},
                content_type="application/json",
                headers=_auth_headers(app, "user_b"),
            )
        assert resp.status_code == 403

    def test_non_owner_delete_returns_403(
        self, client: Any, app: Any
    ) -> None:
        """User B attempting to DELETE User A's property must receive 403 Forbidden."""
        mock_prop = self._prop_owned_by("user_a")
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            resp = client.delete(
                f"/api/v1/properties/{VALID_OBJECT_ID}",
                headers=_auth_headers(app, "user_b"),
            )
        assert resp.status_code == 403

    def test_owner_can_delete_own_property(
        self, client: Any, app: Any
    ) -> None:
        """User A can successfully DELETE their own property."""
        mock_prop = self._prop_owned_by("user_a")
        mock_db = self._insert_db()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.delete(
                f"/api/v1/properties/{VALID_OBJECT_ID}",
                headers=_auth_headers(app, "user_a"),
            )
        assert resp.status_code == 200

    def test_legacy_property_no_owner_can_be_updated_by_any_user(
        self, client: Any, app: Any
    ) -> None:
        """Legacy properties (user_id=None) allow any authenticated user to update."""
        mock_prop = _make_mock_property(user_id=None)
        updated_dict = _make_property_dict()
        del updated_dict["_id"]
        mock_prop.to_dict.return_value = updated_dict
        mock_db = self._insert_db()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.property.get_db", return_value=mock_db),
        ):
            resp = client.put(
                f"/api/v1/properties/{VALID_OBJECT_ID}",
                json={"price": 300000},
                content_type="application/json",
                headers=_auth_headers(app, "any_user"),
            )
        assert resp.status_code == 200

    def test_forbidden_response_contains_error_key(
        self, client: Any, app: Any
    ) -> None:
        """403 response body must include a structured error envelope."""
        mock_prop = self._prop_owned_by("user_a")
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            resp = client.put(
                f"/api/v1/properties/{VALID_OBJECT_ID}",
                json={"price": 500000},
                content_type="application/json",
                headers=_auth_headers(app, "intruder"),
            )
        assert resp.status_code == 403
        body = resp.get_json()
        assert "error" in body


# ===========================================================================
# FLOW 4: Search and Filter Flow
# Multiple properties -> filter by price -> filter by city -> pagination check
# ===========================================================================

class TestSearchAndFilterFlow:
    """
    Verify that the property list endpoint correctly filters results and
    returns a paginated response envelope.
    """

    def _mock_list(self, props: list, count: int) -> tuple[MagicMock, MagicMock]:
        mock_db = _make_mock_db(count=count)
        find_all_mock = MagicMock(return_value=props)
        return mock_db, find_all_mock

    def test_list_endpoint_returns_pagination_envelope(
        self, client: Any
    ) -> None:
        """GET /api/v1/properties response has data, total, page, limit, pages keys."""
        mock_db = _make_mock_db(count=2)
        with (
            patch("models.property.Property.find_all",
                  return_value=[_make_mock_property(), _make_mock_property()]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties")
        assert resp.status_code == 200
        body = resp.get_json()
        for key in ("data", "total", "page", "limit", "pages"):
            assert key in body, f"Missing key: {key}"

    def test_price_filter_passes_correct_params(self, client: Any) -> None:
        """Numeric price filters produce a 200 response (mock validates call shape)."""
        mock_db = _make_mock_db(count=1)
        with (
            patch("models.property.Property.find_all",
                  return_value=[_make_mock_property(price=300000)]) as mock_find,
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties?minPrice=200000&maxPrice=400000")
        assert resp.status_code == 200
        # Property.find_all is called with keyword args; extract 'filters' safely.
        _args, _kwargs = mock_find.call_args
        filters_arg = _kwargs.get("filters", _args[0] if _args else {})
        assert "price" in filters_arg

    def test_city_filter_applied_to_query(self, client: Any) -> None:
        """city= query param is forwarded as a filter to Property.find_all."""
        mock_db = _make_mock_db(count=1)
        with (
            patch("models.property.Property.find_all",
                  return_value=[_make_mock_property(city="Boston")]) as mock_find,
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties?city=Boston")
        assert resp.status_code == 200
        _args, _kwargs = mock_find.call_args
        filters_arg = _kwargs.get("filters", _args[0] if _args else {})
        assert "city" in filters_arg
        assert filters_arg["city"] == "Boston"

    def test_pagination_page_and_limit_respected(self, client: Any) -> None:
        """page and limit parameters are reflected in the response envelope."""
        mock_db = _make_mock_db(count=50)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties?page=2&limit=10")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["page"] == 2
        assert body["limit"] == 10

    def test_pages_calculated_correctly(self, client: Any) -> None:
        """The pages field equals ceil(total/limit) via the -(-(n)//d) formula."""
        # count_documents must return an int, so we set it explicitly.
        mock_collection = MagicMock()
        mock_collection.count_documents.return_value = 25
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties?limit=10")
        body = resp.get_json()
        assert body["pages"] == 3  # ceil(25/10)

    def test_empty_result_set_returns_valid_envelope(self, client: Any) -> None:
        """An empty result set still returns a complete pagination envelope."""
        mock_db = _make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties?city=NonExistentCity")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"] == []
        assert body["total"] == 0
        assert body["pages"] == 0

    def test_state_filter_forwarded(self, client: Any) -> None:
        """state= query param is forwarded as a filter."""
        mock_db = _make_mock_db(count=3)
        with (
            patch("models.property.Property.find_all",
                  return_value=[_make_mock_property()]) as mock_find,
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties?state=CA")
        assert resp.status_code == 200
        _args, _kwargs = mock_find.call_args
        filters_arg = _kwargs.get("filters", _args[0] if _args else {})
        assert filters_arg.get("state") == "CA"


# ===========================================================================
# FLOW 5: Analysis Pipeline
# Create property -> Run GET analysis -> Check metric keys -> Run POST custom
# ===========================================================================

class TestAnalysisPipelineFlow:
    """
    Verify the analysis endpoints return correctly shaped results and that
    custom parameters (POST) produce different values from defaults (GET).
    """

    def _setup_property_mock(
        self, price: int = 350000, sqft: int = 1800
    ) -> MagicMock:
        prop = _make_mock_property(price=price, sqft=sqft)
        # Financial service reads these attributes directly.
        prop.price = price
        prop.sqft = sqft
        prop.city = "Seattle"
        prop.state = "WA"
        prop.zip_code = "98101"
        return prop

    def test_get_analysis_returns_200(self, client: Any) -> None:
        """GET /api/v1/analysis/property/<id> returns 200 for a valid property."""
        mock_prop = self._setup_property_mock()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            resp = client.get(f"/api/v1/analysis/property/{VALID_OBJECT_ID}")
        assert resp.status_code == 200

    def test_get_analysis_contains_required_top_level_keys(
        self, client: Any
    ) -> None:
        """Analysis response must include financial_analysis, tax_benefits, and financing_options."""
        mock_prop = self._setup_property_mock()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            resp = client.get(f"/api/v1/analysis/property/{VALID_OBJECT_ID}")
        body = resp.get_json()
        for key in ("financial_analysis", "tax_benefits", "financing_options", "market_data"):
            assert key in body, f"Missing key: {key}"

    def test_get_analysis_financial_contains_metric_keys(
        self, client: Any
    ) -> None:
        """financial_analysis block must include cap_rate, monthly_cash_flow, and roi."""
        mock_prop = self._setup_property_mock()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            resp = client.get(f"/api/v1/analysis/property/{VALID_OBJECT_ID}")
        body = resp.get_json()
        fa = body.get("financial_analysis", {})
        for metric in ("cap_rate", "monthly_cash_flow", "roi", "mortgage_payment"):
            assert metric in fa, f"Missing financial metric: {metric}"

    def test_post_custom_analysis_returns_200(self, client: Any) -> None:
        """POST /api/v1/analysis/property/<id> with custom params returns 200."""
        mock_prop = self._setup_property_mock()
        custom_params = {
            "down_payment_percentage": 0.25,
            "interest_rate": 0.06,
            "term_years": 20,
            "holding_period": 7,
            "appreciation_rate": 0.04,
        }
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            resp = client.post(
                f"/api/v1/analysis/property/{VALID_OBJECT_ID}",
                json=custom_params,
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_post_custom_analysis_echoes_parameters(self, client: Any) -> None:
        """Custom analysis response body echoes back the submitted parameters."""
        mock_prop = self._setup_property_mock()
        custom_params = {"down_payment_percentage": 0.30, "interest_rate": 0.05}
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            resp = client.post(
                f"/api/v1/analysis/property/{VALID_OBJECT_ID}",
                json=custom_params,
                content_type="application/json",
            )
        body = resp.get_json()
        assert "parameters" in body
        assert body["parameters"]["down_payment_percentage"] == pytest.approx(0.30, abs=0.001)

    def test_opportunity_score_returns_200_with_property_id(
        self, client: Any
    ) -> None:
        """GET /api/v1/analysis/score/<id> returns 200 and includes property_id."""
        mock_prop = self._setup_property_mock()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            resp = client.get(f"/api/v1/analysis/score/{VALID_OBJECT_ID}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "property_id" in body

    def test_analysis_nonexistent_property_returns_404(
        self, client: Any
    ) -> None:
        """Analysis of a non-existent property must return 404."""
        with patch("models.property.Property.find_by_id", return_value=None):
            resp = client.get(
                f"/api/v1/analysis/property/{NONEXISTENT_OBJECT_ID}"
            )
        assert resp.status_code == 404


# ===========================================================================
# FLOW 6: Error Cascades
# Invalid ObjectId -> Missing fields -> Null body -> Invalid pagination
# ===========================================================================

class TestErrorCascadesFlow:
    """
    Verify that invalid inputs are consistently rejected with appropriate
    HTTP status codes and structured error response bodies.
    """

    def test_invalid_objectid_get_property_returns_400(
        self, client: Any
    ) -> None:
        """GET /api/v1/properties/<invalid_id> returns 400 (not 500)."""
        resp = client.get(f"/api/v1/properties/{INVALID_OBJECT_ID}")
        assert resp.status_code == 400

    def test_invalid_objectid_put_property_returns_400(
        self, client: Any, app: Any
    ) -> None:
        """PUT with an invalid ObjectId format returns 400."""
        resp = client.put(
            f"/api/v1/properties/{INVALID_OBJECT_ID}",
            json={"price": 100000},
            content_type="application/json",
            headers=_auth_headers(app),
        )
        assert resp.status_code == 400

    def test_invalid_objectid_delete_property_returns_400(
        self, client: Any, app: Any
    ) -> None:
        """DELETE with an invalid ObjectId format returns 400."""
        resp = client.delete(
            f"/api/v1/properties/{INVALID_OBJECT_ID}",
            headers=_auth_headers(app),
        )
        assert resp.status_code == 400

    def test_invalid_objectid_analysis_returns_400(self, client: Any) -> None:
        """GET analysis with an invalid ID returns 400."""
        resp = client.get(f"/api/v1/analysis/property/{INVALID_OBJECT_ID}")
        assert resp.status_code == 400

    def test_missing_required_field_on_create_returns_400(
        self, client: Any, app: Any
    ) -> None:
        """POST /api/v1/properties without 'price' returns 400."""
        payload = {k: v for k, v in _VALID_PROPERTY_PAYLOAD.items() if k != "price"}
        resp = client.post(
            "/api/v1/properties",
            json=payload,
            content_type="application/json",
            headers=_auth_headers(app),
        )
        assert resp.status_code == 400

    def test_missing_multiple_fields_returns_400_with_error(
        self, client: Any, app: Any
    ) -> None:
        """POST /api/v1/properties with only address returns 400 with error body."""
        resp = client.post(
            "/api/v1/properties",
            json={"address": "Only an address"},
            content_type="application/json",
            headers=_auth_headers(app),
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "error" in body

    def test_null_body_on_create_returns_400(self, client: Any, app: Any) -> None:
        """POST with Content-Type application/json but empty body returns 400."""
        resp = client.post(
            "/api/v1/properties",
            data="",
            content_type="application/json",
            headers=_auth_headers(app),
        )
        assert resp.status_code == 400

    def test_null_body_on_custom_analysis_returns_400(
        self, client: Any
    ) -> None:
        """POST /api/v1/analysis/property/<id> with empty body returns 400."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            resp = client.post(
                f"/api/v1/analysis/property/{VALID_OBJECT_ID}",
                data="",
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_non_numeric_min_price_returns_400(self, client: Any) -> None:
        """minPrice=abc triggers validation error and returns 400."""
        resp = client.get("/api/v1/properties?minPrice=abc")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_non_numeric_page_returns_400(self, client: Any) -> None:
        """page=xyz triggers validation error and returns 400."""
        resp = client.get("/api/v1/properties?page=xyz")
        assert resp.status_code == 400

    def test_error_response_has_structured_error_body(
        self, client: Any
    ) -> None:
        """All 400 error responses use the {error: {code, message}} envelope."""
        resp = client.get(f"/api/v1/properties/{INVALID_OBJECT_ID}")
        assert resp.status_code == 400
        body = resp.get_json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    def test_not_found_property_returns_structured_404(
        self, client: Any
    ) -> None:
        """404 responses also use the structured error envelope."""
        with patch("models.property.Property.find_by_id", return_value=None):
            resp = client.get(f"/api/v1/properties/{NONEXISTENT_OBJECT_ID}")
        assert resp.status_code == 404
        body = resp.get_json()
        assert "error" in body


# ===========================================================================
# FLOW 7: API Versioning Parity
# Same requests to /api/v1/* and /api/* return identical responses
# ===========================================================================

class TestAPIVersioningParityFlow:
    """
    Verify that every endpoint registered at both /api/v1/* and /api/* paths
    returns the same HTTP status code and equivalent response shape.
    """

    def test_home_endpoint_not_versioned_returns_200(
        self, client: Any
    ) -> None:
        """GET / returns 200 and mentions the current API version."""
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "api_versions" in body or "current_api" in body

    def test_get_properties_v1_and_legacy_return_same_status(
        self, client: Any
    ) -> None:
        """GET /api/v1/properties and GET /api/properties must both return 200."""
        mock_db = _make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            v1_resp = client.get("/api/v1/properties")
            legacy_resp = client.get("/api/properties")
        assert v1_resp.status_code == 200
        assert legacy_resp.status_code == 200

    def test_get_properties_v1_and_legacy_have_same_envelope_keys(
        self, client: Any
    ) -> None:
        """Both versioned paths return the same pagination envelope keys."""
        mock_db = _make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            v1_body = client.get("/api/v1/properties").get_json()
            legacy_body = client.get("/api/properties").get_json()
        assert set(v1_body.keys()) == set(legacy_body.keys())

    def test_register_endpoint_available_on_both_paths(
        self, client: Any
    ) -> None:
        """POST /api/v1/auth/register and POST /api/auth/register both respond."""
        mock_users = MagicMock()
        mock_users.find_one.return_value = None
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_users
        with patch("routes.users.get_db", return_value=mock_db):
            v1_resp = client.post(
                "/api/v1/auth/register",
                json={"username": "parity_user_v1", "password": "ParityPass1!"},
                content_type="application/json",
            )
        with patch("routes.users.get_db", return_value=mock_db):
            legacy_resp = client.post(
                "/api/auth/register",
                json={"username": "parity_user_leg", "password": "ParityPass1!"},
                content_type="application/json",
            )
        assert v1_resp.status_code == 201
        assert legacy_resp.status_code == 201

    def test_analysis_endpoint_available_on_both_paths(
        self, client: Any
    ) -> None:
        """Both /api/v1/analysis/property/<id> and /api/analysis/property/<id> return 200."""
        mock_prop = _make_mock_property()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            v1_resp = client.get(f"/api/v1/analysis/property/{VALID_OBJECT_ID}")
            legacy_resp = client.get(f"/api/analysis/property/{VALID_OBJECT_ID}")
        assert v1_resp.status_code == 200
        assert legacy_resp.status_code == 200

    def test_invalid_objectid_rejected_on_both_versioned_paths(
        self, client: Any
    ) -> None:
        """400 validation errors work identically on v1 and legacy paths."""
        v1_resp = client.get(f"/api/v1/properties/{INVALID_OBJECT_ID}")
        legacy_resp = client.get(f"/api/properties/{INVALID_OBJECT_ID}")
        assert v1_resp.status_code == 400
        assert legacy_resp.status_code == 400

    def test_get_single_property_v1_and_legacy_return_same_body_shape(
        self, client: Any
    ) -> None:
        """Both versioned paths for GET /<id> return the same top-level field names."""
        mock_prop = _make_mock_property()
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            v1_body = client.get(f"/api/v1/properties/{VALID_OBJECT_ID}").get_json()
        with patch("models.property.Property.find_by_id", return_value=mock_prop):
            legacy_body = client.get(f"/api/properties/{VALID_OBJECT_ID}").get_json()
        assert set(v1_body.keys()) == set(legacy_body.keys())

    def test_top_markets_available_on_both_paths(self, client: Any) -> None:
        """GET /api/v1/markets/top and GET /api/markets/top both respond with 200."""
        mock_db = MagicMock()
        mock_aggregator = MagicMock()
        mock_aggregator.top_markets_by_roi.return_value = []
        with (
            patch("routes.analysis.get_db", return_value=mock_db),
            patch(
                "routes.analysis.MarketAggregator",
                return_value=mock_aggregator,
            ),
        ):
            v1_resp = client.get("/api/v1/markets/top")
            legacy_resp = client.get("/api/markets/top")
        assert v1_resp.status_code == 200
        assert legacy_resp.status_code == 200


# ===========================================================================
# FLOW 8: Rate Limiting Headers
# Verify rate-limit headers are present on responses
# ===========================================================================

class TestRateLimitHeadersFlow:
    """
    Verify that rate-limit related headers are present in API responses.
    Because RATELIMIT_ENABLED=False in the test config, the Flask-Limiter
    headers (X-RateLimit-Limit, X-RateLimit-Remaining) may not be injected;
    however our custom security headers (set in app.after_request) must
    always be present, and we also verify the app does not reject requests
    that are well within any limit.
    """

    def test_security_headers_present_on_property_list(
        self, client: Any
    ) -> None:
        """Security headers are added to every response by after_request hook."""
        mock_db = _make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_security_headers_present_on_auth_endpoints(
        self, client: Any
    ) -> None:
        """Auth endpoints also carry security headers."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "a", "password": "b"},
            content_type="application/json",
        )
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_security_headers_present_on_analysis_endpoint(
        self, client: Any
    ) -> None:
        """Analysis endpoint responses carry the X-Content-Type-Options header."""
        mock_prop = _make_mock_property()
        with (
            patch("models.property.Property.find_by_id", return_value=mock_prop),
            patch("models.market.Market.find_by_location", return_value=None),
        ):
            resp = client.get(f"/api/v1/analysis/property/{VALID_OBJECT_ID}")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_referrer_policy_header_present(self, client: Any) -> None:
        """Referrer-Policy header is set on every response."""
        mock_db = _make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties")
        assert "Referrer-Policy" in resp.headers

    def test_csp_header_present(self, client: Any) -> None:
        """Content-Security-Policy header is present."""
        mock_db = _make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            resp = client.get("/api/v1/properties")
        assert "Content-Security-Policy" in resp.headers

    def test_many_sequential_requests_all_succeed(
        self, client: Any
    ) -> None:
        """10 sequential GET requests all return 200 (well within any rate limit)."""
        mock_db = _make_mock_db(count=0)
        with (
            patch("models.property.Property.find_all", return_value=[]),
            patch("routes.properties.get_db", return_value=mock_db),
        ):
            for _ in range(10):
                resp = client.get("/api/v1/properties")
                assert resp.status_code == 200

    def test_health_endpoint_accessible_without_auth(
        self, client: Any
    ) -> None:
        """GET /health does not require JWT and returns 200."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_liveness_endpoint_has_security_headers(
        self, client: Any
    ) -> None:
        """GET /health/live carries the standard security headers."""
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.headers.get("X-Frame-Options") == "DENY"
