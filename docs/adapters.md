# GridOS Protocol Adapters

GridOS provides a pluggable adapter framework for communicating with field devices using industry-standard protocols. Each adapter inherits from `BaseAdapter` and implements a consistent async interface.

## Supported Protocols

| Protocol | Module | Status | Use Case |
|----------|--------|--------|----------|
| Modbus TCP | `adapters.modbus` | Production | Inverters, meters, PLCs |
| MQTT | `adapters.mqtt` | Production | IoT sensors, cloud gateways |
| DNP3 | `adapters.dnp3` | Stub | SCADA, utility RTUs |
| IEC 61850 | `adapters.iec61850` | Stub | Substation IEDs |
| OPC-UA | `adapters.opcua` | Production | Industrial PLCs, SCADA |

## Base Adapter Interface

All adapters implement the following async methods:

```python
class BaseAdapter(ABC):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def read_telemetry(self) -> DERTelemetry: ...
    async def write_command(self, command: ControlCommand) -> bool: ...
    async def health_check(self) -> bool: ...
```

## Modbus TCP Adapter

The Modbus adapter communicates with devices using the Modbus TCP protocol via the `pymodbus` library.

### Configuration

```python
from gridos.adapters.modbus import ModbusAdapter

adapter = ModbusAdapter(
    device_id="inverter-001",
    host="192.168.1.100",
    port=502,
    unit_id=1,
    register_map={
        "power_kw": {"address": 40001, "count": 2, "scale": 0.1},
        "voltage_v": {"address": 40003, "count": 1, "scale": 0.1},
        "current_a": {"address": 40004, "count": 1, "scale": 0.01},
    },
)
```

## MQTT Adapter

The MQTT adapter subscribes to device topics and publishes control commands.

### Configuration

```python
from gridos.adapters.mqtt import MQTTAdapter

adapter = MQTTAdapter(
    device_id="sensor-001",
    broker_host="mqtt.example.com",
    broker_port=1883,
    topic_telemetry="gridos/devices/sensor-001/telemetry",
    topic_command="gridos/devices/sensor-001/command",
)
```

## Creating a Custom Adapter

To add support for a new protocol:

1. Create a new file in `src/gridos/adapters/`
2. Inherit from `BaseAdapter`
3. Implement all abstract methods
4. Add tests in `tests/test_adapters.py`

```python
from gridos.adapters.base import BaseAdapter

class MyProtocolAdapter(BaseAdapter):
    async def connect(self) -> None:
        # Establish connection
        ...

    async def read_telemetry(self) -> DERTelemetry:
        # Read and return telemetry
        ...
```
