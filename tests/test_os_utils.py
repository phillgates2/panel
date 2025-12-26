import os
import platform
import shutil
import pytest
from tools.installer import os_utils


def test_ensure_elevated_no_helper_linux(monkeypatch):
    # Simulate non-root and no pkexec/sudo available
    monkeypatch.setattr(os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(shutil, 'which', lambda name: None)

    with pytest.raises(RuntimeError):
        os_utils.ensure_elevated()


def test_ensure_elevated_windows_shell_exec_fail(monkeypatch):
    monkeypatch.setattr(os, 'geteuid', lambda: 1)
    monkeypatch.setattr(platform, 'system', lambda: 'Windows')

    class FakeShell:
        def __init__(self):
            pass
    # Monkeypatch ctypes.windll.shell32.ShellExecuteW to return a failure code
    fake = type('X', (), {'windll': type('Y', (), {'shell32': type('Z', (), {'ShellExecuteW': lambda *a, **k: 1})})})

    monkeypatch.setitem(__import__('sys').modules, 'ctypes', fake)

    with pytest.raises(RuntimeError):
        os_utils.ensure_elevated()
