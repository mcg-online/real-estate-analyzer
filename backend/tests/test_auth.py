"""
Tests for utils/auth.py — JWT token blocklist.

Redis is never contacted during these tests; all Redis interactions are mocked
so the suite runs cleanly in environments without a running Redis server.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_auth():
    """Reload utils.auth so module-level state is reset between tests."""
    for mod in list(sys.modules.keys()):
        if mod in ("utils.auth", "utils"):
            del sys.modules[mod]
    import utils.auth as auth_module
    return auth_module


# ---------------------------------------------------------------------------
# In-memory fallback tests (no REDIS_URL set)
# ---------------------------------------------------------------------------

class TestInMemoryFallback:
    """When REDIS_URL is absent the module must use the in-process set."""

    def test_is_token_revoked_returns_false_for_unknown(self):
        """An unknown JTI must not be considered revoked."""
        with patch.dict("os.environ", {}, clear=False):
            # Ensure REDIS_URL is absent
            import os
            os.environ.pop("REDIS_URL", None)

            auth = _reload_auth()
            assert auth.is_token_revoked("unknown-jti-abc123") is False

    def test_add_token_blocklist_marks_as_revoked(self):
        """A JTI added to the blocklist must subsequently be reported as revoked."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        auth.add_token_to_blocklist("test-jti-001")
        assert auth.is_token_revoked("test-jti-001") is True

    def test_add_and_check_token_blocklist_inmemory(self):
        """Multiple tokens can be blocklisted independently."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        auth.add_token_to_blocklist("jti-alpha")
        auth.add_token_to_blocklist("jti-beta")

        assert auth.is_token_revoked("jti-alpha") is True
        assert auth.is_token_revoked("jti-beta") is True
        assert auth.is_token_revoked("jti-gamma") is False

    def test_non_blocklisted_token_not_revoked(self):
        """A token that was never added must not appear revoked."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        auth.add_token_to_blocklist("jti-added")
        assert auth.is_token_revoked("jti-not-added") is False


# ---------------------------------------------------------------------------
# Redis-backed tests (Redis mocked)
# ---------------------------------------------------------------------------

class TestRedisBacked:
    """When REDIS_URL is set the module should delegate to Redis."""

    def _make_redis_mock(self, exists_return=0):
        """Return a mock that mimics redis.Redis ping/setex/exists."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.exists.return_value = exists_return
        return mock_redis

    def test_add_token_calls_setex(self):
        """add_token_to_blocklist must call Redis setex with the right key."""
        mock_redis_instance = self._make_redis_mock()

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis_instance):
                auth = _reload_auth()
                auth.add_token_to_blocklist("redis-jti-001")

        mock_redis_instance.setex.assert_called_once_with(
            "jwt_blocklist:redis-jti-001",
            3600,
            "1",
        )

    def test_is_token_revoked_true_when_redis_exists(self):
        """is_token_revoked must return True when Redis reports key exists."""
        mock_redis_instance = self._make_redis_mock(exists_return=1)

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis_instance):
                auth = _reload_auth()
                result = auth.is_token_revoked("redis-jti-002")

        assert result is True
        mock_redis_instance.exists.assert_called_once_with("jwt_blocklist:redis-jti-002")

    def test_is_token_revoked_false_when_redis_missing(self):
        """is_token_revoked must return False when Redis reports key absent."""
        mock_redis_instance = self._make_redis_mock(exists_return=0)

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis_instance):
                auth = _reload_auth()
                result = auth.is_token_revoked("redis-jti-003")

        assert result is False

    def test_fallback_to_inmemory_when_redis_ping_fails(self):
        """If Redis.ping() raises, the module must silently use in-memory."""
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = Exception("Connection refused")

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis_instance):
                auth = _reload_auth()
                # Should not raise; should fall back to in-memory
                auth.add_token_to_blocklist("fallback-jti")
                assert auth.is_token_revoked("fallback-jti") is True
                # Redis setex must NOT have been called
                mock_redis_instance.setex.assert_not_called()


# ---------------------------------------------------------------------------
# Round-trip / multi-cycle tests (in-memory)
# ---------------------------------------------------------------------------

class TestBlocklistRoundTrip:
    """Integration-style tests covering add+check cycles without Redis."""

    def test_single_add_then_check(self):
        """Basic round-trip: add then verify revoked."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        jti = "round-trip-jti"
        assert auth.is_token_revoked(jti) is False
        auth.add_token_to_blocklist(jti)
        assert auth.is_token_revoked(jti) is True

    def test_only_added_tokens_are_revoked(self):
        """Tokens not explicitly added must not appear revoked."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        revoked = ["r-1", "r-2", "r-3"]
        alive = ["a-1", "a-2", "a-3"]

        for jti in revoked:
            auth.add_token_to_blocklist(jti)

        for jti in revoked:
            assert auth.is_token_revoked(jti) is True

        for jti in alive:
            assert auth.is_token_revoked(jti) is False

    def test_large_batch_of_tokens(self):
        """Blocklist must correctly handle many tokens in one session."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        count = 200
        jtis = [f"bulk-token-{i}" for i in range(count)]

        for jti in jtis:
            auth.add_token_to_blocklist(jti)

        for jti in jtis:
            assert auth.is_token_revoked(jti) is True

        # A token outside the added range must not be revoked
        assert auth.is_token_revoked(f"bulk-token-{count}") is False

    def test_similar_jtis_do_not_collide(self):
        """Blocklisting 'jti-1' must not affect 'jti-10' or 'jti-2'."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        auth.add_token_to_blocklist("jti-1")
        assert auth.is_token_revoked("jti-10") is False
        assert auth.is_token_revoked("jti-2") is False

    def test_multiple_sessions_simulated(self):
        """Simulate multiple independent token lifecycles in one process."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        session_tokens = {
            "session-A": "jti-session-a-xyz",
            "session-B": "jti-session-b-abc",
            "session-C": "jti-session-c-qrs",
        }

        # Initially none are revoked
        for jti in session_tokens.values():
            assert auth.is_token_revoked(jti) is False

        # Revoke sessions A and C
        auth.add_token_to_blocklist(session_tokens["session-A"])
        auth.add_token_to_blocklist(session_tokens["session-C"])

        assert auth.is_token_revoked(session_tokens["session-A"]) is True
        assert auth.is_token_revoked(session_tokens["session-B"]) is False
        assert auth.is_token_revoked(session_tokens["session-C"]) is True

    def test_special_characters_in_jti(self):
        """JTIs containing special characters should be stored faithfully."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        special_jti = "jti/with+special=chars&more?query#fragment"
        auth.add_token_to_blocklist(special_jti)
        assert auth.is_token_revoked(special_jti) is True
        # A prefix of the special JTI must not match
        assert auth.is_token_revoked("jti/with+special") is False

    def test_duplicate_add_is_idempotent(self):
        """Adding the same JTI twice must not raise and must remain revoked."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        auth.add_token_to_blocklist("jti-dup")
        auth.add_token_to_blocklist("jti-dup")
        assert auth.is_token_revoked("jti-dup") is True

    def test_returns_bool_type(self):
        """is_token_revoked must always return a bool."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        result = auth.is_token_revoked("any-jti")
        assert isinstance(result, bool)

    def test_add_returns_none(self):
        """add_token_to_blocklist has no meaningful return value."""
        import os
        os.environ.pop("REDIS_URL", None)

        auth = _reload_auth()
        result = auth.add_token_to_blocklist("jti-ret")
        assert result is None


# ---------------------------------------------------------------------------
# Redis TTL and key-prefix tests
# ---------------------------------------------------------------------------

class TestRedisKeyFormat:
    """Verify the Redis key prefix and TTL used by the auth module."""

    def _make_redis_mock(self, exists_return=0):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.exists.return_value = exists_return
        return mock_redis

    def test_redis_key_uses_jwt_blocklist_prefix(self):
        """Keys stored in Redis must start with 'jwt_blocklist:'."""
        mock_redis = self._make_redis_mock()

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis):
                auth = _reload_auth()
                auth.add_token_to_blocklist("prefix-check-jti")

        args, _ = mock_redis.setex.call_args
        assert args[0] == "jwt_blocklist:prefix-check-jti"

    def test_redis_ttl_is_3600_seconds(self):
        """The TTL passed to setex must be 3600 (one hour)."""
        mock_redis = self._make_redis_mock()

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis):
                auth = _reload_auth()
                auth.add_token_to_blocklist("ttl-check-jti")

        args, _ = mock_redis.setex.call_args
        assert args[1] == 3600

    def test_redis_stored_value_is_string_one(self):
        """The value stored in Redis must be the string '1'."""
        mock_redis = self._make_redis_mock()

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis):
                auth = _reload_auth()
                auth.add_token_to_blocklist("value-check-jti")

        args, _ = mock_redis.setex.call_args
        assert args[2] == "1"

    def test_exists_check_uses_correct_key_prefix(self):
        """is_token_revoked must query Redis using the 'jwt_blocklist:' prefix."""
        mock_redis = self._make_redis_mock(exists_return=1)

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis):
                auth = _reload_auth()
                auth.is_token_revoked("exists-check-jti")

        mock_redis.exists.assert_called_once_with("jwt_blocklist:exists-check-jti")

    def test_redis_from_url_called_with_decode_responses(self):
        """redis.from_url must be called with decode_responses=True."""
        mock_redis = self._make_redis_mock()

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("redis.from_url", return_value=mock_redis) as mock_from_url:
                auth = _reload_auth()
                auth.add_token_to_blocklist("decode-check-jti")

        _, kwargs = mock_from_url.call_args
        assert kwargs.get("decode_responses") is True
