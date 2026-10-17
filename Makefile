.DEFAULT_GOAL := help

.PHONY: help install lint format format-check typecheck test test-cov clean build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (dev extras)
	uv sync --locked --extra dev --extra langgraph --extra docs

lint: ## Run ruff linter
	uv run ruff check src tests scripts examples

format: ## Auto-format code
	uv run ruff format src tests scripts examples

format-check: ## Check formatting without changes
	uv run ruff format --check src tests scripts examples

typecheck: ## Run mypy type checking
	uv run mypy

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov --cov-report=term-missing

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info src/*.egg-info .mypy_cache .pytest_cache .ruff_cache

build: ## Build package distributions
	uv run python -m build

check: lint format-check typecheck test ## Run all quality gates

.PHONY: docs-check examples-check release-check

docs-check: ## Validate docs snippets/links and build strictly
	uv run --extra docs python scripts/check_docs.py
	uv run --extra docs mkdocs build --strict -f website/mkdocs.yml

examples-check: ## Run offline examples and intent benchmark
	@for example in examples/*.py; do uv run --extra langgraph python "$$example" || exit 1; done
	uv run python scripts/intent_benchmark.py

release-check: ## Validate release source versions and changelog
	uv run python scripts/validate_release.py
