"""Tests for argument validation helpers."""

import pytest

from src.service.arg_checkers import not_falsy


class TestNotFalsy:
    """Tests for the not_falsy function."""

    def test_not_falsy_with_string(self):
        """Test that non-empty strings are returned."""
        result = not_falsy("hello", "test_value")
        assert result == "hello"

    def test_not_falsy_with_number(self):
        """Test that non-zero numbers are returned."""
        result = not_falsy(42, "test_value")
        assert result == 42

    def test_not_falsy_with_list(self):
        """Test that non-empty lists are returned."""
        result = not_falsy([1, 2, 3], "test_value")
        assert result == [1, 2, 3]

    def test_not_falsy_with_dict(self):
        """Test that non-empty dicts are returned."""
        result = not_falsy({"key": "value"}, "test_value")
        assert result == {"key": "value"}

    def test_not_falsy_raises_on_none(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="MY_VAR is required and cannot be empty"):
            not_falsy(None, "MY_VAR")

    def test_not_falsy_raises_on_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(
            ValueError, match="EMPTY_STR is required and cannot be empty"
        ):
            not_falsy("", "EMPTY_STR")

    def test_not_falsy_raises_on_zero(self):
        """Test that 0 raises ValueError (falsy value)."""
        with pytest.raises(
            ValueError, match="ZERO_VAL is required and cannot be empty"
        ):
            not_falsy(0, "ZERO_VAL")

    def test_not_falsy_raises_on_empty_list(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(
            ValueError, match="EMPTY_LIST is required and cannot be empty"
        ):
            not_falsy([], "EMPTY_LIST")

    def test_not_falsy_raises_on_false(self):
        """Test that False raises ValueError."""
        with pytest.raises(
            ValueError, match="BOOL_VAL is required and cannot be empty"
        ):
            not_falsy(False, "BOOL_VAL")
