import platform
import subprocess
import shutil
from tools.installer import service_manager as sm


class Dummy:
    pass


def test_enable_start_stop_linux(monkeypatch):
    monkeypatch.setattr(platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(shutil, 'which', lambda name: '/bin/systemctl' if name == 'systemctl' else None)
    called = []

    def fake_check_call(cmd, shell=False):
        called.append((cmd, shell))
        return 0

    monkeypatch.setattr(subprocess, 'check_call', fake_check_call)

    r = sm.enable_service('postgresql')
    assert r.get('ok')
    r = sm.start_service('postgresql')
    assert r.get('ok')
    r = sm.stop_service('postgresql')
    assert r.get('ok')


def test_enable_on_macos_falls_back(monkeypatch):
    monkeypatch.setattr(platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(shutil, 'which', lambda name: None)

    r = sm.enable_service('postgresql')
    assert r.get('ok') is False
    assert 'macOS' not in r.get('error', '')  # message generic


def test_windows_start_stop(monkeypatch):
    monkeypatch.setattr(platform, 'system', lambda: 'Windows')
    monkeypatch.setattr(shutil, 'which', lambda name: 'C:\\Windows\\System32\\sc.exe' if name == 'sc' else None)

    def fake_check(cmd, shell=False):
        return 0

    monkeypatch.setattr(subprocess, 'check_call', fake_check)
    r = sm.enable_service('postgresql')
    assert r.get('ok')
    r = sm.start_service('postgresql')
    assert r.get('ok')
    r = sm.stop_service('postgresql')
    assert r.get('ok')
