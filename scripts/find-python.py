#!/usr/bin/env python3
"""Find Python 3.10+ interpreter on the system."""
import subprocess
import sys

# List of Python interpreters to try (in order of preference)
CANDIDATES = [
    'python3.13',
    'python3.12',
    'python3.11', 
    'python3.10',
    'python3',
]

def get_python_version(python_cmd):
    """Get Python version as tuple of (major, minor)."""
    try:
        result = subprocess.run(
            [python_cmd, '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            major, minor = result.stdout.strip().split('.')
            return (int(major), int(minor))
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return None

def find_python():
    """Find first available Python 3.10+ interpreter."""
    for candidate in CANDIDATES:
        version = get_python_version(candidate)
        if version and version >= (3, 10):
            return candidate
    return None

if __name__ == '__main__':
    python = find_python()
    if python:
        print(python)
        sys.exit(0)
    else:
        print("ERROR: Python 3.10+ not found. Please install Python 3.10 or newer.", file=sys.stderr)
        sys.exit(1)