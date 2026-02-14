import json
import os
import platform
import subprocess


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def find_panel_requirements_file(repo_root: str | None = None) -> str | None:
    root = repo_root or _repo_root()
    candidates = [
        os.path.join(root, "requirements", "requirements.txt"),
        os.path.join(root, "requirements.txt"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _venv_python(venv_path: str) -> str:
    if platform.system() == "Windows":
        return os.path.join(venv_path, "Scripts", "python.exe")
    return os.path.join(venv_path, "bin", "python")


def check_requirements_installed(
    *,
    venv_path: str,
    requirements_path: str,
) -> dict:
    """Return whether the venv satisfies the requirements file.

    This runs the check *inside the venv* using importlib.metadata, so we're
    validating the environment that the Panel service will run under.
    """
    python = _venv_python(venv_path)
    if not os.path.exists(python):
        return {
            "ok": False,
            "error": "venv python not found",
            "venv_path": venv_path,
            "python": python,
            "requirements": requirements_path,
        }
    if not os.path.exists(requirements_path):
        return {
            "ok": False,
            "error": "requirements file not found",
            "venv_path": venv_path,
            "python": python,
            "requirements": requirements_path,
        }

    code = r"""
import json
import os
import sys
from importlib import metadata as im

REQ_PATH = sys.argv[1]

def _load_requirement_parser():
    # Prefer pip's vendored packaging because it exists when pip exists.
    try:
        from pip._vendor.packaging.requirements import Requirement  # type: ignore
        return Requirement, None
    except Exception as e1:
        try:
            from packaging.requirements import Requirement  # type: ignore
            return Requirement, None
        except Exception as e2:
            return None, f"Requirement parser unavailable (install 'packaging' or 'pip'): {e1} / {e2}"


Requirement, req_err = _load_requirement_parser()
if Requirement is None:
    print(json.dumps({"ok": False, "error": req_err, "requirements": REQ_PATH}))
    raise SystemExit(2)


def _iter_lines(path, seen):
    ap = os.path.abspath(path)
    if ap in seen:
        return
    seen.add(ap)
    base = os.path.dirname(ap)
    try:
        with open(ap, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                # Support nested -r includes.
                if line.startswith("-r") or line.startswith("--requirement"):
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        inc = parts[1].strip().strip('"').strip("'")
                        inc_path = inc if os.path.isabs(inc) else os.path.join(base, inc)
                        yield from _iter_lines(inc_path, seen)
                    continue
                # Skip constraints and options.
                if line.startswith("-c") or line.startswith("--constraint"):
                    continue
                if line.startswith("--"):
                    continue
                yield line
    except Exception as e:
        yield f"__READ_ERROR__:{ap}:{e}"


missing = []
mismatched = []
skipped = []
read_errors = []
checked = 0

for line in _iter_lines(REQ_PATH, seen=set()):
    if line.startswith("__READ_ERROR__:"):
        read_errors.append(line)
        continue
    # Editable/VCS/local paths are not reliably checkable via metadata.
    if line.startswith("-e") or "://" in line or line.startswith(".") or line.startswith("/"):
        skipped.append(line)
        continue
    try:
        req = Requirement(line)
    except Exception:
        skipped.append(line)
        continue

    try:
        if getattr(req, "marker", None) is not None and not req.marker.evaluate():
            continue
    except Exception:
        # If marker evaluation fails, be conservative and attempt to check.
        pass

    name = getattr(req, "name", None)
    if not name:
        skipped.append(line)
        continue

    checked += 1
    try:
        ver = im.version(name)
    except im.PackageNotFoundError:
        missing.append({"name": name, "specifier": str(req.specifier), "line": line})
        continue
    except Exception as e:
        skipped.append(f"{line}  # metadata error: {e}")
        continue

    try:
        spec = getattr(req, "specifier", None)
        if spec and str(spec):
            if not spec.contains(ver, prereleases=True):
                mismatched.append({"name": name, "installed": ver, "required": str(spec), "line": line})
    except Exception as e:
        skipped.append(f"{line}  # specifier check error: {e}")

ok = (not missing) and (not mismatched) and (not read_errors)
print(json.dumps({
    "ok": ok,
    "requirements": REQ_PATH,
    "checked": checked,
    "missing": missing,
    "mismatched": mismatched,
    "skipped": skipped,
    "read_errors": read_errors,
}))
"""

    proc = subprocess.run(
        [python, "-c", code, requirements_path],
        text=True,
        capture_output=True,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    data = None
    if stdout:
        # Tool should print only JSON; still be defensive.
        for line in reversed(stdout.splitlines()):
            try:
                data = json.loads(line)
                break
            except Exception:
                continue
    if not isinstance(data, dict):
        return {
            "ok": False,
            "error": "failed to parse requirements check output",
            "returncode": proc.returncode,
            "stdout": stdout[-4000:],
            "stderr": stderr[-4000:],
            "venv_path": venv_path,
            "python": python,
            "requirements": requirements_path,
        }
    data.setdefault("returncode", proc.returncode)
    data.setdefault("stderr", stderr[-4000:])
    data.setdefault("python", python)
    data.setdefault("venv_path", venv_path)
    return data


def install_requirements(
    *,
    venv_path: str,
    requirements_path: str,
) -> dict:
    """Best-effort: install requirements into the venv."""
    python = _venv_python(venv_path)
    if not os.path.exists(python):
        return {"ok": False, "error": "venv python not found", "python": python, "venv_path": venv_path}
    if not os.path.exists(requirements_path):
        return {"ok": False, "error": "requirements file not found", "requirements": requirements_path}

    def _run(cmd: list[str]) -> tuple[int, str, str]:
        p = subprocess.run(cmd, text=True, capture_output=True)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()

    def _network_hint(stderr: str) -> str | None:
        s = (stderr or "").lower()
        needles = [
            "temporary failure in name resolution",
            "name or service not known",
            "failed to establish a new connection",
            "nodename nor servname provided",
            "read time out",
            "readtimeouterror",
            "connection timed out",
            "max retries exceeded",
        ]
        if any(n in s for n in needles):
            return "Network/DNS error reaching PyPI. Fix DNS/connectivity (e.g. ensure the host can resolve files.pythonhosted.org) and re-run the installer."
        return None

    # Ensure pip exists in the venv.
    rc, out, err = _run([python, "-m", "pip", "--version"])
    if rc != 0:
        rc2, out2, err2 = _run([python, "-m", "ensurepip", "--upgrade"])
        if rc2 != 0:
            return {
                "ok": False,
                "error": "pip missing and ensurepip failed",
                "pip_check": {"returncode": rc, "stdout": out[-2000:], "stderr": err[-2000:]},
                "ensurepip": {"returncode": rc2, "stdout": out2[-2000:], "stderr": err2[-2000:]},
            }

    cmd = [python, "-m", "pip", "install", "--disable-pip-version-check", "-r", requirements_path]
    rc3, out3, err3 = _run(cmd)
    hint = _network_hint(err3)
    return {
        "ok": rc3 == 0,
        "cmd": " ".join(cmd),
        "returncode": rc3,
        "stdout": out3[-4000:],
        "stderr": err3[-4000:],
        "hint": hint,
        "requirements": requirements_path,
        "python": python,
        "venv_path": venv_path,
    }
