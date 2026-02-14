"""SSH-friendly terminal installer.

Provides a text-based flow suitable for remote/terminal sessions.
Streams progress and returns JSON summaries for automation.
"""
import argparse
import getpass
import re
import json
import logging
import os
import shutil
import sys
from typing import Any, Dict, List, Optional

from .core import install_all, uninstall_all, start_component_service, stop_component_service, get_component_service_status
from .deps import check_system_deps, suggest_install_commands

log = logging.getLogger(__name__)


def _progress_printer(step: str, component: str, meta: Dict[str, Any]):
    try:
        # Compact, machine-readable progress lines
        payload = {"step": step, "component": component, "meta": meta}
        print("PROGRESS:", json.dumps(payload, separators=(",", ":")))
    except Exception:
        print(f"PROGRESS: {step} {component} {meta}")


def build_parser():
    p = argparse.ArgumentParser(prog="panel-installer-ssh", description="Panel Installer (SSH/Terminal)")
    sub = p.add_subparsers(dest="cmd")

    ip = sub.add_parser("install", help="Install panel and components (streams progress)")
    ip.add_argument("--domain", default="localhost", help="Panel domain name")
    ip.add_argument("--components", default=",".join(["postgres","redis","nginx","python"]))
    ip.add_argument("--venv-path", default="/opt/panel/venv", help="Target path for Python venv when installing python component")
    ip.add_argument("--dry-run", action="store_true")
    ip.add_argument("--no-elevate", action="store_true", help="Do not attempt elevation (useful for CI)")
    ip.add_argument("--json", action="store_true", help="Emit final result JSON only (progress still streams)")
    ip.add_argument("--auto-start", dest="auto_start", action="store_true", help="Auto-start Panel app service after install")
    ip.add_argument("--no-auto-start", dest="auto_start", action="store_false", help="Do not auto-start Panel app service after install")
    ip.set_defaults(auto_start=True)

    ip.add_argument(
        "--create-default-user",
        dest="create_default_user",
        action="store_true",
        help="Create a default system admin user if none exists",
    )
    ip.add_argument(
        "--no-create-default-user",
        dest="create_default_user",
        action="store_false",
        help="Do not create a default system admin user",
    )
    ip.set_defaults(create_default_user=True)
    ip.add_argument("--admin-email", default=None, help="Admin username/email to create (Panel uses email as login)")
    ip.add_argument(
        "--admin-password",
        default=None,
        help="Admin password to set (WARNING: may be visible in shell history / process list). Prefer --admin-password-stdin.",
    )
    ip.add_argument(
        "--admin-password-stdin",
        action="store_true",
        help="Read admin password from stdin (single line).",
    )

    up = sub.add_parser("uninstall", help="Uninstall panel via recorded state (streams progress)")
    up.add_argument("--preserve-data", action="store_true")
    up.add_argument("--dry-run", action="store_true")
    up.add_argument("--no-elevate", action="store_true", help="Do not require admin for dry-run")
    up.add_argument("--components", default=None, help="Comma-separated components to stop before rollback (e.g. postgres,redis)")
    up.add_argument("--json", action="store_true", help="Emit final result JSON only (progress still streams)")

    sp = sub.add_parser("service", help="Manage component services")
    sp.add_argument("action", choices=["start", "stop", "status"], help="Service action")
    sp.add_argument("--components", default=",".join(["postgres","redis","nginx"]), help="Comma-separated components to act on")

    cp = sub.add_parser("check", help="Check system dependencies")

    wz = sub.add_parser("wizard", help="Interactive guided installer (SSH)")
    wz.add_argument("--json", action="store_true", help="Emit final result JSON only (progress still streams)")

    return p


def main(argv: Optional[List[str]] = None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "install":
        comps = [c.strip() for c in args.components.split(",") if c.strip()]

        admin_password = args.admin_password
        if getattr(args, "admin_password_stdin", False):
            # Read a single line from stdin. This avoids exposing the password in argv.
            admin_password = (sys.stdin.readline() or "").rstrip("\n")

        result = install_all(
            args.domain,
            comps,
            elevate=(not args.no_elevate),
            dry_run=args.dry_run,
            progress_cb=_progress_printer,
            venv_path=args.venv_path,
            auto_start=args.auto_start,
            create_default_user=args.create_default_user,
            admin_email=args.admin_email,
            admin_password=admin_password,
        )
        print(json.dumps(result) if args.json else result)
        return

    if args.cmd == "uninstall":
        comps = None
        if getattr(args, "components", None):
            comps = [c.strip() for c in args.components.split(",") if c.strip()]
        result = uninstall_all(
            preserve_data=args.preserve_data,
            dry_run=args.dry_run,
            components=comps,
            progress_cb=_progress_printer,
            elevate=(not args.no_elevate),
        )
        print(json.dumps(result) if args.json else result)
        return

    if args.cmd == "service":
        comps = [c.strip() for c in args.components.split(",") if c.strip()]
        results = []
        for c in comps:
            if args.action == "start":
                ok = start_component_service(c)
                results.append({"component": c, "started": ok})
            elif args.action == "stop":
                ok = stop_component_service(c)
                results.append({"component": c, "stopped": ok})
            elif args.action == "status":
                res = get_component_service_status(c)
                results.append({"component": c, **res})
        print({"status": "ok", "results": results})
        return

    if args.cmd == "check":
        missing = check_system_deps()
        print(missing)
        if missing:
            sugg = suggest_install_commands(missing)
            if sugg:
                print("\nSuggested install command:\n", sugg)
            else:
                print("\nNo known package manager detected to suggest commands.")
        return

    if args.cmd == "wizard":
        _run_wizard(json_only=args.json)
        return

    parser.print_help()


def _ask_input(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or (default or "")


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    while True:
        val = input(f"{prompt} ({d}): ").strip().lower()
        if not val:
            return default
        if val in ("y", "yes"): return True
        if val in ("n", "no"): return False
        print("Please answer 'y' or 'n'.")


def _parse_components(s: str) -> List[str]:
    return [c.strip() for c in s.split(',') if c.strip()]


def _validate_admin_email(value: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return "Email must not be empty"
    # Keep validation light; Panel uses email as login identifier.
    if "@" not in v or v.startswith("@") or v.endswith("@"): 
        return "Email must look like an email address (e.g. admin@example.com)"
    return None


def _validate_password_complexity(password: str) -> str | None:
    # Mirror src/panel/models.py complexity rules so the installer fails fast.
    if len(password or "") < 12:
        return "Password must be at least 12 characters long"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character"
    weak_passwords = {"password", "123456", "qwerty", "admin", "letmein", "password123"}
    if password.lower() in weak_passwords:
        return "Password is too common; choose a stronger password"
    return None


def _ask_admin_credentials(default_email: str = "admin@panel.local") -> tuple[str, str | None, bool]:
    """Return (email, password_or_none, password_generated).

    When password is None, the installer will auto-generate a strong password.
    """
    while True:
        email = _ask_input("Admin username/email (login email)", default=default_email).strip().lower()
        err = _validate_admin_email(email)
        if err:
            print(err)
            continue
        break

    print("Admin password: enter one now, or leave blank to auto-generate.")
    while True:
        pw1 = getpass.getpass("Admin password: ").strip()
        if not pw1:
            return email, None, True
        pw2 = getpass.getpass("Confirm password: ").strip()
        if pw1 != pw2:
            print("Passwords do not match. Try again.")
            continue
        perr = _validate_password_complexity(pw1)
        if perr:
            print(perr)
            continue
        return email, pw1, False


def _run_wizard(json_only: bool = False):
    print("Panel Installer (SSH Wizard)")
    print("This guided flow will help you install or uninstall components.")
    op = _ask_input("Choose operation [install|uninstall]", default="install").lower()
    if op not in ("install", "uninstall"):
        print("Unsupported operation. Aborting.")
        return

    if op == "install":
        domain = _ask_input("Domain", default="localhost")
        comps = _select_components_menu(
            choices=["postgres","redis","nginx","python"],
            preselected=["postgres","redis","nginx","python"],
            allow_empty=False,
        )
        if comps is None or not comps:
            print("No components selected. Aborting.")
            return
        dry_run = _ask_yes_no("Dry-run (simulate only)", default=True)
        no_elevate = _ask_yes_no("Skip elevation/admin", default=True)
        # If no-elevate, warn when system packages are selected and allow quick deselect
        if no_elevate:
            sys_comps = [c for c in comps if c in ("postgres", "redis", "nginx")]
            if sys_comps:
                print("\nNote: Without elevation, system packages may fail to install:")
                print(f"  Selected system components: {', '.join(sys_comps)}")
                print("  Suggest deselecting them or re-running with elevation.")
                if _ask_yes_no("Remove system components from selection now?", default=True):
                    comps = [c for c in comps if c not in sys_comps]
        # Auto-suggest a user-writable venv path when no-elevate is selected
        venv_path = "/opt/panel/venv"
        if "python" in comps:
            try:
                import os as _os
                if no_elevate:
                    home = _os.path.expanduser("~") or "/tmp"
                    suggested = _os.path.join(home, "panel", "venv")
                    venv_path = _ask_input("Python venv path", default=suggested)
                else:
                    venv_path = _ask_input("Python venv path", default=venv_path)
            except Exception:
                # Fallback to original prompt if home detection fails
                venv_path = _ask_input("Python venv path", default=venv_path)
        auto_start = _ask_yes_no("Auto-start Panel app after install", default=True)

        create_default_user = _ask_yes_no("Create default admin user", default=True)
        admin_email = None
        admin_password = None
        password_generated = False
        if create_default_user:
            admin_email, admin_password, password_generated = _ask_admin_credentials(default_email="admin@panel.local")
        print("\nSummary:")
        print(f"  Operation : install")
        print(f"  Domain    : {domain}")
        print(f"  Components: {', '.join(comps) or '(none)'}")
        if "python" in comps:
            print(f"  venv_path : {venv_path}")
            # Small note when no-elevate is set and venv path appears system-level
            try:
                import os as _os
                if no_elevate:
                    home = _os.path.expanduser("~") or ""
                    system_like = venv_path.startswith(('/opt', '/usr', '/var', '/etc')) and not venv_path.startswith(home)
                    if system_like:
                        print("  Note      : no-elevate + system-level venv path may fail (permissions)")
                        print("              Suggest a user path, e.g., ~/panel/venv")
                        if _ask_yes_no("Change venv path now?", default=True):
                            suggested = _os.path.join(home or "/tmp", "panel", "venv")
                            venv_path = _ask_input("Python venv path", default=suggested)
            except Exception:
                pass
            # Hint when service manager is absent
            try:
                from .service_manager import manager_available
                import platform as _pf
                if not manager_available():
                    osname = _pf.system()
                    print("  Note      : service manager not available")
                    if osname == "Linux":
                        print("              Linux: systemd (systemctl) missing; services won't auto-manage")
                        print("              Options: install systemd or use Docker Compose (docker compose up -d)")
                    elif osname == "Darwin":
                        print("              macOS: brew services not available; consider installing Homebrew")
                    elif osname == "Windows":
                        print("              Windows: Service Control (sc) not available; manage services manually")
            except Exception:
                pass
        print(f"  Dry-run   : {dry_run}")
        print(f"  No-elevate: {no_elevate}")
        if create_default_user:
            print(f"  Admin     : {admin_email}")
            print(f"  Password  : {'auto-generate' if password_generated else 'user-provided'}")
        else:
            print(f"  Admin     : (skip default admin creation)")
        if not _ask_yes_no("Proceed?", default=True):
            print("Aborted by user.")
            return

        # If the user requested elevation but we are not admin, do not call
        # install_all() directly. install_all() will re-exec the *same* argv to
        # elevate, which re-runs the wizard and looks like an infinite loop.
        # Instead, re-exec into the non-interactive `install` subcommand with
        # the captured selections so the elevated process performs the install.
        try:
            from .os_utils import is_admin

            if (not no_elevate) and (not dry_run) and (not is_admin()):
                if create_default_user and (not password_generated):
                    print(
                        "\nA custom admin password was provided, but the wizard needs to elevate and cannot safely pass it to the elevated process.\n"
                        "Re-run the wizard already elevated (e.g. 'sudo python3 -m tools.installer --ssh wizard') and try again."
                    )
                    return

                elev = shutil.which("pkexec") or shutil.which("sudo")
                if not elev:
                    print(
                        "\nElevation is required but no helper was found (pkexec/sudo).\n"
                        "Re-run as root/admin or choose 'Skip elevation/admin'."
                    )
                    return

                cmd = [
                    sys.executable,
                    "-m",
                    "tools.installer",
                    "--ssh",
                    "install",
                    "--domain",
                    domain,
                    "--components",
                    ",".join(comps),
                ]
                if "python" in comps:
                    cmd += ["--venv-path", venv_path]
                if dry_run:
                    cmd.append("--dry-run")
                if no_elevate:
                    cmd.append("--no-elevate")
                if auto_start:
                    cmd.append("--auto-start")
                else:
                    cmd.append("--no-auto-start")
                if not create_default_user:
                    cmd.append("--no-create-default-user")
                elif admin_email:
                    cmd += ["--admin-email", admin_email]
                if json_only:
                    cmd.append("--json")

                print(
                    f"\nElevation required; re-running install under {os.path.basename(elev)}..."
                )
                # Replace current process; elevated process runs install directly.
                os.execvp(elev, [os.path.basename(elev)] + cmd)
        except Exception as e:
            print(f"\nFailed to elevate and re-run install: {e}")
            return

        result = install_all(
            domain,
            comps,
            elevate=(not no_elevate),
            dry_run=dry_run,
            progress_cb=_progress_printer,
            venv_path=venv_path,
            auto_start=auto_start,
            create_default_user=create_default_user,
            admin_email=admin_email,
            admin_password=admin_password,
        )
        print(json.dumps(result) if json_only else result)
        return

    # uninstall
    preserve = _ask_yes_no("Preserve data during uninstall", default=True)
    dry_run = _ask_yes_no("Dry-run (simulate only)", default=True)
    no_elevate = _ask_yes_no("Skip elevation/admin", default=True)
    comps = _select_components_menu(
        choices=["postgres","redis","nginx"],
        preselected=[],
        allow_empty=True,
    )
    # None or empty => implies 'all' for stop phase (or no targeted pre-stop)
    if comps is not None and not comps:
        comps = None
    print("\nSummary:")
    print(f"  Operation : uninstall")
    print(f"  Preserve  : {preserve}")
    print(f"  Dry-run   : {dry_run}")
    print(f"  No-elevate: {no_elevate}")
    if comps:
        print(f"  Pre-stop  : {', '.join(comps)}")
    if not _ask_yes_no("Proceed?", default=True):
        print("Aborted by user.")
        return
    result = uninstall_all(
        preserve_data=preserve,
        dry_run=dry_run,
        components=comps,
        progress_cb=_progress_printer,
        elevate=(not no_elevate),
    )
    print(json.dumps(result) if json_only else result)
    return


def _select_components_menu(choices: List[str], preselected: Optional[List[str]] = None, allow_empty: bool = False) -> Optional[List[str]]:
    """Interactive number-based toggle menu for selecting components.

    - choices: available component names
    - preselected: initial selected items
    - allow_empty: whether empty selection is allowed (returns [])

    Returns list of selected components, [] if allowed and none chosen,
    or None if the user aborts.
    """
    selected = set(preselected or [])
    while True:
        print("\nSelect components (toggle by numbers, 'a' accept, 'n' none, 'q' abort)")
        for idx, name in enumerate(choices, start=1):
            mark = "[x]" if name in selected else "[ ]"
            print(f"  {idx}) {mark} {name}")
        resp = input("Enter numbers (e.g. 1 3), 'a' to accept: ").strip().lower()
        if resp in ("a", ""):  # accept
            if not selected and not allow_empty:
                print("Please select at least one component.")
                continue
            return list(selected)
        if resp in ("q", "quit", "exit"):
            return None
        if resp in ("n", "none"):
            selected.clear()
            if allow_empty:
                return []
            else:
                print("No selection. You can choose numbers or press 'a' to accept once selected.")
                continue
        if resp in ("all", "*", "@"):
            selected = set(choices)
            continue
        # toggle indices
        tokens = [t for t in re.split(r"[\s,]+", resp) if t]
        changed = False
        for t in tokens:
            if t.isdigit():
                i = int(t)
                if 1 <= i <= len(choices):
                    name = choices[i-1]
                    if name in selected:
                        selected.remove(name)
                    else:
                        selected.add(name)
                    changed = True
                else:
                    print(f"Ignoring out-of-range index: {t}")
            else:
                print(f"Ignoring invalid token: {t}")
        if not changed and tokens:
            print("No changes made. Enter valid indices, 'a' to accept, or 'q' to abort.")
