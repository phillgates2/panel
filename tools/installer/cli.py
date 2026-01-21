import argparse
import logging
import json
from .core import install_all, uninstall_all, start_component_service, stop_component_service, get_component_service_status

log = logging.getLogger(__name__)


def build_parser():
    p = argparse.ArgumentParser(prog="panel-installer")
    sub = p.add_subparsers(dest="cmd")

    ip = sub.add_parser("install", help="Install panel and components")
    ip.add_argument("--domain", default="localhost", help="Panel domain name")
    ip.add_argument("--components", default=",".join(["postgres","redis","nginx","python"]))
    ip.add_argument("--venv-path", default="/opt/panel/venv", help="Target path for Python venv when installing python component")
    ip.add_argument("--dry-run", action="store_true")
    ip.add_argument("--no-elevate", action="store_true", help="Do not attempt elevation (useful for CI)")
    ip.add_argument("--auto-start", dest="auto_start", action="store_true", help="Auto-start Panel app service after install")
    ip.add_argument("--no-auto-start", dest="auto_start", action="store_false", help="Do not auto-start Panel app service after install")
    ip.set_defaults(auto_start=True)
    ip.add_argument("--json", action="store_true", help="Emit structured JSON output")

    up = sub.add_parser("uninstall", help="Uninstall panel")
    up.add_argument("--preserve-data", action="store_true")
    up.add_argument("--dry-run", action="store_true")
    up.add_argument("--no-elevate", action="store_true", help="Do not require admin for dry-run")
    up.add_argument("--components", default=None, help="Comma-separated components to stop before rollback (e.g. postgres,redis)")
    up.add_argument("--json", action="store_true", help="Emit structured JSON output")

    cp = sub.add_parser("check", help="Check system dependencies")
    cp.add_argument("--json", action="store_true", help="Emit structured JSON output")

    sp = sub.add_parser("service", help="Manage component services")
    sp.add_argument("action", choices=["start", "stop", "status"], help="Service action")
    sp.add_argument("--components", default=",".join(["postgres","redis","nginx"]), help="Comma-separated components to act on")
    sp.add_argument("--json", action="store_true", help="Emit structured JSON output")

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "install":
        comps = [c.strip() for c in args.components.split(",") if c.strip()]
        result = install_all(args.domain, comps, elevate=(not args.no_elevate), dry_run=args.dry_run, venv_path=args.venv_path, auto_start=args.auto_start)
        print(json.dumps(result) if args.json else result)
    elif args.cmd == "uninstall":
        comps = None
        if getattr(args, "components", None):
            comps = [c.strip() for c in args.components.split(",") if c.strip()]
        result = uninstall_all(preserve_data=args.preserve_data, dry_run=args.dry_run, components=comps, elevate=(not args.no_elevate))
        print(json.dumps(result) if args.json else result)
    elif args.cmd == "check":
        from .deps import check_system_deps, suggest_install_commands
        missing = check_system_deps()
        if args.json:
            sugg = suggest_install_commands(missing) if missing else None
            print(json.dumps({"missing": missing, "suggestion": sugg}))
        else:
            print(missing)
            if missing:
                sugg = suggest_install_commands(missing)
                if sugg:
                    print("\nSuggested install command:\n", sugg)
                else:
                    print("\nNo known package manager detected to suggest commands.")
    elif args.cmd == "service":
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
        output = {"status": "ok", "results": results}
        print(json.dumps(output) if args.json else output)
    else:
        parser.print_help()
