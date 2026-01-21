import os
import sys
from pathlib import Path


def _run_cli():
    _ensure_package()
    try:
        from .cli import main as cli_main
    except Exception:
        # Fallback if relative import fails when executed as a script
        from tools.installer.cli import main as cli_main
    # Strip our control flag if present
    argv = [a for a in sys.argv[1:] if a != "--cli"]
    cli_main(argv)


def _run_gui():
    try:
        _ensure_package()
        try:
            from .gui import run_gui
        except Exception:
            from tools.installer.gui import run_gui
        run_gui()
    except Exception as e:
        print("GUI failed; falling back to CLI:", e)
        _run_cli()


def _run_ssh():
    _ensure_package()
    try:
        from .ssh import main as ssh_main
    except Exception:
        from tools.installer.ssh import main as ssh_main
    argv = [a for a in sys.argv[1:] if a != "--ssh"]
    ssh_main(argv)


def _ensure_package():
    """Ensure repo root is on sys.path so absolute imports work
    when this file is executed directly (not via -m).
    """
    # If running as a package, nothing to do
    if __package__:
        return
    try:
        this = Path(__file__).resolve()
        # tools/installer/__main__.py -> repo root is parent of 'tools'
        repo_root = this.parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
    except Exception:
        pass


if __name__ == '__main__':
    mode = os.environ.get("PANEL_INSTALLER_MODE", "").lower()
    if "--ssh" in sys.argv or mode == "ssh":
        _run_ssh()
    elif "--cli" in sys.argv or mode == "cli":
        _run_cli()
    else:
        _run_gui()
