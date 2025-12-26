from tools.installer.components import postgres, redis, nginx, pythonenv
from tools.installer import state


def test_simulated_install_uninstall_sequence(tmp_path, monkeypatch):
    # Simulate installs by recording actions manually.
    path = tmp_path / "state.json"
    state.clear_state(path)

    # Simulate that installers ran and succeeded (we don't execute system package managers in CI)
    state.add_action({"component": "postgres", "meta": {"installed": True}}, path)
    state.add_action({"component": "redis", "meta": {"installed": True}}, path)
    state.add_action({"component": "nginx", "meta": {"installed": True}}, path)
    state.add_action({"component": "python", "meta": {"installed": True}}, path)

    # Dry-run rollback should not mutate state
    res = state.rollback(preserve_data=True, dry_run=True, path=path)
    assert res['status'] == 'ok'
    assert res['remaining'] == 4

    # Now monkeypatch component uninstalls to succeed and run rollback for real
    monkeypatch.setattr(postgres, 'uninstall', lambda preserve_data=True, dry_run=False: {"uninstalled": True})
    monkeypatch.setattr(redis, 'uninstall', lambda preserve_data=True, dry_run=False: {"uninstalled": True})
    monkeypatch.setattr(nginx, 'uninstall', lambda preserve_data=True, dry_run=False: {"uninstalled": True})
    monkeypatch.setattr(pythonenv, 'uninstall', lambda preserve_data=True, dry_run=False, target='/opt/panel/venv': {"uninstalled": True})

    res2 = state.rollback(preserve_data=True, dry_run=False, path=path)
    assert res2['status'] == 'ok'
    assert res2['remaining'] == 0
    st = state.read_state(path)
    assert st.get('actions') == []
