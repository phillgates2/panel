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

test-unit: ## Run unit tests only
	PANEL_USE_SQLITE=1 pytest tests/ -v -m unit

test-integration: ## Run integration tests only
	PANEL_USE_SQLITE=1 pytest tests/ -v -m integration

test-performance: ## Run performance tests only
	PANEL_USE_SQLITE=1 pytest tests/ -v -m performance

test-validate: ## Run basic validation script (no pytest required)
	python3 validate_enhanced_features.py

test-all: ## Run all tests including validation
	$(MAKE) test-validate
	$(MAKE) test

lint: ## Run all linting tools
	# Run ruff first (auto-fix simple issues)
	ruff check --fix . || true
	black --check .
	isort --check-only .
	flake8 . --exclude=venv,.venv,migrations --max-line-length=100
	bandit -r . --exclude ./venv,./.venv,./.git -ll
	mypy app/ services/ --config-file mypy.ini || true
	radon cc app/ services/ --min C --max 10 --show-complexity --total-average || true
	pydocstyle app/ services/ --convention=google --add-ignore=D100,D104,D105,D107,D203,D204,D213,D215,D400,D401,D402,D403,D404,D405,D406,D407,D408,D409,D410,D411,D412,D413,D414,D415,D416,D417 || true

format: ## Format code with black and isort
	black .
	isort .

mypy: ## Run mypy type checking
	mypy app/ services/ --config-file mypy.ini

radon: ## Run radon complexity analysis
	radon cc app/ services/ --min C --max 10 --show-complexity --total-average
	radon mi app/ services/ --min C --max 10 --show

pydocstyle: ## Run pydocstyle documentation checking
	pydocstyle app/ services/ --convention=google --add-ignore=D100,D104,D105,D107,D203,D204,D213,D215,D400,D401,D402,D403,D404,D405,D406,D407,D408,D409,D410,D411,D412,D413,D414,D415,D416,D417

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

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start Docker containers
	docker-compose up -d

docker-dev: ## Start development environment with additional tools
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-clean: ## Clean Docker containers, images, and volumes
	docker-compose down -v
	docker system prune -f
	docker image prune -f

docker-test: ## Run tests in Docker containers
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit

docker-security-scan: ## Run security scans on Docker images
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-e TRIVY_CACHE_DIR=/tmp/trivy \
		aquasecurity/trivy image --exit-code 0 --no-progress --format table \
		$(shell docker images --format "table {{.Repository}}:{{.Tag}}" | grep panel | head -1 | awk '{print $1}')

docker-validate: ## Validate Docker setup and configuration
	./validate-docker-setup.sh

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

ci-test: ## Run CI test suite locally
	PANEL_USE_SQLITE=1 pytest tests/ -v --cov=. --cov-report=html --cov-report=term --cov-fail-under=80

ci-lint: ## Run CI linting locally
	pre-commit run --all-files --show-diff-on-failure
	mypy app/ services/ --ignore-missing-imports --no-strict-optional || true
	radon cc app/ services/ -a -i A,B | grep -E " [1-9][0-9]+ " && echo "High complexity functions found!" || echo "Complexity check passed"

ci-security: ## Run CI security scans locally
	bandit -r . -f json -o bandit-report.json || true
	safety check --full-report || true
	pip-audit --format json || true

ci-validate: ## Run all CI checks locally
	$(MAKE) ci-lint
	$(MAKE) ci-test
	$(MAKE) ci-security
	$(MAKE) docker-validate

logs: ## Show recent application logs
	tail -f instance/logs/panel.log

logs-errors: ## Show recent error logs
	tail -f instance/logs/panel_errors.log

logs-audit: ## Show recent audit logs
	tail -f instance/audit_logs/security_audit.log

logs-performance: ## Show recent performance logs
	tail -f instance/logs/panel_performance.log

config-validate: ## Validate current configuration
	python -m flask config-validate

config-show: ## Show current configuration
	python -m flask config-show

config-check: ## Check configuration for common issues
	python -m flask config-check

config-template: ## Generate configuration template
	python -m flask config-template

.DEFAULT_GOAL := help
