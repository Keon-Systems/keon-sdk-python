"""
RFC 8785 JSON Canonicalization Scheme (JCS) for Keon

This is the Python implementation of the Keon canonicalization standard,
matching the behavior of the C# KeonCanonicalJsonV1.cs implementation.

Guarantees:
- Byte-identical output for identical inputs across platforms
- Unicode NFC normalization applied before canonicalization
- Properties sorted by UTF-16 code unit (lexicographic/ordinal)
- Deterministic number formatting
- No unnecessary escape sequences

Version: 1.0.0
Spec: CANONICALIZATION_SPEC_V1_LOCKED.md + RFC 8785
"""

import json
import math
import unicodedata
from typing import Any, List, Union


def canonicalize(value: Any) -> bytes:
    """
    Canonicalizes a value to canonical JSON bytes.

    Args:
        value: Any JSON-serializable value

    Returns:
        Canonical JSON as UTF-8 bytes
    """
    return canonicalize_to_string(value).encode("utf-8")


def canonicalize_to_string(value: Any) -> str:
    """
    Canonicalizes a value to a canonical JSON string.

    Args:
        value: Any JSON-serializable value

    Returns:
        Canonical JSON string
    """
    return _canonicalize_value(value)


def canonicalize_bytes(json_bytes: bytes) -> bytes:
    """
    Canonicalizes JSON bytes to canonical form.

    Args:
        json_bytes: JSON as UTF-8 bytes

    Returns:
        Canonical JSON as UTF-8 bytes
    """
    parsed = json.loads(json_bytes.decode("utf-8"))
    return canonicalize(parsed)


def validate_integrity(json_bytes: bytes) -> bool:
    """
    Validates that bytes are already in canonical form.

    Args:
        json_bytes: JSON bytes to validate

    Returns:
        True if bytes are canonical, False otherwise
    """
    try:
        canonical = canonicalize_bytes(json_bytes)
        return json_bytes == canonical
    except Exception:
        return False


def _canonicalize_value(value: Any) -> str:
    """Recursively canonicalizes a JSON value."""
    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return _canonicalize_number(value)

    if isinstance(value, str):
        return _canonicalize_string(value)

    if isinstance(value, list):
        return _canonicalize_array(value)

    if isinstance(value, dict):
        return _canonicalize_object(value)

    raise TypeError(f"Unsupported type: {type(value)}")


def _canonicalize_string(s: str) -> str:
    """Canonicalizes a string with NFC normalization and proper escaping."""
    # Apply Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", s)

    result = ['"']
    for char in normalized:
        code = ord(char)

        if char == '"':
            result.append('\\"')
        elif char == "\\":
            result.append("\\\\")
        elif char == "\b":
            result.append("\\b")
        elif char == "\f":
            result.append("\\f")
        elif char == "\n":
            result.append("\\n")
        elif char == "\r":
            result.append("\\r")
        elif char == "\t":
            result.append("\\t")
        elif code < 0x20:
            # Control characters: use \uXXXX
            result.append(f"\\u{code:04x}")
        else:
            # RFC 8785: Non-control Unicode characters (U+0020 to U+10FFFF)
            # MUST be written as literal UTF-8, NOT escaped
            result.append(char)

    result.append('"')
    return "".join(result)


def _canonicalize_number(num: Union[int, float]) -> str:
    """Canonicalizes a number per RFC 8785."""
    # Handle special cases
    if isinstance(num, float):
        if math.isnan(num) or math.isinf(num):
            raise ValueError("NaN and Infinity are not valid JSON numbers")

        # Normalize -0.0 to 0
        if num == 0.0:
            return "0"

        # Check if it's effectively an integer
        if num == int(num) and abs(num) <= 2**53:
            return str(int(num))

        # Format with minimal representation
        # Python's repr for floats is already minimal
        s = repr(num)
        # Remove unnecessary .0 suffix if present
        if s.endswith(".0"):
            s = s[:-2]
        return s

    # Integer
    return str(num)


def _canonicalize_array(arr: List[Any]) -> str:
    """Canonicalizes an array (preserves order)."""
    elements = [_canonicalize_value(elem) for elem in arr]
    return "[" + ",".join(elements) + "]"


def _canonicalize_object(obj: dict) -> str:
    """Canonicalizes an object (sorts keys by UTF-16 code unit order)."""
    # Get keys and apply NFC normalization
    keys = [unicodedata.normalize("NFC", k) for k in obj.keys()]

    # Sort by UTF-16 code unit order
    keys.sort(key=lambda k: _utf16_sort_key(k))

    pairs = []
    for key in keys:
        # Find original key (pre-normalization) to get value
        original_key = next(
            (k for k in obj.keys() if unicodedata.normalize("NFC", k) == key), key
        )
        value = obj[original_key]
        pairs.append(_canonicalize_string(key) + ":" + _canonicalize_value(value))

    return "{" + ",".join(pairs) + "}"


def _utf16_sort_key(s: str) -> List[int]:
    """
    Returns a sort key based on UTF-16 code units.

    This matches StringComparer.Ordinal in .NET and is required by RFC 8785.
    """
    result = []
    for char in s:
        code = ord(char)
        if code < 0x10000:
            # BMP character - single code unit
            result.append(code)
        else:
            # Supplementary character - surrogate pair
            code -= 0x10000
            high = 0xD800 + (code >> 10)
            low = 0xDC00 + (code & 0x3FF)
            result.append(high)
            result.append(low)
    return result
