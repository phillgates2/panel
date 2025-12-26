import pytest
from tools.installer.components import nginx, pythonenv


def test_nginx_dry_run_returns_cmd():
    res = nginx.install(dry_run=True)
    assert isinstance(res, dict)
    assert 'cmd' in res
    assert isinstance(res['cmd'], str)


def test_nginx_is_installed_check():
    assert isinstance(nginx.is_installed(), bool)


def test_pythonenv_dry_run_returns_cmd():
    res = pythonenv.install(dry_run=True, target='/tmp/panelvenv')
    assert isinstance(res, dict)
    assert 'cmd' in res
    assert isinstance(res['cmd'], str)


def test_pythonenv_is_installed_check():
    assert isinstance(pythonenv.is_installed(), bool)
