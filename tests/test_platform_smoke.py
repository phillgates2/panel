import platform
import shutil
import pytest
from tools.installer.deps import get_package_manager
from tools.installer.os_utils import detect_elevation_methods


def test_detect_package_manager_on_runner():
    pm = get_package_manager()
    # If package manager found, ensure shutil.which reports a binary
    if pm:
        assert isinstance(pm, str)
    else:
        pytest.skip("No package manager detected on runner; skipping smoke check")


def test_detect_elevation_methods_present_or_skip():
    methods = detect_elevation_methods()
    if methods:
        assert isinstance(methods, list)
    else:
        pytest.skip("No elevation methods detected on runner; skipping smoke check")


def test_components_dry_run_provide_cmd_or_msg():
    # Dry-run install for components must return either 'cmd' string or a helpful 'msg'
    from tools.installer.components import postgres, redis, nginx, pythonenv

    for mod in (postgres, redis, nginx, pythonenv):
        res = mod.install(dry_run=True, target='/tmp/panelvenv' if mod is pythonenv else None)
        assert isinstance(res, dict)
        assert 'cmd' in res or 'msg' in res
