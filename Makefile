.PHONY: help install dev test lint format clean docker run docs

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install GridOS in production mode
	pip install -r requirements/base.txt
	pip install -e .

dev: ## Install GridOS in development mode
	pip install -r requirements/base.txt -r requirements/dev.txt
	pip install -e ".[dev]"

test: ## Run the test suite with coverage
	pytest tests/ -v --cov=gridos --cov-report=term-missing --tb=short

lint: ## Run linting checks
	ruff check src/ tests/
	ruff format --check src/ tests/

format: ## Auto-format code
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck: ## Run type checking
	mypy src/gridos/ --ignore-missing-imports

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

docker: ## Build Docker image
	docker build -t gridos:latest .

docker-up: ## Start all services with Docker Compose
	docker-compose up --build -d

docker-down: ## Stop all Docker Compose services
	docker-compose down

run: ## Run the API server locally
	uvicorn gridos.main:app --host 0.0.0.0 --port 8000 --reload

demo: ## Run the quick start demo
	PYTHONPATH=src python notebooks/01_quickstart.py
