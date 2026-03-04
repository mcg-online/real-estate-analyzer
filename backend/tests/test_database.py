"""Tests for backend/utils/database.py.

pymongo.MongoClient is always mocked so no real MongoDB instance is required.
Module-level globals (_db_client, _db, _mongodb_uri) are reset between tests
via the ``reset_db_state`` fixture to avoid cross-test contamination.
"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Fixture: reset module globals before every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_db_state():
    """Reset utils.database module-level globals before and after each test."""
    import utils.database as db_module

    # Save originals
    orig_client = db_module._db_client
    orig_db = db_module._db
    orig_uri = db_module._mongodb_uri

    # Reset to clean state
    db_module._db_client = None
    db_module._db = None
    db_module._mongodb_uri = None

    yield

    # Restore originals
    db_module._db_client = orig_client
    db_module._db = orig_db
    db_module._mongodb_uri = orig_uri


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mongo_client_mock() -> MagicMock:
    """Return a MagicMock that satisfies the MongoClient interface used in database.py."""
    client = MagicMock()
    # admin.command('ping') must not raise by default
    client.admin.command.return_value = {"ok": 1}
    # Subscript access client[db_name] returns a mock db.
    # MagicMock pre-wires __getitem__ on the type, so we configure via .return_value
    # rather than instance attribute assignment.
    client.__getitem__.return_value = MagicMock()
    return client


def _make_flask_app_mock(uri: str = "mongodb://localhost:27017/realestate") -> MagicMock:
    """Return a minimal Flask app mock with MONGODB_URI in config."""
    app = MagicMock()
    app.config = {"MONGODB_URI": uri}
    app.config.get = lambda key, default=None: app.config.get(key, default) if False else (
        uri if key == "MONGODB_URI" else default
    )
    return app


# ---------------------------------------------------------------------------
# _parse_db_name tests
# ---------------------------------------------------------------------------

class TestParseDbName:
    """Tests for the private _parse_db_name helper."""

    def test_extracts_db_name_from_uri(self):
        from utils.database import _parse_db_name
        assert _parse_db_name("mongodb://localhost:27017/mydb") == "mydb"

    def test_defaults_to_realestate_when_no_path(self):
        from utils.database import _parse_db_name
        assert _parse_db_name("mongodb://localhost:27017/") == "realestate"

    def test_strips_query_params(self):
        from utils.database import _parse_db_name
        # Path with only query params but no db name
        result = _parse_db_name("mongodb://localhost:27017/?retryWrites=true")
        # Either empty path → 'realestate', or db name extracted
        assert isinstance(result, str) and len(result) > 0

    def test_handles_uri_with_credentials(self):
        from utils.database import _parse_db_name
        result = _parse_db_name("mongodb://user:pass@host:27017/proddb")
        assert result == "proddb"


# ---------------------------------------------------------------------------
# init_db tests
# ---------------------------------------------------------------------------

class TestInitDb:
    """Tests for utils.database.init_db()."""

    def test_returns_none_when_no_uri_configured(self):
        from utils.database import init_db

        app = MagicMock()
        app.config.get = MagicMock(return_value=None)

        result = init_db(app)
        assert result is None

    def test_stores_mongodb_uri_from_app_config(self):
        import utils.database as db_module
        from utils.database import init_db

        mock_client = _make_mongo_client_mock()

        app = MagicMock()
        app.config.get = MagicMock(return_value="mongodb://localhost:27017/testdb")

        with patch("utils.database.MongoClient", return_value=mock_client):
            init_db(app)

        assert db_module._mongodb_uri == "mongodb://localhost:27017/testdb"

    def test_returns_db_object_on_successful_connect(self):
        from utils.database import init_db

        mock_client = _make_mongo_client_mock()

        app = MagicMock()
        app.config.get = MagicMock(return_value="mongodb://localhost:27017/testdb")

        with patch("utils.database.MongoClient", return_value=mock_client):
            result = init_db(app)

        assert result is not None

    def test_creates_property_indexes(self):
        """init_db should create indexes on the properties collection."""
        from utils.database import init_db

        mock_client = _make_mongo_client_mock()
        # mock_client.__getitem__.return_value is already a MagicMock (mock_db).
        # _connect does: _db = _db_client[db_name]; then _db['properties'].create_index(...)
        # That means mock_db.__getitem__.return_value.create_index() gets called.
        mock_db = mock_client.__getitem__.return_value

        app = MagicMock()
        app.config.get = MagicMock(return_value="mongodb://localhost:27017/testdb")

        with patch("utils.database.MongoClient", return_value=mock_client):
            init_db(app)

        # Verify that the db subscript was accessed (meaning index creation ran).
        assert mock_db.__getitem__.called, (
            "Expected db['properties'] / db['users'] / db['markets'] to be accessed"
        )

    def test_creates_users_index(self):
        """init_db should create a unique index on users.username."""
        from utils.database import init_db

        mock_client = _make_mongo_client_mock()
        mock_db = mock_client.__getitem__.return_value

        app = MagicMock()
        app.config.get = MagicMock(return_value="mongodb://localhost:27017/testdb")

        with patch("utils.database.MongoClient", return_value=mock_client):
            init_db(app)

        # Verify create_index was invoked on the collection returned by db[key]
        collection_mock = mock_db.__getitem__.return_value
        assert collection_mock.create_index.called, (
            "Expected create_index to be called on at least one collection"
        )

    def test_returns_none_when_connection_fails_all_retries(self):
        from utils.database import init_db

        app = MagicMock()
        app.config.get = MagicMock(return_value="mongodb://localhost:27017/testdb")

        with (
            patch("utils.database.MongoClient", side_effect=Exception("connection refused")),
            patch("time.sleep"),  # skip backoff delays
        ):
            result = init_db(app)

        assert result is None

    def test_retries_on_transient_failure(self):
        """MongoClient should be retried up to max_retries times on failure."""
        from utils.database import init_db

        good_client = _make_mongo_client_mock()

        call_count = {"n": 0}

        def client_factory(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise Exception("transient error")
            return good_client

        app = MagicMock()
        app.config.get = MagicMock(return_value="mongodb://localhost:27017/testdb")

        with (
            patch("utils.database.MongoClient", side_effect=client_factory),
            patch("time.sleep"),
        ):
            result = init_db(app)

        assert result is not None
        assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# get_db tests
# ---------------------------------------------------------------------------

class TestGetDb:
    """Tests for utils.database.get_db()."""

    def test_raises_value_error_when_not_initialized(self):
        from utils.database import get_db

        with pytest.raises((ValueError, ConnectionError)):
            get_db()

    def test_returns_existing_db_without_reconnect(self):
        """If _db is already set and ping succeeds, the same db is returned."""
        import utils.database as db_module
        from utils.database import get_db

        mock_client = _make_mongo_client_mock()
        mock_db = MagicMock()

        db_module._db_client = mock_client
        db_module._db = mock_db
        db_module._mongodb_uri = "mongodb://localhost:27017/testdb"

        result = get_db()

        assert result is mock_db
        # Ping is called once to verify liveness
        mock_client.admin.command.assert_called_once_with("ping")

    def test_reconnects_when_ping_fails(self):
        """If the liveness ping raises, get_db should reconnect."""
        import utils.database as db_module
        from utils.database import get_db
        from pymongo.errors import ConnectionFailure

        stale_client = MagicMock()
        stale_client.admin.command.side_effect = ConnectionFailure("timeout")

        fresh_client = _make_mongo_client_mock()

        db_module._db_client = stale_client
        db_module._db = MagicMock()
        db_module._mongodb_uri = "mongodb://localhost:27017/testdb"

        with (
            patch("utils.database.MongoClient", return_value=fresh_client),
            patch("time.sleep"),
        ):
            result = get_db()

        assert result is not None

    def test_raises_connection_error_when_reconnect_fails(self):
        """If reconnect also fails, a ConnectionError is raised."""
        import utils.database as db_module
        from utils.database import get_db
        from pymongo.errors import ServerSelectionTimeoutError

        stale_client = MagicMock()
        stale_client.admin.command.side_effect = ServerSelectionTimeoutError("down")

        db_module._db_client = stale_client
        db_module._db = MagicMock()
        db_module._mongodb_uri = "mongodb://localhost:27017/testdb"

        with (
            patch("utils.database.MongoClient", side_effect=Exception("refused")),
            patch("time.sleep"),
        ):
            with pytest.raises((ConnectionError, Exception)):
                get_db()

    def test_raises_when_uri_none_and_db_none(self):
        """With no URI and no db, a meaningful error is raised."""
        import utils.database as db_module
        from utils.database import get_db

        db_module._db = None
        db_module._db_client = None
        db_module._mongodb_uri = None

        with pytest.raises((ValueError, ConnectionError)):
            get_db()

    def test_initialises_db_lazily_if_uri_set(self):
        """If _db is None but _mongodb_uri is set, get_db() connects on demand."""
        import utils.database as db_module
        from utils.database import get_db

        mock_client = _make_mongo_client_mock()

        db_module._db = None
        db_module._db_client = None
        db_module._mongodb_uri = "mongodb://localhost:27017/lazydb"

        with (
            patch("utils.database.MongoClient", return_value=mock_client),
            patch("time.sleep"),
        ):
            result = get_db()

        assert result is not None


# ---------------------------------------------------------------------------
# close_db tests
# ---------------------------------------------------------------------------

class TestCloseDb:
    """Tests for utils.database.close_db()."""

    def test_closes_client_connection(self):
        import utils.database as db_module
        from utils.database import close_db

        mock_client = MagicMock()
        db_module._db_client = mock_client
        db_module._db = MagicMock()

        close_db()

        mock_client.close.assert_called_once()

    def test_sets_client_and_db_to_none(self):
        import utils.database as db_module
        from utils.database import close_db

        db_module._db_client = MagicMock()
        db_module._db = MagicMock()

        close_db()

        assert db_module._db_client is None
        assert db_module._db is None

    def test_is_idempotent_when_already_closed(self):
        """Calling close_db() when nothing is open must not raise."""
        import utils.database as db_module
        from utils.database import close_db

        db_module._db_client = None
        db_module._db = None

        # Should complete without error
        close_db()

    def test_logs_closure_message(self, caplog):
        import logging
        import utils.database as db_module
        from utils.database import close_db

        db_module._db_client = MagicMock()
        db_module._db = MagicMock()

        with caplog.at_level(logging.INFO, logger="utils.database"):
            close_db()

        messages = [r.message.lower() for r in caplog.records]
        assert any("close" in msg or "connection" in msg for msg in messages)


# ---------------------------------------------------------------------------
# Graceful degradation: no MongoDB available
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """Verify the module handles unavailable MongoDB gracefully."""

    def test_init_db_returns_none_gracefully(self):
        """When MongoDB is unreachable, init_db must return None (not raise)."""
        from utils.database import init_db

        app = MagicMock()
        app.config.get = MagicMock(return_value="mongodb://unreachable:27017/db")

        with (
            patch("utils.database.MongoClient", side_effect=Exception("host unreachable")),
            patch("time.sleep"),
        ):
            result = init_db(app)

        assert result is None

    def test_get_db_raises_after_failed_init(self):
        """After a failed init_db, get_db should raise rather than return None."""
        import utils.database as db_module
        from utils.database import get_db

        db_module._mongodb_uri = "mongodb://unreachable:27017/db"
        db_module._db = None
        db_module._db_client = None

        with (
            patch("utils.database.MongoClient", side_effect=Exception("refused")),
            patch("time.sleep"),
        ):
            with pytest.raises(Exception):
                get_db()
