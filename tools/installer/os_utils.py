import os
import sys
import platform


def is_admin():
    """Return True if running as root/admin."""
    if platform.system() == "Windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def ensure_elevated():
    """Try to re-run the process with elevated privileges.

    Behavior:
      - Windows: use ShellExecute with "runas" to re-launch the same Python executable
      - macOS: use `osascript` to run the same command with administrator privileges
      - Linux/Unix: try `pkexec` then `sudo` to re-exec the process

    On success this function will either re-exec into an elevated process or exit
    the current process. On failure it raises RuntimeError with a user-facing message.
    """
    if is_admin():
        return True

    osname = platform.system()
    if osname == "Windows":
        # Use ShellExecute to re-run as admin
        try:
            import ctypes
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            r = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            if int(r) <= 32:
                raise RuntimeError(f"ShellExecute returned {r}")
            # If ShellExecute succeeded the elevated process will start; exit current
            sys.exit(0)
        except Exception as e:
            raise RuntimeError(f"Failed to elevate on Windows: {e}")

    if osname == "Darwin":
        # Use osascript to ask for admin and run the same command
        try:
            import subprocess, shlex
            cmd = ' '.join([shlex.quote(arg) for arg in [sys.executable] + sys.argv])
            osa = f'do shell script "{cmd}" with administrator privileges'
            subprocess.check_call(["osascript", "-e", osa])
            # elevated command ran, exit current
            sys.exit(0)
        except Exception as e:
            raise RuntimeError(f"Failed to elevate on macOS: {e}")

    # Fallback for Linux/Unix-like: try pkexec -> sudo
    import shutil
    for elev in ("pkexec", "sudo"):
        if shutil.which(elev):
            try:
                os.execvp(elev, [elev, sys.executable] + sys.argv)
            except Exception as e:
                raise RuntimeError(f"Failed to re-exec with {elev}: {e}")

    raise RuntimeError("No elevation helper found (pkexec/sudo). Please re-run as root or install a polkit helper.")


def detect_elevation_methods():
    """Detect available elevation helpers without attempting to execute them.

    Returns a list of method names that are available on the system.
    """
    methods = []
    import shutil
    osname = platform.system()
    if osname == "Windows":
        try:
            import ctypes
            # We assume ShellExecuteW is available when ctypes.windll.shell32 exists
            if hasattr(ctypes, 'windll') and hasattr(ctypes.windll, 'shell32'):
                methods.append('shell_execute')
        except Exception:
            pass
    elif osname == "Darwin":
        if shutil.which('osascript'):
            methods.append('osascript')
    else:
        # Linux/Unix
        if shutil.which('pkexec'):
            methods.append('pkexec')
        if shutil.which('sudo'):
            methods.append('sudo')
    return methods
