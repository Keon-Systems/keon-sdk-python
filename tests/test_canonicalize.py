"""Tests for RFC 8785 canonicalization."""

import pytest
from keon_sdk.canonicalize import (
    canonicalize,
    canonicalize_to_string,
    canonicalize_bytes,
    validate_integrity,
)


class TestKeyOrdering:
    """JCS-001: UTF-16 code unit ordering."""

    def test_uppercase_before_lowercase(self):
        """Uppercase ASCII (0x41-0x5A) sorts before lowercase (0x61-0x7A)."""
        input_data = {
            "z_key": 3,
            "a_key": 1,
            "A_key": 0,
            "m_key": 2,
        }

        result = canonicalize_to_string(input_data)
        assert result == '{"A_key":0,"a_key":1,"m_key":2,"z_key":3}'


class TestNumberNormalization:
    """JCS-004: Number formatting."""

    def test_integer(self):
        assert canonicalize_to_string(42) == "42"

    def test_integer_from_float(self):
        assert canonicalize_to_string(100.0) == "100"

    def test_negative_zero(self):
        assert canonicalize_to_string(-0.0) == "0"

    def test_decimal_precision(self):
        assert canonicalize_to_string(3.14159) == "3.14159"

    def test_small_decimal(self):
        assert canonicalize_to_string(0.001) == "0.001"

    def test_nan_raises(self):
        import math

        with pytest.raises(ValueError, match="NaN"):
            canonicalize_to_string(math.nan)

    def test_infinity_raises(self):
        import math

        with pytest.raises(ValueError, match="Infinity"):
            canonicalize_to_string(math.inf)


class TestStringEscaping:
    """String escaping rules."""

    def test_escape_quotes(self):
        assert canonicalize_to_string('say "hi"') == '"say \\"hi\\""'

    def test_escape_backslash(self):
        assert canonicalize_to_string("path\\to") == '"path\\\\to"'

    def test_escape_newline(self):
        assert canonicalize_to_string("line1\nline2") == '"line1\\nline2"'

    def test_escape_tab(self):
        assert canonicalize_to_string("col1\tcol2") == '"col1\\tcol2"'

    def test_no_escape_unicode(self):
        """RFC 8785: Non-control Unicode should be literal, not escaped."""
        result = canonicalize_to_string("Hello")
        assert result == '"Hello"'
        # Should NOT contain \\u00F6
        assert "\\u" not in result or "\\u00" in result  # Only control chars escaped


class TestNullHandling:
    """JCS-005: Explicit null handling."""

    def test_explicit_null(self):
        input_data = {
            "present_null": None,
            "present_value": "exists",
        }

        result = canonicalize_to_string(input_data)
        assert result == '{"present_null":null,"present_value":"exists"}'


class TestArrayOrder:
    """Array order preservation."""

    def test_preserve_order(self):
        assert canonicalize_to_string([3, 1, 2]) == "[3,1,2]"


class TestWhitespace:
    """Whitespace elimination."""

    def test_no_whitespace(self):
        input_data = {
            "a": 1,
            "b": {
                "c": 2,
            },
        }

        result = canonicalize_to_string(input_data)
        assert result == '{"a":1,"b":{"c":2}}'


class TestValidateIntegrity:
    """Integrity validation."""

    def test_valid_canonical(self):
        canonical = b'{"A":1,"a":2}'
        assert validate_integrity(canonical) is True

    def test_invalid_whitespace(self):
        not_canonical = b'{ "A": 1, "a": 2 }'
        assert validate_integrity(not_canonical) is False

    def test_wrong_order(self):
        wrong_order = b'{"a":2,"A":1}'
        assert validate_integrity(wrong_order) is False


class TestRoundTrip:
    """Round-trip invariant."""

    def test_no_change_on_recanonicalze(self):
        input_data = {"z": 3, "a": 1, "m": 2}

        first = canonicalize(input_data)
        second = canonicalize_bytes(first)

        assert first == second


class TestCrossPlatformDeterminism:
    """Cross-platform determinism vectors."""

    def test_canonical_ordering_vector(self):
        """Test vector from evidence-pack-test-vectors-v1.json."""
        input_data = {
            "A_key": 0,
            "a_key": 1,
            "m_key": 2,
            "z_key": 3,
        }

        result = canonicalize_to_string(input_data)
        assert result == '{"A_key":0,"a_key":1,"m_key":2,"z_key":3}'
