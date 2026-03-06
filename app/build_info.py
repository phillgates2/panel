"""Build/runtime identification helpers.

This module is intentionally dependency-free so it can be imported in
minimal environments (including production containers) to emit a useful
build identifier to logs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def detect_git_sha(start_path: str | Path) -> Optional[str]:
    """Best-effort detection of the current git commit SHA.

    This reads `.git/HEAD` and referenced ref files directly (no `git` binary
    required). Returns None if a SHA cannot be determined.
    """

    try:
        start = Path(start_path).resolve()
    except Exception:
        return None

    for candidate in (start, *start.parents):
        git_dir = candidate / ".git"
        if not git_dir.is_dir():
            continue

        head_file = git_dir / "HEAD"
        try:
            head = head_file.read_text(encoding="utf-8").strip()
        except Exception:
            return None

        # Detached HEAD: HEAD contains the SHA directly.
        if head and not head.startswith("ref: "):
            return head

        # Symbolic ref: HEAD points to a ref.
        if head.startswith("ref: "):
            ref_path = head[len("ref: ") :].strip()
            if not ref_path:
                return None

            ref_file = git_dir / ref_path
            try:
                if ref_file.exists():
                    return ref_file.read_text(encoding="utf-8").strip()
            except Exception:
                return None

            # Some repos use packed-refs.
            packed_refs = git_dir / "packed-refs"
            try:
                if packed_refs.exists():
                    for line in packed_refs.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith("^"):
                            continue
                        sha, _, name = line.partition(" ")
                        if name.strip() == ref_path:
                            return sha
            except Exception:
                return None

        return None

    return None
