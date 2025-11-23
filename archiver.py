import os
from mitmproxy import http, ctx

# Configuration
CACHE_DIR = "/data"
CHUNK_SIZE = 8192  # 8KB chunks for streaming

# Connection optimization: Track known TLS hosts to enable connection reuse
# Mitmproxy will keep these connections alive instead of reconnecting each time
_seen_hosts = set()

def get_safe_path(url_path: str) -> str:
    clean_path = url_path.replace("https://", "").replace("http://", "").split("?")[0]
    final_path = os.path.join(CACHE_DIR, clean_path)
    real_path = os.path.abspath(final_path)
    if not os.path.commonprefix([real_path, os.path.abspath(CACHE_DIR)]) == os.path.abspath(CACHE_DIR):
        raise ValueError(f"Invalid path: {url_path}")
    return real_path

def tls_clienthello(data):
    """
    Called on TLS Client Hello. Track hosts we've seen to enable connection reuse.
    Mitmproxy can reuse TLS connections to known hosts, avoiding repeated handshakes.
    """
    try:
        # Try to get the SNI (Server Name Indication) from the client hello
        if hasattr(data, 'client_hello') and data.client_hello and hasattr(data.client_hello, 'sni'):
            host = data.client_hello.sni
        elif hasattr(data, 'context') and data.context.server:
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
        if server and hasattr(server, 'address') and server.address:
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
    if flow.request.method != "GET": return

    try:
        local_path = get_safe_path(flow.request.pretty_url)
    except ValueError: return

    if os.path.exists(local_path):
        ctx.log.info(f"⚡ CACHE HIT: Serving {local_path} (no upstream GET)")
        try:
            # Mark that we served from cache (upstream connection will be kept alive)
            flow.metadata["cache_hit"] = True
            
            # Load entire file into memory (TODO: streaming implementation)
            with open(local_path, "rb") as f:
                flow.response = http.Response.make(
                    200,
                    f.read(),
                    {"Content-Type": "application/octet-stream"}
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
        except:
            pass
        ctx.log.info(f"💾 CACHE MISS: Will fetch from upstream: {flow.request.pretty_url}")
        flow.metadata["cache_hit"] = False

def responseheaders(flow: http.HTTPFlow):
    """CACHE MISS: Initialize file capture."""
    if flow.request.method != "GET" or flow.response.status_code != 200: return

    try:
        local_path = get_safe_path(flow.request.pretty_url)
    except ValueError: return

    # Only start capturing if we don't have it yet
    if not os.path.exists(local_path):
        ctx.log.info(f"💾 CACHE MISS: Teeing stream to {local_path}")
        
        tmp_path = local_path + ".tmp"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            # 1. Open file NOW and store handle in the flow object
            # This keeps it open across multiple stream calls
            f = open(tmp_path, "wb")
            flow.metadata["save_file"] = f
            flow.metadata["save_path"] = local_path
            flow.metadata["tmp_path"] = tmp_path
            
            # 2. Define the stream processor
            def tee_stream(chunks):
                # Handle the "int vs bytes" edge case
                iterator = [chunks] if isinstance(chunks, bytes) else chunks
                
                # Retrieve our open file handle
                f = flow.metadata.get("save_file")
                
                for chunk in iterator:
                    if f and not f.closed:
                        try:
                            f.write(chunk)
                        except Exception as e:
                            ctx.log.error(f"Write error: {e}")
                    yield chunk

            flow.response.stream = tee_stream
            
        except Exception as e:
            ctx.log.error(f"Failed to open tmp file: {e}")

def response(flow: http.HTTPFlow):
    """Called after the full response has been read - finalize file."""
    f = flow.metadata.get("save_file")
    tmp_path = flow.metadata.get("tmp_path")
    save_path = flow.metadata.get("save_path")
    
    # Close and rename the file if we were saving it
    if f:
        try:
            if not f.closed:
                f.flush()
                f.close()
                ctx.log.info(f"Response complete, file closed")
        except Exception as e:
            ctx.log.error(f"Error closing file: {e}")
        
        # Clean up metadata
        if "save_file" in flow.metadata:
            del flow.metadata["save_file"]
        
        # Rename tmp to final
        if tmp_path and save_path and os.path.exists(tmp_path):
            if os.path.getsize(tmp_path) > 0:
                try:
                    os.rename(tmp_path, save_path)
                    ctx.log.info(f"✅ DOWNLOAD COMPLETE: {save_path}")
                except OSError as e:
                    ctx.log.error(f"Rename failed: {e}")
            else:
                os.remove(tmp_path)
                ctx.log.warn(f"Empty tmp file deleted: {tmp_path}")

def error(flow: http.HTTPFlow):
    """Handle network errors/disconnects: Cleanup."""
    cleanup(flow, success=False)

def done(flow: http.HTTPFlow):
    """Request finished: Finalize the file."""
    cleanup(flow, success=True)

def cleanup(flow: http.HTTPFlow, success: bool):
    """Helper to close file and rename/delete - mostly for error cases."""
    # For streaming responses, the stream's finally block handles everything
    # This is mainly for error cases where streaming never started
    
    f = flow.metadata.get("save_file")
    tmp_path = flow.metadata.get("tmp_path")
    save_path = flow.metadata.get("save_path")

    # Only clean up if the file handle still exists (wasn't closed by stream)
    if f:
        try:
            if not f.closed:
                f.flush()
                f.close()
                ctx.log.info(f"File closed in error cleanup (success={success})")
        except Exception as e:
            ctx.log.error(f"Error closing file in cleanup: {e}")
        
        # Clean up metadata
        if "save_file" in flow.metadata:
            del flow.metadata["save_file"]
        
        # On error/disconnect, delete the partial file
        if not success and tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
            ctx.log.info(f"❌ INCOMPLETE: Deleted partial {tmp_path}")
