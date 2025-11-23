#!/usr/bin/env python3
"""Generate Quadlet configuration from repository."""
import os
import sys
from pathlib import Path

# Auto-detect repo root (parent of scripts directory where this script lives)
repo_root = Path(__file__).parent.parent.resolve()

# Add repo root to path to import config module
sys.path.insert(0, str(repo_root))
import config

# User config from config.py (reuses same defaults and .env loading logic)
source_dir = str(repo_root)
cache_dir = str(config.CACHE_DIR)
certs_dir = str(config.CERTS_DIR)
listen_port = str(config.LISTEN_PORT)
proxy_auth = config.PROXY_AUTH

# Read template and substitute
template_path = Path(__file__).parent / 'mitm-archiver.container.template'
with open(template_path) as f:
    template = f.read()

output = template.format(
    SOURCE_DIR=source_dir,
    CACHE_DIR=cache_dir,
    CERTS_DIR=certs_dir,
    LISTEN_PORT=listen_port,
    PROXY_AUTH=proxy_auth
)

output_file = 'mitm-archiver.container'
with open(output_file, 'w') as f:
    f.write(output)

print(f"✅ Generated: {output_file}")
print(f"📁 Source directory: {source_dir}")
print(f"🔧 Cache directory: {cache_dir}")
print(f"📜 Certificates: {certs_dir}")
print(f"🔌 Listen port: {listen_port}")
print(f"🔐 Proxy auth: {'***set***' if proxy_auth else 'disabled'}")
print()
print("To install:")
print(f"  sudo cp {output_file} /etc/containers/systemd/")
print("  sudo systemctl daemon-reload")
print("  sudo systemctl enable mitm-archiver.service")
print("  sudo systemctl start mitm-archiver.service")