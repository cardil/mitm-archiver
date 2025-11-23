#!/usr/bin/env python3
"""Show current mitm-archiver configuration."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

from config import CACHE_DIR, CERTS_DIR, LISTEN_PORT, PROXY_AUTH

config = {
    'cache_dir': str(CACHE_DIR),
    'listen_port': LISTEN_PORT,
    'certs_dir': str(CERTS_DIR),
    'proxy_auth': '***SET***' if PROXY_AUTH else '***NOT SET***'
}

print(json.dumps(config, indent=2))
