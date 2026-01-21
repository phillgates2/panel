import os
import sys


def _run_cli():
    from .cli import main as cli_main
    # Strip our control flag if present
    argv = [a for a in sys.argv[1:] if a != "--cli"]
    cli_main(argv)


def _run_gui():
    try:
        from .gui import run_gui
        run_gui()
    except Exception as e:
        print("GUI failed; falling back to CLI:", e)
        _run_cli()


def _run_ssh():
    from .ssh import main as ssh_main
    argv = [a for a in sys.argv[1:] if a != "--ssh"]
    ssh_main(argv)


if __name__ == '__main__':
    mode = os.environ.get("PANEL_INSTALLER_MODE", "").lower()
    if "--ssh" in sys.argv or mode == "ssh":
        _run_ssh()
    elif "--cli" in sys.argv or mode == "cli":
        _run_cli()
    else:
        _run_gui()
