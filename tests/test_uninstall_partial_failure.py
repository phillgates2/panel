import os
from tools.installer import state
from tools.installer.components import postgres, pythonenv


def test_partial_failure_leaves_failed_action(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    state.clear_state(path)

    # Record two actions: postgres then python
    state.add_action({"component": "postgres", "meta": {}}, path)
    state.add_action({"component": "python", "meta": {}}, path)

    # Make python uninstall fail, postgres success
    def fake_uninstall_python(preserve_data=True, dry_run=False, target='/opt/panel/venv'):
        raise RuntimeError("simulated failure")

    def fake_uninstall_postgres(preserve_data=True, dry_run=False):
        return {"uninstalled": True}

    monkeypatch.setattr(pythonenv, 'uninstall', fake_uninstall_python)
    monkeypatch.setattr(postgres, 'uninstall', fake_uninstall_postgres)

    res = state.rollback(preserve_data=True, dry_run=False, path=path)
    assert res['status'] == 'ok'
    # python was attempted first and failed -> should remain; postgres succeeded and be removed
    assert res['remaining'] == 1
    st = state.read_state(path)
    assert len(st.get('actions', [])) == 1
    assert st['actions'][0]['component'] == 'python'
