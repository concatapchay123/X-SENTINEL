from __future__ import annotations

import logging
import os
from typing import Any

import psutil

from infrastructure.monitoring.metrics import get_metrics_registry, safe_record_metric

logger = logging.getLogger("x_sentinel.monitoring.telemetry")


def collect_system_telemetry() -> dict[str, Any]:
    """Collects authentic system and process performance telemetry via psutil.

    Strict Invariant:
    Under zero circumstances should simulated or fixed constants be reported.
    Every number originates from host OS inspection.
    """
    try:
        cpu_pct = float(psutil.cpu_percent(interval=None))
        vmem = psutil.virtual_memory()
        proc = psutil.Process(os.getpid())
        proc_mem = proc.memory_info()
        thread_cnt = int(proc.num_threads())

        telemetry: dict[str, Any] = {
            "status": "ok",
            "cpu": {
                "utilization_percent": round(cpu_pct, 2),
                "logical_cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False),
            },
            "memory": {
                "total_bytes": vmem.total,
                "available_bytes": vmem.available,
                "used_bytes": vmem.used,
                "used_percent": round(vmem.percent, 2),
            },
            "process": {
                "pid": os.getpid(),
                "rss_bytes": proc_mem.rss,
                "vms_bytes": proc_mem.vms,
                "thread_count": thread_cnt,
            },
        }

        # Update global Prometheus gauges fail-safe
        reg = get_metrics_registry()
        safe_record_metric(reg.gauge("system_cpu_percent").set, cpu_pct)
        safe_record_metric(reg.gauge("system_ram_used_bytes").set, float(vmem.used))
        safe_record_metric(reg.gauge("system_ram_percent").set, float(vmem.percent))
        safe_record_metric(reg.gauge("system_thread_count").set, float(thread_cnt))

        return telemetry
    except Exception as exc:
        logger.warning("Failed to collect authentic system telemetry: %s", exc)
        return {
            "status": "degraded",
            "error": str(exc),
        }
