from pathlib import Path

from mitmproxy import ctx, http

from config import CACHE_DIR

# Chunk size for streaming responses (in bytes)
CHUNK_SIZE = 8192

# Connection optimization: Track known TLS hosts to enable connection reuse
# Mitmproxy will keep these connections alive instead of reconnecting each time
_seen_hosts = set()


def get_safe_path(url_path: str) -> Path:
    """
    Convert URL to safe filesystem path within CACHE_DIR.

    Args:
        url_path: URL to convert to filesystem path

    Returns:
        Path object pointing to the cache file location

    Raises:
        ValueError: If the resulting path is outside CACHE_DIR
    """
    clean_path = url_path.replace("https://", "").replace("http://", "").split("?")[0]
    final_path = CACHE_DIR / clean_path
    real_path = final_path.resolve()

    # Security check: ensure the path is within CACHE_DIR
    try:
        real_path.relative_to(CACHE_DIR.resolve())
    except ValueError:
        raise ValueError(f"Invalid path: {url_path}") from None

    return real_path


def tls_clienthello(data):
    """
    Called on TLS Client Hello. Track hosts we've seen to enable connection reuse.
    Mitmproxy can reuse TLS connections to known hosts, avoiding repeated handshakes.
    """
    try:
        # Try to get the SNI (Server Name Indication) from the client hello
        if (
            hasattr(data, "client_hello")
            and data.client_hello
            and hasattr(data.client_hello, "sni")
        ):
            host = data.client_hello.sni
        elif hasattr(data, "context") and data.context.server:
            host = data.context.server.address[0]
        else:
            host = "unknown"

        if host and host != "unknown" and host not in _seen_hosts:
            _seen_hosts.add(host)
            ctx.log.info(f"🔐 New TLS host: {host} (will cache connection)")
    except Exception as e:
        ctx.log.warn(f"Could not track TLS host: {e}")


def server_connect(data) -> None:
    """
    Called when mitmproxy is about to connect to upstream server.
    Note: For HTTPS, this MUST happen even for cache hits (to get TLS cert).
    However, with connection_strategy=lazy, the connection will be reused.
    """
    # The data object has a 'server' attribute with the connection details
    try:
        server = data.server
        if server and hasattr(server, "address") and server.address:
            host = server.address[0]
            port = server.address[1]
            is_known = host in _seen_hosts
            status = "reusing" if is_known else "new"
            ctx.log.info(f"🔌 Server connect: {host}:{port} ({status})")
    except Exception as e:
        ctx.log.warn(f"Could not log server connection: {e}")


def request(flow: http.HTTPFlow) -> None:
    """
    CACHE HIT: Serve from disk.

    This happens AFTER the TLS CONNECT but BEFORE the GET is sent to upstream.
    By setting flow.response here, we prevent the actual GET request from being
    sent to the upstream server.

    Note: The TLS CONNECT still happens (needed for cert inspection), but:
    - The connection is reused (not closed after each request)
    - No actual HTTP GET is sent upstream (saves bandwidth)
    - No suspicious "connect and immediately disconnect" pattern
    """
    if flow.request.method != "GET":
        return

    try:
        local_path = get_safe_path(flow.request.pretty_url)
    except ValueError:
        return

    if local_path.exists():
        ctx.log.info(f"⚡ CACHE HIT: Serving {local_path} (no upstream GET)")
        try:
            # Mark that we served from cache (upstream connection will be kept alive)
            flow.metadata["cache_hit"] = True

            # Load entire file into memory (TODO: streaming implementation)
            with local_path.open("rb") as f:
                flow.response = http.Response.make(
                    200, f.read(), {"Content-Type": "application/octet-stream"}
                )
        except Exception as e:
            ctx.log.error(f"Read error: {e}")
            flow.metadata["cache_hit"] = False
    else:
        # Cache miss - the GET will be sent upstream
        # Track the host for connection reuse
        try:
            host = flow.request.host
            if host and host not in _seen_hosts:
                _seen_hosts.add(host)
        except (AttributeError, TypeError) as e:
            ctx.log.debug(f"Could not track request host for cache miss: {e}")
        ctx.log.info(
            f"💾 CACHE MISS: Will fetch from upstream: {flow.request.pretty_url}"
        )
        flow.metadata["cache_hit"] = False


def response(flow: http.HTTPFlow):
    """
    Called after the full response has been read.

    For cache misses with successful responses, save the content to disk.
    This is a simpler approach than streaming - we write the full response
    body after it's been received.
    """
    # Skip non-GET requests or failed responses
    if flow.request.method != "GET" or flow.response.status_code != 200:
        return

    # Skip if this was a cache hit (already served from disk in request hook)
    if flow.metadata.get("cache_hit"):
        return

    try:
        local_path = get_safe_path(flow.request.pretty_url)
    except ValueError:
        return

    # Only save if we don't have it yet
    if not local_path.exists():
        ctx.log.info(f"💾 Saving response to {local_path}")

        tmp_path = local_path.with_suffix(local_path.suffix + ".tmp")
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Write the full response content to a temporary file
            with tmp_path.open("wb") as f:
                f.write(flow.response.content)

            # Rename temporary file to final location
            if tmp_path.stat().st_size > 0:
                tmp_path.rename(local_path)
                ctx.log.info(
                    f"✅ SAVED: {local_path} ({len(flow.response.content)} bytes)"
                )
            else:
                tmp_path.unlink()
                ctx.log.warn(f"Empty response, not saved: {flow.request.pretty_url}")
        except Exception as e:
            ctx.log.error(f"Failed to save response: {e}")
            # Clean up temporary file on error
            if tmp_path.exists():
                tmp_path.unlink()
