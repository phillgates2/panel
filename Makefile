.PHONY: help install test lint format clean dev docker-dev docs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Run tests with coverage
	PANEL_USE_SQLITE=1 pytest tests/ -v --cov=. --cov-report=html --cov-report=term

test-fast: ## Run tests without coverage
	PANEL_USE_SQLITE=1 pytest tests/ -v

lint: ## Run linters
	black --check .
	isort --check-only .
	flake8 . --exclude=venv,.venv,migrations --max-line-length=100
	bandit -r . --exclude ./venv,./.venv,./.git -ll

format: ## Format code with black and isort
	black .
	isort .

security: ## Run security checks
	bandit -r . --exclude ./venv,./.venv,./.git -ll
	safety check
	pip-audit

clean: ## Clean up generated files
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf dist/
	rm -rf build/

dev: ## Run development server
	PANEL_USE_SQLITE=1 FLASK_DEBUG=1 python app.py

dev-mariadb: ## Run development server with MariaDB
	python app.py

docker-dev: ## Run development environment with Docker
	docker-compose -f docker-compose.dev.yml up

docker-dev-build: ## Build and run development environment
	docker-compose -f docker-compose.dev.yml up --build

docker-stop: ## Stop Docker development environment
	docker-compose -f docker-compose.dev.yml down

docs: ## Generate documentation
	@echo "Documentation available in docs/"
	@echo "  - Database Management: docs/DATABASE_MANAGEMENT.md"
	@echo "  - API Documentation: docs/API_DOCUMENTATION.md"
	@echo "  - Troubleshooting: docs/TROUBLESHOOTING.md"

upgrade: ## Upgrade dependencies
	pip install --upgrade pip
	pip install --upgrade -r requirements.txt
	pip install --upgrade -r requirements-dev.txt

db-migrate: ## Create database migration
	FLASK_APP=migrations_init.py flask db migrate -m "$(message)"

db-upgrade: ## Apply database migrations
	FLASK_APP=migrations_init.py flask db upgrade

db-downgrade: ## Rollback database migration
	FLASK_APP=migrations_init.py flask db downgrade

db-init: ## Initialize migrations directory
	FLASK_APP=migrations_init.py flask db init

db-history: ## Show migration history
	FLASK_APP=migrations_init.py flask db history

db-current: ## Show current migration
	FLASK_APP=migrations_init.py flask db current

db-backup: ## Backup SQLite database
	@mkdir -p backups
	@if [ -f instance/panel.db ]; then \
		cp instance/panel.db backups/panel_$$(date +%Y%m%d_%H%M%S).db; \
		echo "Backup created: backups/panel_$$(date +%Y%m%d_%H%M%S).db"; \
	else \
		echo "No database found"; \
	fi

serve-prod: ## Run with gunicorn (production)
	gunicorn -w 4 -b 0.0.0.0:8080 app:app

worker: ## Run RQ worker
	python run_worker.py

coverage-report: ## Open coverage report in browser
	@if [ -f htmlcov/index.html ]; then \
		python -m webbrowser htmlcov/index.html; \
	else \
		echo "No coverage report found. Run 'make test' first."; \
	fi

check: lint test ## Run all checks (lint + test)

ci: install-dev lint test ## Run CI pipeline locally

.DEFAULT_GOAL := help
