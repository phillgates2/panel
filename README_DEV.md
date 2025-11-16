Local dev run instructions

- create a virtualenv and install deps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- run with SQLite dev config using panel.sh (preferred)

```bash
# Initialize and start via unified CLI
./panel.sh install    # interactive local install
./panel.sh start      # start dev server
```

- legacy direct run (advanced / debugging)

```bash
# Use the dev config directly
python -c "import app, config_dev; print('creating DB...'); from app import db; db.create_all()"
python app.py
```

- run tests

```bash
pytest -q
```

Deprecated helper scripts (use panel.sh instead):
- scripts/install.sh
- scripts/update.sh
- scripts/uninstall.sh
- start-dev.sh
