#!/usr/bin/env python3
"""Compatibility wrapper for Ptero-Eggs import helpers.

The runtime sync code in :mod:`ptero_eggs_updater` imports helpers from
``scripts.import_ptero_eggs``.

The real implementation lives in ``tools/scripts/import_ptero_eggs.py``.
This wrapper keeps both paths working.
"""

from __future__ import annotations

from typing import Any, Dict


try:
    from tools.scripts.import_ptero_eggs import clean_game_type, extract_config_from_egg  # type: ignore
except Exception:  # pragma: no cover
    # Minimal fallbacks to avoid crashing app startup in ultra-minimal envs.
    def clean_game_type(name: str) -> str:  # type: ignore
        return (name or "").strip().lower().replace(" ", "_")

    def extract_config_from_egg(egg_data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {}


__all__ = ["clean_game_type", "extract_config_from_egg"]


def main() -> int:
    # This wrapper is primarily for imports. Keep a minimal CLI entrypoint.
    print("Ptero-Eggs import helper wrapper (see tools/scripts/import_ptero_eggs.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
