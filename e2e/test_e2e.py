"""End-to-end tests for mitm-archiver."""
import hashlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from config import CACHE_DIR, CERTS_DIR


def find_free_port():
    """Find a free port to use for the proxy."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="session")
def proxy_port():
    """Get or find proxy port."""
    # Check if using external proxy with predefined port
    use_external = os.getenv("USE_EXTERNAL_PROXY", "").lower() in ("1", "true", "yes")
    if use_external:
        # Use port from environment or default
        return int(os.getenv("LISTEN_PORT", "8080"))
    
    # Find free port for internal proxy
    return find_free_port()


@pytest.fixture(scope="session")
def proxy_server(proxy_port):
    """
    Start proxy server for tests.
    
    If USE_EXTERNAL_PROXY env var is set, assumes proxy is already running
    (for testing Docker/Quadlet deployments).
    Otherwise, starts the proxy in background for the test session.
    """
    use_external = os.getenv("USE_EXTERNAL_PROXY", "").lower() in ("1", "true", "yes")
    
    if use_external:
        print(f"\n🔗 Using external proxy server on port {proxy_port}")
        # Just verify it's reachable
        max_wait = 30
        for i in range(max_wait):
            try:
                requests.get(
                    "http://httpbin.org/status/200",
                    proxies={"http": f"http://localhost:{proxy_port}"},
                    timeout=1,
                )
                print("✅ External proxy is reachable")
                yield None
                return
            except Exception:
                if i < max_wait - 1:
                    time.sleep(1)
        raise RuntimeError(
            f"External proxy not reachable on port {proxy_port} after {max_wait}s"
        )
    
    # Start proxy in background
    print(f"\n🚀 Starting proxy server on port {proxy_port}...")
    
    # Ensure directories exist
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Start the proxy with dynamic port
    python_exe = sys.executable
    archiver_script = Path(__file__).parent.parent / "bin" / "mitm-archiver"
    
    env = os.environ.copy()
    env["LISTEN_PORT"] = str(proxy_port)
    
    process = subprocess.Popen(
        [python_exe, str(archiver_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    
    # Wait for proxy to be ready
    max_wait = 30
    for i in range(max_wait):
        try:
            requests.get(
                "http://httpbin.org/status/200",
                proxies={"http": f"http://localhost:{proxy_port}"},
                timeout=1,
            )
            print(f"✅ Proxy started successfully on port {proxy_port}")
            break
        except Exception:
            if i < max_wait - 1:
                time.sleep(1)
            else:
                process.kill()
                stdout, stderr = process.communicate()
                raise RuntimeError(
                    f"Proxy failed to start after {max_wait}s\nStdout: {stdout}\nStderr: {stderr}"
                ) from None
    
    yield process
    
    # Cleanup
    print("\n🛑 Stopping proxy server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    print("✅ Proxy stopped")


@pytest.fixture
def proxy_config(proxy_server, proxy_port):
    """Get proxy configuration."""
    proxy_url = f"http://localhost:{proxy_port}"
    ca_cert_path = CERTS_DIR / "mitmproxy-ca-cert.pem"
    ca_cert = str(ca_cert_path) if ca_cert_path.exists() else False

    return {
        "proxies": {
            "http": proxy_url,
            "https": proxy_url,
        },
        "verify": ca_cert,
    }


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hash of data."""
    return hashlib.sha256(data).hexdigest()


def find_cache_file(url: str) -> Path:
    """Find cache file for given URL."""
    # Clean URL to match archiver.py's get_safe_path logic
    clean_path = url.replace("https://", "").replace("http://", "").split("?")[0]
    return CACHE_DIR / clean_path


def test_cache_miss_downloads_and_stores(proxy_config):
    """Test that first request downloads and caches the file."""
    test_url = "https://httpbin.org/bytes/10240"

    # Make first request (cache miss)
    start = time.time()
    response = requests.get(test_url, timeout=30, **proxy_config)
    miss_duration = time.time() - start

    # Verify response
    assert response.status_code == 200
    assert len(response.content) == 10240
    print(f"✅ Cache miss completed in {miss_duration:.2f}s")

    # Compute hash of downloaded content
    content_hash = compute_sha256(response.content)
    print(f"📝 Content hash: {content_hash}")

    # Find and verify cache file
    cache_file = find_cache_file(test_url)
    assert cache_file.exists(), f"Cache file not created: {cache_file}"

    # Verify cache file hash matches downloaded content
    with cache_file.open("rb") as f:
        cache_hash = compute_sha256(f.read())

    assert (
        cache_hash == content_hash
    ), f"Cache hash mismatch: {cache_hash} != {content_hash}"
    print(f"✅ Cache file verified: {cache_file}")


def test_cache_hit_is_fast_and_identical(proxy_config):
    """Test that second request uses cache and returns identical content."""
    test_url = "https://httpbin.org/bytes/10240"

    # First request to populate cache
    response1 = requests.get(test_url, timeout=30, **proxy_config)
    hash1 = compute_sha256(response1.content)

    # Give proxy a moment to finish writing
    time.sleep(0.1)

    # Second request (cache hit)
    start = time.time()
    response2 = requests.get(test_url, timeout=30, **proxy_config)
    hit_duration = time.time() - start

    # Verify response
    assert response2.status_code == 200
    assert len(response2.content) == 10240
    print(f"✅ Cache hit completed in {hit_duration:.2f}s")

    # Verify content is identical
    hash2 = compute_sha256(response2.content)
    assert hash1 == hash2, f"Content mismatch: {hash1} != {hash2}"
    print(f"✅ Content hash verified: {hash2}")

    # Verify cache hit was fast (< 100ms)
    assert hit_duration < 0.1, f"Cache hit too slow: {hit_duration:.3f}s"
    print(f"⚡ Cache hit was very fast: {hit_duration*1000:.1f}ms")


def test_cache_file_integrity(proxy_config):
    """Test that cached file exactly matches downloaded content."""
    test_url = "https://httpbin.org/bytes/5000"

    # Download and cache
    response = requests.get(test_url, timeout=30, **proxy_config)
    download_hash = compute_sha256(response.content)

    # Wait for file to be fully written
    time.sleep(0.1)

    # Read cache file
    cache_file = find_cache_file(test_url)
    assert cache_file.exists(), "Cache file not found"

    with cache_file.open("rb") as f:
        cache_data = f.read()
        cache_hash = compute_sha256(cache_data)

    # Verify integrity
    assert cache_hash == download_hash, "Cache file corrupted"
    assert len(cache_data) == len(response.content), "Cache file size mismatch"
    assert cache_data == response.content, "Cache file content differs"

    print(f"✅ Cache integrity verified: {cache_hash}")
    print(f"📁 Cache file size: {len(cache_data)} bytes")


def test_multiple_files_cached(proxy_config):
    """Test that multiple different URLs are all cached correctly."""
    test_urls = [
        "https://httpbin.org/bytes/1024",
        "https://httpbin.org/bytes/2048",
        "https://httpbin.org/bytes/4096",
    ]

    hashes = {}

    # Download all URLs
    for url in test_urls:
        response = requests.get(url, timeout=30, **proxy_config)
        assert response.status_code == 200
        hashes[url] = compute_sha256(response.content)

    # Wait for all files to be written
    time.sleep(0.2)

    # Verify all cache files exist and match
    for url, expected_hash in hashes.items():
        cache_file = find_cache_file(url)
        assert cache_file.exists(), f"Cache file not found for {url}"

        with cache_file.open("rb") as f:
            cache_hash = compute_sha256(f.read())

        assert cache_hash == expected_hash, f"Hash mismatch for {url}"

    print(f"✅ All {len(test_urls)} files cached correctly")