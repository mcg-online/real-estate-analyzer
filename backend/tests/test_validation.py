"""Tests for utils.validation module."""

from utils.validation import is_valid_objectid


class TestIsValidObjectId:
    """Tests for the ObjectId validator."""

    def test_valid_objectid_string(self):
        assert is_valid_objectid("64a1f2c3d4e5f6a7b8c9d0e1") is True

    def test_all_zeros_valid(self):
        assert is_valid_objectid("000000000000000000000000") is True

    def test_invalid_short_string(self):
        assert is_valid_objectid("abc123") is False

    def test_invalid_non_hex_chars(self):
        assert is_valid_objectid("zzzzzzzzzzzzzzzzzzzzzzzz") is False

    def test_none_generates_new_id(self):
        # ObjectId(None) generates a new valid ObjectId, so it passes validation
        assert is_valid_objectid(None) is True

    def test_empty_string_returns_false(self):
        assert is_valid_objectid("") is False

    def test_integer_returns_false(self):
        assert is_valid_objectid(12345) is False
