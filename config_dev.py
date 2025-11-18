# Local dev SQLite override for quick testing
SQLALCHEMY_DATABASE_URI = "sqlite:///panel_dev.db"
SECRET_KEY = "dev-local-change-me"
SQLALCHEMY_TRACK_MODIFICATIONS = False
