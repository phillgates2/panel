import argparse
import logging
from .core import install_all, uninstall_all

log = logging.getLogger(__name__)


def build_parser():
    p = argparse.ArgumentParser(prog="panel-installer")
    sub = p.add_subparsers(dest="cmd")

    ip = sub.add_parser("install", help="Install panel and components")
    ip.add_argument("--domain", default="localhost", help="Panel domain name")
    ip.add_argument("--components", default=",".join(["postgres","redis","nginx","python"]))
    ip.add_argument("--dry-run", action="store_true")

    up = sub.add_parser("uninstall", help="Uninstall panel")
    up.add_argument("--preserve-data", action="store_true")

    cp = sub.add_parser("check", help="Check system dependencies")

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "install":
        comps = [c.strip() for c in args.components.split(",") if c.strip()]
        print(install_all(args.domain, comps, dry_run=args.dry_run))
    elif args.cmd == "uninstall":
        print(uninstall_all(preserve_data=args.preserve_data))
    elif args.cmd == "check":
        from .deps import check_system_deps, suggest_install_commands
        missing = check_system_deps()
        print(missing)
        if missing:
            sugg = suggest_install_commands(missing)
            if sugg:
                print("\nSuggested install command:\n", sugg)
            else:
                print("\nNo known package manager detected to suggest commands.")
    else:
        parser.print_help()
