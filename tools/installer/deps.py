import shutil
import platform


def check_system_deps():
    """Basic system dependency checks. Returns dict of missing utilities."""
    reqs = ["python3", "pip3"]
    sys_miss = {}
    for r in reqs:
        if shutil.which(r) is None:
            sys_miss[r] = "missing"

    # Check for common service managers
    osname = platform.system()
    if osname == "Linux":
        if shutil.which("systemctl") is None:
            sys_miss["systemctl"] = "missing"
    elif osname == "Darwin":
        if shutil.which("launchctl") is None:
            sys_miss["launchctl"] = "missing"
    elif osname == "Windows":
        # No simple CLI to check; assume Service Manager present.
        pass

    return sys_miss


def get_package_manager():
    """Detect a sensible package manager for the current system (best-effort)."""
    checks = [
        ("apt", "apt-get"),
        ("dnf", "dnf"),
        ("yum", "yum"),
        ("pacman", "pacman"),
        ("apk", "apk"),
        ("brew", "brew"),
        ("choco", "choco"),
        ("winget", "winget"),
    ]
    for name, binname in checks:
        if shutil.which(binname):
            return name
    return None


def suggest_install_commands(missing):
    """Return a best-effort install command string for the detected package manager.

    `missing` should be the dict returned by `check_system_deps()`.
    """
    if not missing:
        return None

    pm = get_package_manager()
    pkgs = []
    for k in missing.keys():
        # Map to plausible package names by manager (not exhaustive)
        if k == "python3":
            pkg = {
                "apt": "python3",
                "apk": "python3",
                "dnf": "python3",
                "yum": "python3",
                "pacman": "python",
                "brew": "python",
                "choco": "python",
                "winget": "Python.Python.3",
            }.get(pm, "python3")
        elif k == "pip3":
            pkg = {
                "apt": "python3-pip",
                "apk": "py3-pip",
                "dnf": "python3-pip",
                "yum": "python3-pip",
                "pacman": "python-pip",
                "brew": "pipx",
                "choco": "pip",
                "winget": "pip",
            }.get(pm, "python3-pip")
        elif k == "systemctl":
            pkg = "systemd"
        elif k == "launchctl":
            pkg = "launchd"
        else:
            pkg = k
        pkgs.append(pkg)

    if pm in ("apt",):
        return f"sudo apt-get update && sudo apt-get install -y {' '.join(pkgs)}"
    if pm in ("dnf",):
        return f"sudo dnf install -y {' '.join(pkgs)}"
    if pm in ("yum",):
        return f"sudo yum install -y {' '.join(pkgs)}"
    if pm == "pacman":
        return f"sudo pacman -Sy --noconfirm {' '.join(pkgs)}"
    if pm == "apk":
        return f"sudo apk add {' '.join(pkgs)}"
    if pm == "brew":
        return f"brew install {' '.join(pkgs)}"
    if pm == "choco":
        return f"choco install -y {' '.join(pkgs)}"
    if pm == "winget":
        return f"winget install --exact {' '.join(pkgs)}"

    return None
