"""
Tests for GridOS security module.
"""

from __future__ import annotations

from gridos.security.auth import (
    _VALID_API_KEYS,
    generate_api_key,
    register_api_key,
)


class TestAPIKeyAuth:
    """Tests for API key authentication."""

    def test_generate_api_key(self):
        key = generate_api_key()
        assert key.startswith("gos_")
        assert len(key) > 20

    def test_generate_api_key_custom_prefix(self):
        key = generate_api_key(prefix="test")
        assert key.startswith("test_")

    def test_register_api_key(self):
        key = generate_api_key()
        key_hash = register_api_key(key, "Test User", roles=["admin"])
        assert key_hash in _VALID_API_KEYS
        assert _VALID_API_KEYS[key_hash]["name"] == "Test User"
        assert "admin" in _VALID_API_KEYS[key_hash]["roles"]

    def test_unique_keys(self):
        key1 = generate_api_key()
        key2 = generate_api_key()
        assert key1 != key2
