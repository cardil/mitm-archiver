"""
Configuration module for mitm-archiver.

Loads settings from environment variables with sensible defaults.
Environment variables can be set in .env file or system environment.
"""

import os
from pathlib import Path

# Load .env if present (optional)
try:
    from dotenv import load_dotenv
    env_file = os.getenv("ENV_FILE", ".env")
    if Path(env_file).exists():
        load_dotenv(env_file)
except (ImportError, FileNotFoundError):
    pass  # No .env file or dotenv not installed - use defaults


# Cache directory - where archived files are stored
# Default: ./data (relative to current directory)
CACHE_DIR = Path(os.getenv("CACHE_DIR", "./data")).resolve()
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Port to listen on for proxy connections
# Default: 8080
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "8080"))

# Certificates directory - where mitmproxy stores SSL certificates
# Default: ./certs (relative to current directory)
CERTS_DIR = Path(os.getenv("CERTS_DIR", "./certs")).resolve()
CERTS_DIR.mkdir(parents=True, exist_ok=True)

# Proxy authentication in format "username:password"
# Default: "" (no authentication)
PROXY_AUTH = os.getenv("PROXY_AUTH", "")