.PHONY: help install dev-install run test lint format clean docker-build docker-up docker-down

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	poetry install --no-dev

dev-install: ## Install all dependencies including dev
	poetry install

run: ## Run the MCP server locally
	poetry run python -m src.api.main

test: ## Run tests
	poetry run pytest

test-cov: ## Run tests with coverage
	poetry run pytest --cov=src --cov-report=html --cov-report=term

lint: ## Run linting
	poetry run flake8 src tests
	poetry run mypy src

format: ## Format code with black and isort
	poetry run black src tests
	poetry run isort src tests

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +

docker-build: ## Build Docker image
	docker-compose build

docker-up: ## Start services with Docker Compose
	docker-compose up -d

docker-down: ## Stop Docker Compose services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f mcp-server

docker-shell: ## Open shell in MCP server container
	docker-compose exec mcp-server /bin/bash

redis-cli: ## Connect to Redis CLI
	docker-compose exec redis redis-cli

fly-deploy: ## Deploy to Fly.io
	fly deploy

fly-logs: ## Show Fly.io logs
	fly logs

fly-secrets: ## Set Fly.io secrets (requires OPENAI_API_KEY and SECRET_KEY env vars)
	fly secrets set OPENAI_API_KEY=$(OPENAI_API_KEY) SECRET_KEY=$(SECRET_KEY) 