# Developer Guide

Quick guide for local development and testing.

## Prerequisites

- Python 3.10+
- curl (for testing)

## Quick Start

```bash
# 1. Setup
make setup

# 2. Run proxy
make run

# 3. Test (in another terminal)
make test
```

## Development Workflow

### Common Commands

```bash
make help        # Show all available commands
make run         # Start proxy (localhost:8080)
make test        # Run automated tests
make config-show # Display current configuration
make format      # Format code with black
make lint        # Lint code with ruff
make clean       # Clean cache and temp files
make clean-all   # Clean everything including venv
```

### Making Changes

1. Edit `archiver.py` or `config.py`
2. Stop proxy (Ctrl+C)
3. Run `make run` to restart
4. Run `make test` to verify

### Custom Configuration

Edit `.env` (create from `.env.example` if needed):

```bash
CACHE_DIR=./data
LISTEN_PORT=8080
CERTS_DIR=./certs
# PROXY_AUTH=  # Leave empty for no auth
```

Or use a custom env file:
```bash
ENV_FILE=.env.custom make run
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_DIR` | `./data` | Cached files location |
| `LISTEN_PORT` | `8080` | Proxy port |
| `CERTS_DIR` | `./certs` | SSL certificates |
| `PROXY_AUTH` | _(empty)_ | Optional auth (`user:pass`) |

## Project Structure

```text
mitm-archiver/
├── archiver.py              # Main mitmproxy script
├── config.py                # Configuration module
├── pyproject.toml           # Python project metadata
├── Makefile                 # Development commands
├── .env.example             # Config template
├── .env                     # Your config (gitignored)
├── docker-compose.yml       # Docker Compose deployment
├── scripts/
│   ├── mitm-archiver.container.template  # Quadlet template
│   └── generate-quadlet.py               # Quadlet generator
├── data/                    # Cache directory (gitignored)
└── certs/                   # Certificates (gitignored)
```

## Testing

### Automated Tests
```bash
make test
```

### Manual Testing
```bash
# Set proxy
export http_proxy=http://localhost:8080
export https_proxy=http://localhost:8080

# Test
curl -k https://httpbin.org/get

# Check cache
ls -la ./data/
```

### Testing Docker Compose Locally
```bash
# Create .env if not exists
cp .env.example .env

# Run
docker compose up

# Test (in another terminal)
curl -x localhost:8080 -k https://httpbin.org/get

# Stop
docker compose down
```

### Testing Quadlet Template
```bash
# Generate from local config
python3 scripts/generate-quadlet.py
cat mitm-archiver.container  # Review generated file
```

## Troubleshooting

**Certificate errors:**
Use `-k` flag: `curl -k -x localhost:8080 https://example.com`

**Port in use:**
Change port in `.env`: `LISTEN_PORT=8081`

**Virtual environment issues:**
```bash
make clean-all
make setup
```

**Import errors:**
```bash
source .venv/bin/activate
# or just use make commands
```

## Code Quality

```bash
# Format
make format

# Lint
make lint
```

Uses [black](https://github.com/psf/black) and [ruff](https://github.com/astral-sh/ruff).