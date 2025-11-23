# Mitm Archiver

A mitm proxy that archives the downloads (download once).

## 1. Background & Problem Statement
Our CI/CD pipelines on GitHub Actions frequently depend on external assets (datasets, binaries, large artifacts) hosted by third-party vendors.

**Risks:**
* **Upstream Volatility:** Vendors may delete, move, or change these files without warning, breaking build pipelines.
* **Reliability:** Upstream servers may experience downtime or rate limiting.
* **Inefficiency:** Repeatedly downloading large files (GBs) for every workflow run is slow and bandwidth-intensive.

## 2. Purpose & Scope
The goal is to build a **Self-Hosted Intercepting Proxy** that acts as a permanent "Lazy Mirror" for these external assets.

Unlike a standard cache (which expires files) or a repository manager (which requires manual uploading), this tool must:
1.  **Archive Automatically:** Save a local copy of any file downloaded through it during a build.
2.  **Ensure Permanence:** Treat downloaded files as permanent archives, not temporary cache. If the upstream vendor deletes a file, our system must continue serving the local copy indefinitely.
3.  **Be Transparent:** Require zero code changes to the build logic (scripts using `curl`/`wget` should work as-is via standard Proxy environment variables).

---

## 3. Functional Requirements

### 3.1 Traffic Interception
* The system must accept standard HTTP and HTTPS proxy connections (via `HTTP_PROXY` / `HTTPS_PROXY`).
* The system must perform **SSL/TLS Interception (Man-in-the-Middle)** to inspect URL paths and cache content securely.
* The system must provide a generated **Certificate Authority (CA)** file to be trusted by the client (GitHub Runner).

### 3.2 "Tee-Streaming" (The Core Logic)
To handle multi-gigabyte downloads efficiently:
* **Cache Miss (First Request):** The system must stream the data from the Upstream Vendor to the Client immediately while **simultaneously** writing a copy to the local disk.
    * *Constraint:* Must not buffer the full file in RAM.
    * *Constraint:* Must handle client disconnects gracefully (delete partial files).
* **Cache Hit (Subsequent Requests):** The system must serve the file directly from the local disk, **without sending the GET request** to the upstream vendor.
    * *Constraint:* Must serve the file even if the upstream vendor is offline or returns a 404.
    * *Note:* For HTTPS URLs, a TLS CONNECT still occurs to obtain the upstream certificate (required for proper SSL/TLS interception), but the actual HTTP GET request is never sent upstream.

### 3.3 Connection Optimization
* **Connection Reuse:** The system must reuse upstream TLS connections instead of disconnecting after each request to avoid suspicious activity patterns.
    * *Implementation:* Uses `connection_strategy=lazy` to keep connections alive.
    * *Benefit:* Reduces CDN rate limiting risk and improves performance.
* **Smart Request Handling:** Cache hits are detected AFTER the TLS handshake but BEFORE the GET request is sent, minimizing bandwidth usage while maintaining proper SSL/TLS interception.

### 3.4 Storage & Persistence
* Files must be stored on the host filesystem using a directory structure mirroring the URL path (e.g., `/data/example.com/files/dataset.zip`).
* Storage must be persistent across container restarts and host reboots.

### 3.5 Security
* **Access Control:** The proxy must reject unauthenticated connections. It must enforce Basic Authentication (Username/Password).
* **Path Sanitization:** The system must strictly validate URL paths to prevent Directory Traversal attacks (prevent malicious URLs from writing to `/etc/` or other system paths).

---

---

## 4. Implementation Details

### 4.1 Request Flow
1. **Client CONNECT:** Client initiates HTTPS CONNECT request through proxy.
2. **TLS Handshake:** Proxy establishes TLS connection to upstream server (if not already connected).
3. **Certificate Inspection:** Proxy examines upstream certificate and generates matching fake certificate.
4. **Client Request:** Client sends HTTP GET request through established tunnel.
5. **Cache Check:** Proxy checks local disk cache:
   - **HIT:** Serve file from disk immediately, no upstream GET sent, connection kept alive for reuse.
   - **MISS:** Forward GET to upstream, stream response to client while simultaneously writing to disk.
6. **Connection Reuse:** Upstream connection remains open for subsequent requests to the same host.

### 4.2 File Streaming Architecture
* **Streaming Response:** Uses mitmproxy's streaming API to avoid buffering large files in memory.
* **Tee Implementation:** Custom stream processor writes chunks to disk while yielding them to the client.
* **Atomic Operations:** Downloads write to `.tmp` files and rename on completion to prevent serving partial files.
* **Error Handling:** Incomplete downloads are automatically deleted on client disconnect or network errors.

---

## 5. Environmental & System Requirements

### 5.1 Infrastructure
* **Host OS:** Red Hat Enterprise Linux 9 (RHEL 9).
* **Runtime:** Podman (Rootful or Rootless with Quadlets).
* **Service Management:** Integration with `systemd` for auto-start and log management.

### 5.2 Constraints
* **SELinux:** The solution must be compatible with RHEL SELinux enforcement (requires correct context labeling on storage volumes).
* **Network:** Inbound traffic on a specific non-standard port (e.g., 54321) must be allowed through the host firewall.
