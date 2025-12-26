import pytest
from tools.installer.components import redis


def test_redis_dry_run_returns_cmd():
    res = redis.install(dry_run=True)
    assert isinstance(res, dict)
    assert 'cmd' in res
    assert isinstance(res['cmd'], str)


def test_redis_is_installed_check():
    assert isinstance(redis.is_installed(), bool)
