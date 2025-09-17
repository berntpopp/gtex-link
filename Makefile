.PHONY: help install lint format typecheck test test-cov clean dev-setup check-all fix server mcp mcp-http unified-server cli-help

help:  ## Show this help message
	@echo "GTEx-Link Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick start: make dev-setup && make server"

install:  ## Install dependencies using uv
	export UV_LINK_MODE=copy UV_CACHE_DIR=/tmp/uv-cache && uv sync --group dev

lint:  ## Run ruff linting only
	uv run ruff check .

format:  ## Run ruff formatting
	uv run ruff format .

typecheck:  ## Run mypy type checking
	uv run mypy gtex_link/

fix:  ## Auto-fix linting and formatting issues
	uv run ruff check --fix .
	uv run ruff format .

test:  ## Run tests
	uv run pytest

test-cov:  ## Run tests with coverage report
	uv run pytest --cov=gtex_link --cov-report=html --cov-report=term-missing

check-all: lint typecheck test  ## Run all quality checks

dev-setup: install  ## Complete development environment setup
	uv run pre-commit install

server:  ## Start development HTTP server
	uv run python server.py

mcp:  ## Start MCP server (STDIO transport)
	uv run python mcp_server.py

mcp-http:  ## Start MCP server with HTTP transport
	uv run python mcp_http_server.py

unified-server:  ## Start unified server (FastAPI + MCP info)
	uv run python unified_server.py

clean:  ## Clean cache and temporary files
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

info:  ## Show project information
	@echo "Project: GTEx-Link"
	@echo "uv: $(shell uv --version)"

# Docker operations
docker-build:  ## Build Docker image
	docker compose -f docker/docker-compose.yml build

docker-dev:  ## Start development environment with Docker Compose (foreground)
	docker compose -f docker/docker-compose.dev.yml down 2>/dev/null || true
	docker compose -f docker/docker-compose.dev.yml up --build

docker-dev-bg:  ## Start development environment with Docker Compose (background)
	docker compose -f docker/docker-compose.dev.yml down 2>/dev/null || true
	docker compose -f docker/docker-compose.dev.yml up --build -d

docker-prod:  ## Start production environment with Docker Compose
	docker compose -f docker/docker-compose.yml up -d

docker-mcp:  ## Start MCP services with Docker Compose
	docker compose -f docker/docker-compose.mcp.yml up -d --build

docker-stop:  ## Stop all Docker services
	docker compose -f docker/docker-compose.yml down
	docker compose -f docker/docker-compose.dev.yml down
	docker compose -f docker/docker-compose.mcp.yml down

docker-logs:  ## Show Docker logs (production)
	docker compose -f docker/docker-compose.yml logs -f

docker-logs-dev:  ## Show Docker logs (development)
	docker compose -f docker/docker-compose.dev.yml logs -f

docker-clean:  ## Clean Docker resources
	docker compose -f docker/docker-compose.yml down -v --rmi all
	docker compose -f docker/docker-compose.dev.yml down -v --rmi all
	docker compose -f docker/docker-compose.mcp.yml down -v --rmi all
