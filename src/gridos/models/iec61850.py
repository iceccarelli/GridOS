"""
IEC 61850 specific data models for GridOS.

Provides Pydantic representations of key IEC 61850 logical nodes and data
objects used in substation automation and DER integration.  These models
serve as a bridge between the IEC 61850 protocol adapter and the GridOS
common information model.

References:
    - IEC 61850-7-420: DER logical nodes
    - IEC 61850-7-4: Compatible logical node classes
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ── IEC 61850 Enumerations ───────────────────────────────────────────────────


class HealthKind(str, Enum):
    """IEC 61850 Health enumeration (CDC: INS)."""

    OK = "Ok"
    WARNING = "Warning"
    ALARM = "Alarm"


class BehaviourModeKind(str, Enum):
    """IEC 61850 Behaviour mode enumeration."""

    ON = "on"
    BLOCKED = "blocked"
    TEST = "test"
    TEST_BLOCKED = "test/blocked"
    OFF = "off"


class DERGeneratorStateKind(str, Enum):
    """Operating state of a DER generator (DGEN)."""

    NOT_OPERATING = "not_operating"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAULT = "fault"


class DERStorageModeKind(str, Enum):
    """Operating mode of a storage unit (DSTO)."""

    IDLE = "idle"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    STANDBY = "standby"


# ── IEC 61850 Data Objects ───────────────────────────────────────────────────


class Quality(BaseModel):
    """IEC 61850 Quality descriptor for measured values."""

    validity: str = Field(default="good", description="good | invalid | questionable")
    source: str = Field(default="process", description="process | substituted")
    test: bool = Field(default=False, description="True if value is a test value.")
    operator_blocked: bool = Field(default=False)


class AnalogueValue(BaseModel):
    """IEC 61850 Analogue value with quality and timestamp (MV CDC)."""

    mag_f: float = Field(..., description="Floating-point magnitude.")
    quality: Quality = Field(default_factory=Quality)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    unit: str = Field(default="", description="Engineering unit symbol.")


class StatusValue(BaseModel):
    """IEC 61850 Status value (SPS / DPS CDC)."""

    stval: bool = Field(..., description="Status value.")
    quality: Quality = Field(default_factory=Quality)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── IEC 61850 Logical Nodes ─────────────────────────────────────────────────


class LLN0(BaseModel):
    """Logical Node Zero — common attributes for every logical device."""

    health: HealthKind = Field(default=HealthKind.OK)
    behaviour: BehaviourModeKind = Field(default=BehaviourModeKind.ON)
    name_plate: dict[str, Any] = Field(default_factory=dict)


class MMXU(BaseModel):
    """Measurement logical node — three-phase electrical measurements.

    Represents IEC 61850 MMXU (Measurement – Multi-phase).
    """

    tot_w: AnalogueValue = Field(..., description="Total active power (W).")
    tot_var: AnalogueValue = Field(..., description="Total reactive power (VAR).")
    tot_va: AnalogueValue | None = Field(
        default=None, description="Total apparent power (VA)."
    )
    hz: AnalogueValue | None = Field(default=None, description="Frequency (Hz).")
    pph_v_a: AnalogueValue | None = Field(
        default=None, description="Phase A voltage (V)."
    )
    pph_v_b: AnalogueValue | None = Field(
        default=None, description="Phase B voltage (V)."
    )
    pph_v_c: AnalogueValue | None = Field(
        default=None, description="Phase C voltage (V)."
    )
    a_pha: AnalogueValue | None = Field(
        default=None, description="Phase A current (A)."
    )
    a_phb: AnalogueValue | None = Field(
        default=None, description="Phase B current (A)."
    )
    a_phc: AnalogueValue | None = Field(
        default=None, description="Phase C current (A)."
    )
    tot_pf: AnalogueValue | None = Field(
        default=None, description="Total power factor."
    )


class DGEN(BaseModel):
    """DER Generator logical node (IEC 61850-7-420).

    Represents the operating state and output of a DER generator such as
    a PV inverter or wind turbine.
    """

    gn_st: DERGeneratorStateKind = Field(
        default=DERGeneratorStateKind.NOT_OPERATING,
        description="Generator operating state.",
    )
    gn_op_tm_h: float | None = Field(
        default=None, description="Cumulative operating time (hours)."
    )
    w_max_rtg: float | None = Field(
        default=None, description="Maximum rated active power (W)."
    )
    measurements: MMXU | None = Field(
        default=None, description="Electrical measurements."
    )


class DSTO(BaseModel):
    """DER Storage logical node (IEC 61850-7-420).

    Represents a battery energy storage system with state-of-charge
    and operating mode.
    """

    sto_st: DERStorageModeKind = Field(
        default=DERStorageModeKind.IDLE,
        description="Storage operating mode.",
    )
    soc: AnalogueValue = Field(..., description="State of charge (%).")
    w_max_chrg: float | None = Field(
        default=None, description="Maximum charge power (W)."
    )
    w_max_dis: float | None = Field(
        default=None, description="Maximum discharge power (W)."
    )
    wh_rtg: float | None = Field(
        default=None, description="Rated energy capacity (Wh)."
    )
    measurements: MMXU | None = Field(
        default=None, description="Electrical measurements."
    )


class DRCT(BaseModel):
    """DER Controller logical node — setpoint and control interface.

    Provides the control interface for issuing active / reactive power
    setpoints to a DER.
    """

    w_set: AnalogueValue | None = Field(
        default=None, description="Active power setpoint (W)."
    )
    var_set: AnalogueValue | None = Field(
        default=None, description="Reactive power setpoint (VAR)."
    )
    op_tm_h: float | None = Field(
        default=None, description="Controller operating time (hours)."
    )
