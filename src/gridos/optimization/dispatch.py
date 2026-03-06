"""
Real-time dispatch module for GridOS.

Applies the schedule produced by :class:`Scheduler` to physical devices
via the adapter layer.  Handles schedule interpolation, constraint
enforcement, and command generation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from gridos.adapters.base import BaseAdapter
from gridos.models.common import ControlCommand, ControlMode
from gridos.optimization.scheduler import ScheduleResult

logger = logging.getLogger(__name__)


class Dispatcher:
    """Real-time dispatch engine.

    Parameters
    ----------
    schedule:
        The optimised schedule to execute.
    adapters:
        Mapping of ``device_id`` to adapter instances.
    time_step_minutes:
        Granularity matching the scheduler.
    start_time:
        UTC start time of the schedule.
    """

    def __init__(
        self,
        schedule: ScheduleResult,
        adapters: dict[str, BaseAdapter],
        time_step_minutes: int = 15,
        start_time: datetime | None = None,
    ) -> None:
        self.schedule = schedule
        self.adapters = adapters
        self.time_step_minutes = time_step_minutes
        self.start_time = start_time or datetime.utcnow()
        self._current_step: int = 0
        self._dispatch_log: list[dict[str, Any]] = []

    @property
    def is_complete(self) -> bool:
        """Whether all schedule steps have been dispatched."""
        return self._current_step >= len(self.schedule.battery_power_kw)

    def get_current_setpoint(self) -> float | None:
        """Return the battery power setpoint for the current step."""
        if self.is_complete:
            return None
        return self.schedule.battery_power_kw[self._current_step]

    def _determine_step(self, now: datetime) -> int:
        """Determine the schedule step index for the given time."""
        elapsed = (now - self.start_time).total_seconds()
        step = int(elapsed / (self.time_step_minutes * 60))
        return min(step, len(self.schedule.battery_power_kw) - 1)

    async def dispatch_step(
        self,
        battery_device_id: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Dispatch the current schedule step to the battery.

        Parameters
        ----------
        battery_device_id:
            Device ID of the battery to control.
        now:
            Current UTC time (defaults to ``utcnow``).

        Returns
        -------
        dict
            Dispatch result with command details and success status.
        """
        if now is None:
            now = datetime.utcnow()

        step = self._determine_step(now)
        self._current_step = step

        if step >= len(self.schedule.battery_power_kw):
            logger.info("Schedule complete — no more steps to dispatch")
            return {"status": "complete", "step": step}

        setpoint_kw = self.schedule.battery_power_kw[step]

        command = ControlCommand(
            device_id=battery_device_id,
            mode=ControlMode.POWER_SETPOINT,
            setpoint_kw=setpoint_kw,
            duration_seconds=self.time_step_minutes * 60,
            source="scheduler",
        )

        adapter = self.adapters.get(battery_device_id)
        success = False
        if adapter is not None:
            try:
                success = await adapter.write_command(command)
            except Exception as exc:
                logger.error("Dispatch error for %s: %s", battery_device_id, exc)
        else:
            logger.warning("No adapter found for device %s", battery_device_id)

        result = {
            "status": "dispatched" if success else "failed",
            "step": step,
            "setpoint_kw": setpoint_kw,
            "command_id": str(command.command_id),
            "device_id": battery_device_id,
            "timestamp": now.isoformat(),
        }
        self._dispatch_log.append(result)
        logger.info(
            "Dispatched step %d: setpoint=%.2f kW, success=%s",
            step,
            setpoint_kw,
            success,
        )
        return result

    async def run_all(self, battery_device_id: str) -> list[dict[str, Any]]:
        """Dispatch all remaining schedule steps sequentially.

        This is primarily for testing — in production, use
        ``dispatch_step`` driven by a timer.
        """
        results: list[dict[str, Any]] = []
        for step_idx in range(self._current_step, len(self.schedule.battery_power_kw)):
            t = self.start_time + timedelta(minutes=step_idx * self.time_step_minutes)
            result = await self.dispatch_step(battery_device_id, now=t)
            results.append(result)
        return results

    def get_dispatch_log(self) -> list[dict[str, Any]]:
        """Return the full dispatch log."""
        return list(self._dispatch_log)
