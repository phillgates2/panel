Local dev run instructions

- create a virtualenv and install deps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- run with SQLite dev config

```bash
# Use the dev config
python -c "import app, config_dev; print('creating DB...'); from app import db; db.create_all()"
# start the app
python app.py
```

- run tests

```bash
pytest -q
```
