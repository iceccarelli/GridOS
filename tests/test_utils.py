"""
Tests for GridOS utility functions.
"""

from __future__ import annotations

import math

import pytest

from gridos.utils.helpers import (
    chunk_list,
    clamp,
    generate_id,
    hash_dict,
    kw_to_mw,
    moving_average,
    mw_to_kw,
    power_factor_to_reactive,
    safe_divide,
)


class TestHelpers:
    """Tests for utility helper functions."""

    def test_kw_to_mw(self):
        assert kw_to_mw(1000) == 1.0

    def test_mw_to_kw(self):
        assert mw_to_kw(1.5) == 1500.0

    def test_clamp(self):
        assert clamp(5, 0, 10) == 5
        assert clamp(-1, 0, 10) == 0
        assert clamp(15, 0, 10) == 10

    def test_power_factor_to_reactive(self):
        q = power_factor_to_reactive(100, 0.9)
        assert q > 0
        # PF=1 should give 0 reactive
        assert power_factor_to_reactive(100, 1.0) == pytest.approx(0.0, abs=1e-10)

    def test_generate_id(self):
        id1 = generate_id("dev")
        assert id1.startswith("dev-")
        id2 = generate_id()
        assert "-" not in id2

    def test_chunk_list(self):
        items = list(range(10))
        chunks = chunk_list(items, 3)
        assert len(chunks) == 4
        assert chunks[0] == [0, 1, 2]
        assert chunks[-1] == [9]

    def test_hash_dict(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert hash_dict(d1) == hash_dict(d2)

    def test_safe_divide(self):
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=-1) == -1

    def test_moving_average(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        ma = moving_average(values, 3)
        assert math.isnan(ma[0])
        assert math.isnan(ma[1])
        assert ma[2] == pytest.approx(2.0)
        assert ma[4] == pytest.approx(4.0)
