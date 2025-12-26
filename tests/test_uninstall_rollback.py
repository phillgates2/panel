import os
import json
import shutil
from tools.installer import state
from tools.installer.components import postgres, redis, nginx, pythonenv


def test_state_add_and_read(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    state.clear_state(path)
    state.add_action({"component": "postgres", "meta": {"installed": True}}, path)
    st = state.read_state(path)
    assert len(st.get("actions", [])) == 1


def test_rollback_calls_uninstall(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    state.clear_state(path)
    # record two actions
    state.add_action({"component": "postgres", "meta": {}}, path)
    state.add_action({"component": "python", "meta": {}}, path)

    called = []

    def fake_uninstall_postgres(preserve_data=True, dry_run=False):
        called.append(('postgres', preserve_data, dry_run))
        return {"uninstalled": True}

    def fake_uninstall_python(preserve_data=True, dry_run=False, target='/opt/panel/venv'):
        called.append(('python', preserve_data, dry_run, target))
        return {"uninstalled": True}

    monkeypatch.setattr(postgres, 'uninstall', fake_uninstall_postgres)
    monkeypatch.setattr(pythonenv, 'uninstall', fake_uninstall_python)

    res = state.rollback(preserve_data=True, dry_run=False, path=path)
    assert res['status'] == 'ok'
    # rollback should call python uninstall (last action) then postgres
    assert called[0][0] == 'python' and called[1][0] == 'postgres'

    # state cleared after rollback
    st = state.read_state(path)
    assert st.get('actions') == []


def test_rollback_dry_run(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    state.clear_state(path)
    state.add_action({"component": "redis", "meta": {}}, path)

    res = state.rollback(preserve_data=True, dry_run=True, path=path)
    assert res['status'] == 'ok'
    assert res['results'][0]['result'] == 'dry-run'
    # state should be cleared even after dry-run
    assert state.read_state(path).get('actions') == []
