def test_cms_index_empty(client):
    rv = client.get("/cms/")
    assert rv.status_code == 200
    assert b"No pages yet" in rv.data or b"Pages" in rv.data


def test_forum_index(client):
    rv = client.get("/forum/")
    assert rv.status_code == 200
    assert b"Forum" in rv.data


def test_forum_index_logged_in_missing_forum_tables(app, client, test_user):
    # Simulate a deployment where the main tables exist but forum tables are missing
    # (e.g., migrations not applied yet). The forum index intentionally swallows
    # those DB errors, but must rollback so later user lookups don't hit
    # InFailedSqlTransaction.
    from app import db
    from src.panel.forum import Post, Thread

    with app.app_context():
        # Drop forum tables only; keep User table for get_current_user().
        Post.__table__.drop(db.engine, checkfirst=True)
        Thread.__table__.drop(db.engine, checkfirst=True)

    with client.session_transaction() as sess:
        sess["user_id"] = test_user.id

    rv = client.get("/forum/")
    assert rv.status_code == 200
