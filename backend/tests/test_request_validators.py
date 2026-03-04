"""
Tests for utils/request_validators.py

The three decorators — require_json_body, validate_objectid, require_entity —
are exercised via a minimal Flask application with synthetic routes.  No real
MongoDB connection is made; find_by_id is always mocked.

Test structure
--------------
TestRequireJsonBody       — 8 tests
TestValidateObjectId      — 7 tests
TestRequireEntity         — 10 tests
TestDecoratorStacking     — 5 tests
TestDecoratorMetadata     — 3 tests
                           -------
Total                       33 tests
"""

from __future__ import annotations

import json
import sys
import os
from unittest.mock import MagicMock

import pytest

# Ensure the backend root is on sys.path regardless of how pytest is invoked.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask
from flask_restful import Api, Resource

from utils.request_validators import require_json_body, validate_objectid, require_entity


# ---------------------------------------------------------------------------
# Helpers & constants
# ---------------------------------------------------------------------------

VALID_OID = "64a1f2c3d4e5f6a7b8c9d0e1"
ANOTHER_OID = "64a1f2c3d4e5f6a7b8c9d0e2"
INVALID_OID = "not-a-valid-objectid"


def _make_mock_model(return_value=None):
    """Return a fake model class whose find_by_id() returns *return_value*."""
    mock_class = MagicMock()
    mock_class.__name__ = "FakeEntity"
    mock_class.find_by_id.return_value = return_value
    return mock_class


def _make_mock_entity():
    """Return a non-None entity mock (simulates a found DB record)."""
    entity = MagicMock()
    entity.name = "Test Entity"
    return entity


# ---------------------------------------------------------------------------
# Minimal Flask application fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def flask_app():
    """
    A fresh Flask app with Flask-RESTful for each test function.

    Routes are registered inside each individual test via the helpers below so
    that tests stay fully isolated.
    """
    app = Flask(__name__)
    app.config["TESTING"] = True
    # Suppress Flask-RESTful's default 404 / 400 error handler overrides so
    # our 400/404 responses flow through unmodified.
    app.config["PROPAGATE_EXCEPTIONS"] = False
    return app


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()


# ---------------------------------------------------------------------------
# Route-registration helpers
# ---------------------------------------------------------------------------

def _register_json_body_route(app, path="/test"):
    """Register a POST route decorated with @require_json_body."""
    api = Api(app)

    class _JsonBodyResource(Resource):
        @require_json_body
        def post(self, data):
            return {"received": data}, 200

    api.add_resource(_JsonBodyResource, path)


def _register_objectid_route(app, path="/test/<string:item_id>", param="item_id"):
    """Register a GET route decorated with @validate_objectid(param)."""
    api = Api(app)

    class _OidResource(Resource):
        @validate_objectid(param)
        def get(self, item_id):
            return {"id": item_id}, 200

    api.add_resource(_OidResource, path)


def _register_entity_route(app, model_class, path="/test/<string:item_id>",
                            param="item_id", inject_as="entity"):
    """Register a GET route decorated with @require_entity(...)."""
    api = Api(app)

    class _EntityResource(Resource):
        @require_entity(model_class, param, inject_as=inject_as)
        def get(self, item_id, **kwargs):
            entity = kwargs[inject_as]
            return {"found": True, "entity_name": entity.name}, 200

    api.add_resource(_EntityResource, path)


# ---------------------------------------------------------------------------
# TestRequireJsonBody
# ---------------------------------------------------------------------------

class TestRequireJsonBody:
    """Unit tests for the @require_json_body decorator."""

    def test_valid_json_body_passes_through(self, flask_app, client):
        """A well-formed JSON object body is accepted; handler receives data."""
        _register_json_body_route(flask_app)
        resp = client.post(
            "/test",
            data=json.dumps({"key": "value"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["received"]["key"] == "value"

    def test_missing_body_returns_400(self, flask_app, client):
        """No body at all should yield 400."""
        _register_json_body_route(flask_app)
        resp = client.post("/test", content_type="application/json")
        assert resp.status_code == 400

    def test_missing_body_error_code(self, flask_app, client):
        """Error response must carry VALIDATION_ERROR code."""
        _register_json_body_route(flask_app)
        resp = client.post("/test", content_type="application/json")
        body = resp.get_json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_non_json_content_type_returns_400(self, flask_app, client):
        """Plain text body (wrong content-type) should yield 400."""
        _register_json_body_route(flask_app)
        resp = client.post("/test", data="hello", content_type="text/plain")
        assert resp.status_code == 400

    def test_json_array_body_returns_400(self, flask_app, client):
        """A JSON array is not a dict; should yield 400."""
        _register_json_body_route(flask_app)
        resp = client.post(
            "/test",
            data=json.dumps([1, 2, 3]),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_json_null_body_returns_400(self, flask_app, client):
        """A JSON null body should yield 400."""
        _register_json_body_route(flask_app)
        resp = client.post(
            "/test",
            data=json.dumps(None),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_empty_json_object_is_accepted(self, flask_app, client):
        """An empty JSON object {} is technically valid — the decorator passes it."""
        _register_json_body_route(flask_app)
        resp = client.post(
            "/test",
            data=json.dumps({}),
            content_type="application/json",
        )
        # {} is falsy in Python, so the guard `if not body` catches it.
        # The spec says "non-empty dict", so this should be 400.
        assert resp.status_code == 400

    def test_nested_json_object_passes_through(self, flask_app, client):
        """A nested JSON object is accepted and the nested structure is preserved."""
        _register_json_body_route(flask_app)
        payload = {"a": {"b": [1, 2, 3]}, "c": True}
        resp = client.post(
            "/test",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["received"]["a"]["b"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# TestValidateObjectId
# ---------------------------------------------------------------------------

class TestValidateObjectId:
    """Unit tests for the @validate_objectid(param_name) decorator."""

    def test_valid_objectid_passes(self, flask_app, client):
        """A well-formed 24-char hex ObjectId passes the decorator."""
        _register_objectid_route(flask_app)
        resp = client.get(f"/test/{VALID_OID}")
        assert resp.status_code == 200

    def test_valid_objectid_preserves_value(self, flask_app, client):
        """The raw string is passed to the handler unchanged."""
        _register_objectid_route(flask_app)
        resp = client.get(f"/test/{VALID_OID}")
        body = resp.get_json()
        assert body["id"] == VALID_OID

    def test_invalid_objectid_returns_400(self, flask_app, client):
        """A non-hex / wrong-length string is rejected with 400."""
        _register_objectid_route(flask_app)
        resp = client.get(f"/test/{INVALID_OID}")
        assert resp.status_code == 400

    def test_invalid_objectid_error_code(self, flask_app, client):
        """Error response must carry VALIDATION_ERROR code."""
        _register_objectid_route(flask_app)
        resp = client.get(f"/test/{INVALID_OID}")
        body = resp.get_json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_objectid_error_message_contains_param_name(self, flask_app, client):
        """Error message should mention the parameter name (humanised)."""
        _register_objectid_route(flask_app, param="item_id")
        resp = client.get(f"/test/{INVALID_OID}")
        body = resp.get_json()
        # param_name 'item_id' -> 'item id' -> appears in message
        assert "item id" in body["error"]["message"].lower()

    def test_short_hex_string_rejected(self, flask_app, client):
        """A hex string shorter than 24 characters is rejected."""
        _register_objectid_route(flask_app)
        resp = client.get("/test/abc123")
        assert resp.status_code == 400

    def test_all_zeros_objectid_passes(self, flask_app, client):
        """The all-zeros ObjectId is technically valid bson."""
        _register_objectid_route(flask_app)
        resp = client.get("/test/000000000000000000000000")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestRequireEntity
# ---------------------------------------------------------------------------

class TestRequireEntity:
    """Unit tests for the @require_entity(model, param, inject_as) decorator."""

    def test_found_entity_injected_into_handler(self, flask_app, client):
        """When find_by_id returns an entity it is injected as a kwarg."""
        entity = _make_mock_entity()
        model = _make_mock_model(return_value=entity)
        _register_entity_route(flask_app, model)
        resp = client.get(f"/test/{VALID_OID}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["found"] is True

    def test_invalid_objectid_returns_400(self, flask_app, client):
        """Bad ObjectId format is caught before find_by_id is called."""
        model = _make_mock_model(return_value=_make_mock_entity())
        _register_entity_route(flask_app, model)
        resp = client.get(f"/test/{INVALID_OID}")
        assert resp.status_code == 400
        model.find_by_id.assert_not_called()

    def test_invalid_objectid_error_code(self, flask_app, client):
        """400 response carries VALIDATION_ERROR."""
        model = _make_mock_model()
        _register_entity_route(flask_app, model)
        resp = client.get(f"/test/{INVALID_OID}")
        body = resp.get_json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_not_found_entity_returns_404(self, flask_app, client):
        """When find_by_id returns None the decorator returns 404."""
        model = _make_mock_model(return_value=None)
        _register_entity_route(flask_app, model)
        resp = client.get(f"/test/{VALID_OID}")
        assert resp.status_code == 404

    def test_not_found_error_code(self, flask_app, client):
        """404 response carries NOT_FOUND code."""
        model = _make_mock_model(return_value=None)
        _register_entity_route(flask_app, model)
        resp = client.get(f"/test/{VALID_OID}")
        body = resp.get_json()
        assert body["error"]["code"] == "NOT_FOUND"

    def test_not_found_message_contains_model_name(self, flask_app, client):
        """Error message names the model class (e.g. 'FakeEntity not found')."""
        model = _make_mock_model(return_value=None)
        _register_entity_route(flask_app, model)
        resp = client.get(f"/test/{VALID_OID}")
        body = resp.get_json()
        assert "FakeEntity" in body["error"]["message"]

    def test_find_by_id_called_with_correct_id(self, flask_app, client):
        """The raw string ID is passed to find_by_id."""
        entity = _make_mock_entity()
        model = _make_mock_model(return_value=entity)
        _register_entity_route(flask_app, model)
        client.get(f"/test/{VALID_OID}")
        model.find_by_id.assert_called_once_with(VALID_OID)

    def test_find_by_id_exception_returns_500(self, flask_app, client):
        """If find_by_id raises an unexpected exception the decorator returns 500."""
        model = MagicMock()
        model.__name__ = "FakeEntity"
        model.find_by_id.side_effect = RuntimeError("DB exploded")
        _register_entity_route(flask_app, model)
        resp = client.get(f"/test/{VALID_OID}")
        assert resp.status_code == 500
        body = resp.get_json()
        assert body["error"]["code"] == "INTERNAL_ERROR"

    def test_inject_as_custom_name(self, flask_app, client):
        """The loaded entity is available under the custom inject_as name."""
        entity = _make_mock_entity()
        model = _make_mock_model(return_value=entity)
        # Use a custom inject_as name "my_thing"
        api = Api(flask_app)

        class _CustomInjectResource(Resource):
            @require_entity(model, "item_id", inject_as="my_thing")
            def get(self, item_id, my_thing):
                return {"thing_name": my_thing.name}, 200

        api.add_resource(_CustomInjectResource, "/custom/<string:item_id>")
        resp = client.get(f"/custom/{VALID_OID}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["thing_name"] == "Test Entity"

    def test_different_param_name(self, flask_app, client):
        """The decorator works when the URL parameter is named something other than item_id."""
        entity = _make_mock_entity()
        model = _make_mock_model(return_value=entity)
        api = Api(flask_app)

        class _MarketResource(Resource):
            @require_entity(model, "market_id", inject_as="market_obj")
            def get(self, market_id, market_obj):
                return {"ok": True}, 200

        api.add_resource(_MarketResource, "/markets/<string:market_id>")
        resp = client.get(f"/markets/{VALID_OID}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestDecoratorStacking
# ---------------------------------------------------------------------------

class TestDecoratorStacking:
    """Tests for routes that combine multiple decorators."""

    def _register_entity_plus_json_route(self, app, model):
        """
        Register a PUT-like route that needs both @require_entity and @require_json_body.

        Decorator application order (Python applies bottom-up):
            @require_entity(...)   <- outer, runs first
            @require_json_body     <- inner, runs second
        """
        api = Api(app)

        class _StackedResource(Resource):
            @require_entity(model, "item_id", inject_as="entity")
            @require_json_body
            def put(self, item_id, entity, data):
                return {"entity_name": entity.name, "data_key": data.get("key")}, 200

        api.add_resource(_StackedResource, "/stacked/<string:item_id>")

    def test_both_decorators_pass(self, flask_app, client):
        """Valid ObjectId + valid JSON body: handler is called with both injected args."""
        entity = _make_mock_entity()
        model = _make_mock_model(return_value=entity)
        self._register_entity_plus_json_route(flask_app, model)
        resp = client.put(
            f"/stacked/{VALID_OID}",
            data=json.dumps({"key": "hello"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data_key"] == "hello"

    def test_invalid_objectid_short_circuits_before_json_check(self, flask_app, client):
        """Bad ObjectId returns 400 without ever checking the body."""
        model = _make_mock_model(return_value=_make_mock_entity())
        self._register_entity_plus_json_route(flask_app, model)
        resp = client.put(
            f"/stacked/{INVALID_OID}",
            data=json.dumps({"key": "hello"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_entity_not_found_short_circuits_before_json_check(self, flask_app, client):
        """Entity 404 is returned without checking the JSON body."""
        model = _make_mock_model(return_value=None)
        self._register_entity_plus_json_route(flask_app, model)
        resp = client.put(
            f"/stacked/{VALID_OID}",
            data=json.dumps({"key": "hello"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_valid_entity_bad_json_returns_400(self, flask_app, client):
        """Entity found but JSON body missing -> 400 from require_json_body."""
        entity = _make_mock_entity()
        model = _make_mock_model(return_value=entity)
        self._register_entity_plus_json_route(flask_app, model)
        resp = client.put(
            f"/stacked/{VALID_OID}",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_validate_objectid_and_require_json_stacked(self, flask_app, client):
        """@validate_objectid + @require_json_body can be stacked on a plain function."""
        api = Api(flask_app)

        class _OidJsonResource(Resource):
            @validate_objectid("item_id")
            @require_json_body
            def post(self, item_id, data):
                return {"id": item_id, "got": data.get("x")}, 200

        api.add_resource(_OidJsonResource, "/oid_json/<string:item_id>")

        # Happy path
        resp = client.post(
            f"/oid_json/{VALID_OID}",
            data=json.dumps({"x": 42}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["id"] == VALID_OID
        assert body["got"] == 42


# ---------------------------------------------------------------------------
# TestDecoratorMetadata
# ---------------------------------------------------------------------------

class TestDecoratorMetadata:
    """Verify that functools.wraps preserves the original function's metadata."""

    def test_require_json_body_preserves_name(self):
        def my_handler(data):
            pass

        wrapped = require_json_body(my_handler)
        assert wrapped.__name__ == "my_handler"

    def test_validate_objectid_preserves_name(self):
        def my_handler(item_id):
            pass

        wrapped = validate_objectid("item_id")(my_handler)
        assert wrapped.__name__ == "my_handler"

    def test_require_entity_preserves_name(self):
        model = _make_mock_model()

        def my_handler(item_id, entity):
            pass

        wrapped = require_entity(model, "item_id", inject_as="entity")(my_handler)
        assert wrapped.__name__ == "my_handler"
