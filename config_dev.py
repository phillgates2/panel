# Local dev PostgreSQL override for quick testing
# Prefer setting DATABASE_URL in your environment; this is a fallback.
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://paneluser:panelpass@127.0.0.1:5432/paneldb"
SECRET_KEY = "dev-local-change-me"
SQLALCHEMY_TRACK_MODIFICATIONS = False
