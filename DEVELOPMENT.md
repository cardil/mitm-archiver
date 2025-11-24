# Developer Guide

Quick guide for local development and testing.

## Prerequisites

- Python 3.9+
- curl (for testing)

## Quick Start

```bash
# 1. Setup
make setup

# 2. Run proxy (uses defaults: port 8080, ./data cache, no auth)
make run

# 3. Run E2E tests (starts its own proxy automatically)
make e2e
```

## Development Workflow

### Common Commands

```bash
make help        # Show all available commands
make run         # Start proxy (localhost:8080)
make e2e         # Run automated E2E tests
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
4. Run `make e2e` to verify

### Configuration

**No configuration needed** - runs with sensible defaults.

**Defaults:**
- Cache: `./data`
- Port: `8080`
- Certificates: `./certs`
- Auth: None

**To customize**, create `.env` from `.env.example`:

```bash
cp .env.example .env
vi .env
```

Example custom settings:
```bash
CACHE_DIR=./my-cache
LISTEN_PORT=9090
CERTS_DIR=./my-certs
PROXY_AUTH=user:pass
```

Or use a different env file:
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
make e2e  # Automatically starts proxy, runs tests, stops proxy
```

**Note:** E2E tests start their own proxy server automatically - you don't need to run `make run` first.

### Manual Testing (For Interactive Testing)
```bash
# 1. Start proxy manually (in one terminal)
make run

# 2. In another terminal, set proxy and test
export http_proxy=http://localhost:8080
export https_proxy=http://localhost:8080

# 3. Test
curl -k https://httpbin.org/get

# 4. Check cache
ls -la ./data/
```

### Testing Docker Compose Locally
```bash
# Run with defaults (no .env needed)
docker compose up

# Or customize with .env
cp .env.example .env
vi .env  # Edit settings
docker compose up

# Test (in another terminal)
curl -x localhost:8080 -k https://httpbin.org/get

# Stop
docker compose down
```

### Testing Quadlet Template
```bash
# Quadlet generation requires .env
cp .env.example .env
vi .env  # Edit settings

# Generate Quadlet file
make quadlet
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