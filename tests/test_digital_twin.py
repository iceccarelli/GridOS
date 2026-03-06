"""
Tests for the GridOS digital twin engine and physics models.
"""

from __future__ import annotations

import pytest

from gridos.digital_twin.engine import DigitalTwinEngine
from gridos.digital_twin.models.battery import Battery
from gridos.digital_twin.models.bus import Bus
from gridos.digital_twin.models.ev_charger import ChargerState, EVCharger
from gridos.digital_twin.models.line import Line
from gridos.digital_twin.models.pv import PV
from gridos.digital_twin.models.transformer import Transformer


class TestBus:
    """Tests for the Bus model."""

    def test_create_bus(self):
        bus = Bus(bus_id="b1", name="Test Bus", base_kv=0.4)
        assert bus.voltage_pu == 1.0
        assert bus.p_inject_kw == 0.0

    def test_add_injection(self):
        bus = Bus(bus_id="b1")
        bus.add_injection(10.0, 5.0)
        bus.add_injection(-3.0, -1.0)
        assert bus.p_inject_kw == 7.0
        assert bus.q_inject_kvar == 4.0

    def test_reset_injections(self):
        bus = Bus(bus_id="b1")
        bus.add_injection(10.0)
        bus.reset_injections()
        assert bus.p_inject_kw == 0.0


class TestLine:
    """Tests for the Line model."""

    def test_impedance(self):
        line = Line(
            line_id="l1",
            from_bus="b1",
            to_bus="b2",
            r_ohm_per_km=0.2,
            x_ohm_per_km=0.1,
            length_km=2.0,
        )
        assert line.r_total == pytest.approx(0.4)
        assert line.x_total == pytest.approx(0.2)


class TestTransformer:
    """Tests for the Transformer model."""

    def test_create_transformer(self):
        tx = Transformer(
            transformer_id="tx1",
            from_bus="b0",
            to_bus="b1",
            rated_kva=500,
            hv_kv=11.0,
            lv_kv=0.4,
        )
        assert tx.z_base_ohm > 0
        assert tx.r_ohm > 0


class TestPV:
    """Tests for the PV model."""

    def test_pv_output(self):
        pv = PV(pv_id="pv1", bus_id="b1", rated_kw=10.0, area_m2=55.0, efficiency=0.18)
        pv.update(900, {"irradiance_w_m2": 800, "temperature_c": 25})
        assert pv.p_output_kw > 0
        assert pv.p_output_kw <= pv.rated_kw

    def test_pv_zero_irradiance(self):
        pv = PV(pv_id="pv1", bus_id="b1")
        pv.update(900, {"irradiance_w_m2": 0})
        assert pv.p_output_kw == 0.0

    def test_pv_curtailment(self):
        pv = PV(pv_id="pv1", bus_id="b1", rated_kw=10.0, area_m2=55.0, efficiency=0.18)
        pv.update(900, {"irradiance_w_m2": 1000, "temperature_c": 25})
        original = pv.p_output_kw
        pv.curtail(5.0)
        pv.update(900, {"irradiance_w_m2": 1000, "temperature_c": 25})
        assert pv.p_output_kw < original


class TestBattery:
    """Tests for the Battery model."""

    def test_discharge(self):
        batt = Battery(battery_id="b1", bus_id="b1", capacity_kwh=100, soc=0.5)
        batt.set_power(25.0)  # discharge
        batt.update(3600)  # 1 hour
        assert batt.soc < 0.5
        assert batt.p_output_kw == pytest.approx(25.0)

    def test_charge(self):
        batt = Battery(battery_id="b1", bus_id="b1", capacity_kwh=100, soc=0.5)
        batt.set_power(-25.0)  # charge
        batt.update(3600)
        assert batt.soc > 0.5

    def test_soc_limits(self):
        batt = Battery(
            battery_id="b1",
            bus_id="b1",
            capacity_kwh=100,
            soc=0.11,
            soc_min=0.1,
        )
        batt.set_power(50.0)  # try to discharge
        batt.update(3600)
        assert batt.soc >= batt.soc_min


class TestEVCharger:
    """Tests for the EVCharger model."""

    def test_charging_session(self):
        ev = EVCharger(charger_id="ev1", bus_id="b1", max_power_kw=22.0)
        ev.plug_in(ev_battery_kwh=60, ev_soc=0.3, target_soc=0.9)
        assert ev.state == ChargerState.CHARGING

        ev.update(3600)  # 1 hour
        assert ev.ev_soc > 0.3
        assert ev.p_output_kw > 0

    def test_idle_state(self):
        ev = EVCharger(charger_id="ev1", bus_id="b1")
        ev.update(3600)
        assert ev.p_output_kw == 0.0


class TestGridModel:
    """Tests for the GridModel."""

    def test_power_flow(self, sample_grid_model):
        # Set PV output
        pv = sample_grid_model.pvs["pv_1"]
        pv.update(900, {"irradiance_w_m2": 800, "temperature_c": 25})

        result = sample_grid_model.simulate()
        assert result["converged"] is True
        assert "bus_voltages" in result

    def test_aggregate_injections(self, sample_grid_model):
        pv = sample_grid_model.pvs["pv_1"]
        pv.update(900, {"irradiance_w_m2": 800, "temperature_c": 25})
        sample_grid_model._aggregate_injections()

        bus1 = sample_grid_model.buses["bus_1"]
        # Bus should have net injection (PV - load)
        assert bus1.p_inject_kw != 0.0


class TestDigitalTwinEngine:
    """Tests for the DigitalTwinEngine."""

    def test_single_step(self, sample_grid_model):
        engine = DigitalTwinEngine(sample_grid_model, dt_seconds=900)
        snapshot = engine.step({"irradiance_w_m2": 600, "temperature_c": 30})
        assert "step" in snapshot
        assert snapshot["step"] == 0
        assert engine.step_count == 1

    def test_multi_step(self, sample_grid_model):
        engine = DigitalTwinEngine(sample_grid_model, dt_seconds=900)
        conditions = [
            {"irradiance_w_m2": i * 100, "temperature_c": 25} for i in range(4)
        ]
        results = engine.run(4, conditions)
        assert len(results) == 4
        assert engine.step_count == 4

    def test_reset(self, sample_grid_model):
        engine = DigitalTwinEngine(sample_grid_model)
        engine.step()
        engine.reset()
        assert engine.step_count == 0
        assert len(engine.history) == 0
