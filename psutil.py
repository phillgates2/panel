# Minimal psutil stub for test environment on Alpine without native wheels
# Provides only what tests require: Process.memory_info().rss
import os
from dataclasses import dataclass


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
