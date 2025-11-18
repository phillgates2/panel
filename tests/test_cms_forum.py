def test_cms_index_empty(client):
    rv = client.get("/cms/")
    assert rv.status_code == 200
    assert b"No pages yet" in rv.data or b"Pages" in rv.data


def test_forum_index(client):
    rv = client.get("/forum/")
    assert rv.status_code == 200
    assert b"Forum" in rv.data
