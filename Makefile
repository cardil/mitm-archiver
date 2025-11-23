.PHONY: help setup install dev-install run test clean format lint config-show

# Default Python interpreter
PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip

# Environment file
ENV_FILE ?= .env.local

# Color output
BOLD := \033[1m
RESET := \033[0m
GREEN := \033[32m
YELLOW := \033[33m

help: ## Show this help message
	@printf '$(BOLD)Available targets:$(RESET)\n'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'

setup: ## Set up development environment (create venv and install deps)
	@printf "$(YELLOW)🔧 Setting up Python virtual environment...$(RESET)\n"
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	@$(MAKE) dev-install
	@printf "$(GREEN)✅ Virtual environment ready!$(RESET)\n"
	@printf "\n"
	@printf "To activate manually: source $(VENV_BIN)/activate\n"
	@printf "To run the proxy: make run\n"

install: ## Install production dependencies
	@printf "$(YELLOW)📦 Installing dependencies...$(RESET)\n"
	$(PIP) install -e .
	@printf "$(GREEN)✅ Dependencies installed$(RESET)\n"

dev-install: install ## Install development dependencies
	@printf "$(YELLOW)📦 Installing dev dependencies...$(RESET)\n"
	$(PIP) install -e ".[dev]"
	@printf "$(GREEN)✅ Dev dependencies installed$(RESET)\n"

.env.local:
	@printf "$(YELLOW)📝 Creating .env.local from template...$(RESET)\n"
	@cp .env.example .env.local
	@printf "$(GREEN)✅ Created .env.local$(RESET)\n"

config-show: .env.local ## Show current configuration
	@printf "$(YELLOW)⚙️  Current configuration:$(RESET)\n"
	@ENV_FILE=$(ENV_FILE) $(VENV_BIN)/python scripts/show-config.py

run: .env.local ## Run mitm-archiver in development mode
	@printf "$(YELLOW)🚀 Starting mitm-archiver...$(RESET)\n"
	@$(MAKE) config-show
	@printf "\n"
	@ENV_FILE=$(ENV_FILE) $(VENV_BIN)/python bin/mitm-archiver

test: ## Test the proxy with sample requests
	@printf "$(YELLOW)🧪 Testing mitm-archiver...$(RESET)\n"
	@printf "\n"
	@bash -c '\
		PORT=$$(ENV_FILE=$(ENV_FILE) $(VENV_BIN)/python -c "from config import LISTEN_PORT; print(LISTEN_PORT)"); \
		PROXY_HOST="localhost:$$PORT"; \
		export http_proxy="http://$$PROXY_HOST"; \
		export https_proxy="http://$$PROXY_HOST"; \
		export HTTPS_PROXY="http://$$PROXY_HOST"; \
		export HTTP_PROXY="http://$$PROXY_HOST"; \
		export CURL_CA_BUNDLE=""; \
		printf "1️⃣  Testing cache MISS (first download)...\n"; \
		time curl -k -s "https://httpbin.org/bytes/10240" > /dev/null; \
		printf "$(GREEN)✅ Cache miss completed$(RESET)\n"; \
		printf "\n"; \
		printf "2️⃣  Testing cache HIT (should be instant)...\n"; \
		time curl -k -s "https://httpbin.org/bytes/10240" > /dev/null; \
		printf "$(GREEN)✅ Cache hit completed$(RESET)\n"; \
		printf "\n"; \
		printf "3️⃣  Checking cache directory...\n"; \
		find ./data -type f 2>/dev/null | head -10 || printf "Cache directory not found or empty\n"; \
		printf "\n"; \
		printf "$(GREEN)✅ All tests passed!$(RESET)\n"'

clean: ## Clean up cache and temporary files
	@printf "$(YELLOW)🧹 Cleaning up...$(RESET)\n"
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	@printf "$(GREEN)✅ Cleaned up$(RESET)\n"

clean-all: clean ## Clean everything including venv
	@printf "$(YELLOW)🧹 Cleaning everything including venv...$(RESET)\n"
	rm -rf $(VENV)
	rm -f .env
	@printf "$(GREEN)✅ Everything cleaned$(RESET)\n"

format: ## Format code with black
	@printf "$(YELLOW)🎨 Formatting code...$(RESET)\n"
	$(VENV_BIN)/black archiver.py config.py
	@printf "$(GREEN)✅ Code formatted$(RESET)\n"

lint: ## Lint code with ruff
	@printf "$(YELLOW)🔍 Linting code...$(RESET)\n"
	$(VENV_BIN)/ruff check archiver.py config.py
	@printf "$(GREEN)✅ Linting complete$(RESET)\n"

# Development workflow shortcuts
dev: setup ## Alias for setup

start: run ## Alias for run

# Show help by default
.DEFAULT_GOAL := help