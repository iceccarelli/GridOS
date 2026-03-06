"""
GridOS energy management and optimization.

Provides a Mixed-Integer Linear Programming (MILP) scheduler for optimal
DER dispatch and a real-time dispatch module that applies the schedule.
"""

from gridos.optimization.scheduler import Scheduler

__all__ = ["Scheduler"]
