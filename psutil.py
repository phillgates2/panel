"""Minimal psutil stub.

This repo ships a lightweight `psutil` shim to support environments where the
real `psutil` wheel may be unavailable.

Only a small subset of the psutil API is implemented — enough for the Panel
metrics collector and basic memory checks.
"""

import os
import time
import shutil
from dataclasses import dataclass
from typing import List


def _read_rss_bytes(pid: int) -> int:
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    # VmRSS: <value> kB
                    if len(parts) >= 2:
                        kb = int(parts[1])
                        return kb * 1024
    except Exception:
        pass
    # Fallback: 0 if unavailable
    return 0


@dataclass
class _MemInfo:
    rss: int


class Process:
    def __init__(self, pid: int):
        self._pid = int(pid)

    def memory_info(self) -> _MemInfo:
        return _MemInfo(rss=_read_rss_bytes(self._pid))


@dataclass
class _VirtMem:
    used: int


@dataclass
class _Partition:
    mountpoint: str


@dataclass
class _DiskUsage:
    used: int


def _read_cpu_times() -> List[int]:
    """Read aggregate CPU times from /proc/stat."""
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("cpu "):
                    parts = line.split()
                    # cpu user nice system idle iowait irq softirq steal guest guest_nice
                    return [int(p) for p in parts[1:9]]
    except Exception:
        pass
    return [0] * 8


def cpu_percent(interval: float = 0.0) -> float:
    """Return CPU utilization percentage (best-effort).

    The implementation samples /proc/stat twice with the provided interval.
    """
    t1 = _read_cpu_times()
    if interval and interval > 0:
        time.sleep(interval)
    t2 = _read_cpu_times()

    idle1 = t1[3] + t1[4]
    idle2 = t2[3] + t2[4]
    total1 = sum(t1)
    total2 = sum(t2)

    total_delta = max(0, total2 - total1)
    idle_delta = max(0, idle2 - idle1)
    if total_delta == 0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (total_delta - idle_delta) / total_delta))


def virtual_memory() -> _VirtMem:
    """Return a small virtual memory struct with `.used`."""
    mem_total = 0
    mem_available = 0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    mem_available = int(line.split()[1]) * 1024
    except Exception:
        pass
    used = max(0, mem_total - mem_available)
    return _VirtMem(used=used)


def disk_partitions() -> List[_Partition]:
    """Return a best-effort list of mountpoints from /proc/mounts."""
    partitions: List[_Partition] = []
    try:
        with open("/proc/mounts", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mountpoint = parts[1]
                    partitions.append(_Partition(mountpoint=mountpoint))
    except Exception:
        pass
    return partitions


def disk_usage(path: str) -> _DiskUsage:
    usage = shutil.disk_usage(path)
    return _DiskUsage(used=int(usage.used))
