def test_module_app_rolls_back_and_removes_session(monkeypatch):
    import app as app_module
    from app.db import db

    calls = {"rollback": 0, "remove": 0}

    def _rollback():
        calls["rollback"] += 1

    def _remove():
        calls["remove"] += 1

    monkeypatch.setattr(db.session, "rollback", _rollback, raising=True)
    monkeypatch.setattr(db.session, "remove", _remove, raising=True)

    teardown_funcs = app_module.app.teardown_request_funcs.get(None, [])
    assert teardown_funcs, "Expected at least one teardown_request handler"

    # Simulate request teardown after an exception
    for func in teardown_funcs:
        func(Exception("boom"))

    assert calls["rollback"] >= 1
    assert calls["remove"] >= 1


def test_factory_app_rolls_back_and_removes_session(monkeypatch):
    from app.db import db
    from app.factory import create_app

    calls = {"rollback": 0, "remove": 0}

    def _rollback():
        calls["rollback"] += 1

    def _remove():
        calls["remove"] += 1

    monkeypatch.setattr(db.session, "rollback", _rollback, raising=True)
    monkeypatch.setattr(db.session, "remove", _remove, raising=True)

    flask_app = create_app()
    teardown_funcs = flask_app.teardown_request_funcs.get(None, [])
    assert teardown_funcs, "Expected at least one teardown_request handler"

    for func in teardown_funcs:
        func(Exception("boom"))

    assert calls["rollback"] >= 1
    assert calls["remove"] >= 1
