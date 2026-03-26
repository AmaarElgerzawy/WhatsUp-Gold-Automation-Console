"""
Backward compatibility: re-export availability report API.
Availability logic lives in AvailabilityReport.py; scheduling in ReportScheduler.py.
"""
from scripts.reporting.AvailabilityReport import (
    get_device_groups,
    write_excel_for_group,
    get_active_monitor_availability,
    get_duration_from_seconds,
    OUTPUT_FOLDER,
)

__all__ = [
    "get_device_groups",
    "write_excel_for_group",
    "get_active_monitor_availability",
    "get_duration_from_seconds",
    "OUTPUT_FOLDER",
]
