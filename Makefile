.PHONY: help setup dev run e2e clean clean-all format lint config-show quadlet start

# Find Python 3.10+ using helper script
# This handles systems like RHEL9 where python3 is 3.9 but python3.11 exists
# Will fail with clear error if Python 3.10+ is not found
PYTHON := $(shell python3 scripts/find-python.py)
VENV := .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip

# Guard files to track build steps
VENV_GUARD := $(VENV)/.venv_created
INSTALL_GUARD := $(VENV)/.installed
DEV_GUARD := $(VENV)/.dev_installed

# Environment file
ENV_FILE ?= .env

# Color output
BOLD := \033[1m
RESET := \033[0m
GREEN := \033[32m
YELLOW := \033[33m

help: ## Show this help message
	@printf '$(BOLD)Available targets:$(RESET)\n'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'

# Create virtual environment
$(VENV_GUARD): Makefile
	@printf "$(YELLOW)🔧 Creating Python virtual environment...$(RESET)\n"
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	@touch $@
	@printf "$(GREEN)✅ Virtual environment created$(RESET)\n"

# Install production dependencies
$(INSTALL_GUARD): $(VENV_GUARD) pyproject.toml
	@printf "$(YELLOW)📦 Installing production dependencies...$(RESET)\n"
	$(PIP) install -e .
	@touch $@
	@printf "$(GREEN)✅ Production dependencies installed$(RESET)\n"

# Install development dependencies
$(DEV_GUARD): $(INSTALL_GUARD) pyproject.toml
	@printf "$(YELLOW)📦 Installing dev dependencies...$(RESET)\n"
	$(PIP) install -e ".[dev]"
	@touch $@
	@printf "$(GREEN)✅ Dev dependencies installed$(RESET)\n"

setup: $(INSTALL_GUARD) ## Set up production environment (venv + production deps)
	@printf "$(GREEN)✅ Production environment ready!$(RESET)\n"
	@printf "\nTo activate manually: source $(VENV_BIN)/activate\n"
	@printf "To run the proxy: make run\n"

dev: $(DEV_GUARD) ## Set up development environment (venv + all deps)
	@printf "$(GREEN)✅ Development environment ready!$(RESET)\n"
	@printf "\nTo activate manually: source $(VENV_BIN)/activate\n"
	@printf "To run E2E tests: make e2e\n"
	@printf "To run linter: make lint\n"

config-show: $(VENV_GUARD) ## Show current configuration
	@printf "$(YELLOW)⚙️  Current configuration:$(RESET)\n"
	@if [ ! -f "$(ENV_FILE)" ]; then \
		printf "$(YELLOW)⚠️  No $(ENV_FILE) found, using defaults$(RESET)\n"; \
	fi
	@ENV_FILE=$(ENV_FILE) $(VENV_BIN)/python scripts/show-config.py

run: $(INSTALL_GUARD) ## Run mitm-archiver in development mode
	@printf "$(YELLOW)🚀 Starting mitm-archiver...$(RESET)\n"
	@$(MAKE) config-show
	@printf "\n"
	@ENV_FILE=$(ENV_FILE) $(VENV_BIN)/python bin/mitm-archiver

e2e: $(DEV_GUARD) ## Run E2E tests with pytest (starts proxy automatically)
	@printf "$(YELLOW)🧪 Running E2E tests...$(RESET)\n"
	@ENV_FILE=$(ENV_FILE) $(VENV_BIN)/pytest e2e/ -v

clean: ## Clean up cache and temporary files
	@printf "$(YELLOW)🧹 Cleaning up...$(RESET)\n"
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf *.egg-info/
	rm -rf data/
	rm -rf certs/
	rm -rf test-data/
	rm -rf test-certs/
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	@printf "$(GREEN)✅ Cleaned up$(RESET)\n"

clean-all: clean ## Clean everything including venv
	@printf "$(YELLOW)🧹 Cleaning everything including venv...$(RESET)\n"
	rm -rf $(VENV)
	@printf "$(GREEN)✅ Everything cleaned$(RESET)\n"

format: $(DEV_GUARD) ## Format code with black
	@printf "$(YELLOW)🎨 Formatting code...$(RESET)\n"
	$(VENV_BIN)/black archiver.py config.py
	@printf "$(GREEN)✅ Code formatted$(RESET)\n"

lint: $(DEV_GUARD) ## Lint code with ruff
	@printf "$(YELLOW)🔍 Linting code...$(RESET)\n"
	$(VENV_BIN)/ruff check archiver.py config.py
	@printf "$(GREEN)✅ Linting complete$(RESET)\n"

quadlet: $(INSTALL_GUARD) ## Generate Quadlet systemd container file
	@printf "$(YELLOW)📦 Generating Quadlet file...$(RESET)\n"
	@ENV_FILE=$(ENV_FILE) $(VENV_BIN)/python scripts/generate-quadlet.py
	@printf "$(GREEN)✅ Quadlet file generated: mitm-archiver.container$(RESET)\n"

# Convenience alias
start: run ## Alias for run

# Show help by default
.DEFAULT_GOAL := help