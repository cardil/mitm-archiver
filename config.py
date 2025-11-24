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
    # Resolve symlinks and check if file exists
    env_path = Path(env_file)
    if env_path.is_symlink():
        env_path = env_path.resolve()

    if env_path.exists():
        # Load .env file, but let system environment variables take precedence
        # This allows overriding .env values via system env vars
        load_dotenv(str(env_path), override=False)
except (ImportError, FileNotFoundError):
    pass  # No .env file or dotenv not installed - use defaults


# Cache directory - where archived files are stored
# Default: ./data (relative to current directory)
CACHE_DIR = Path(os.getenv("CACHE_DIR", "./data")).resolve()

# Port to listen on for proxy connections
# Default: 8080
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "8080"))

# Certificates directory - where mitmproxy stores SSL certificates
# Default: ./certs (relative to current directory)
CERTS_DIR = Path(os.getenv("CERTS_DIR", "./certs")).resolve()

# Proxy authentication in format "username:password"
# Default: "" (no authentication)
PROXY_AUTH = os.getenv("PROXY_AUTH", "")


def ensure_directories():
    """
    Ensure cache and certificates directories exist.

    This should be called when the proxy starts, not when config is imported.
    This allows config to be imported for inspection (e.g., show-config.py)
    without requiring write permissions.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
