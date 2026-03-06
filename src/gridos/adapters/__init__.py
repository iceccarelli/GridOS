"""
GridOS protocol adapters.

Provides a unified interface for communicating with Distributed Energy
Resources over various industrial protocols (Modbus TCP/RTU, MQTT, DNP3,
IEC 61850, OPC-UA).  All adapters inherit from :class:`BaseAdapter` and
expose the same async API.
"""

from gridos.adapters.base import BaseAdapter

__all__ = ["BaseAdapter"]
