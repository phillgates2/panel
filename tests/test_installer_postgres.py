import pytest
from tools.installer.components import postgres


def test_postgres_dry_run_returns_cmd():
    res = postgres.install(dry_run=True)
    assert isinstance(res, dict)
    assert 'cmd' in res
    assert isinstance(res['cmd'], str)


def test_postgres_is_installed_check():
    # Should be a boolean; we don't require it to be True in CI
    assert isinstance(postgres.is_installed(), bool)
