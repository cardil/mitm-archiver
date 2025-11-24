# Mitm Archiver

A mitm proxy that archives downloads (download once) - acting as a permanent "Lazy Mirror" for external assets used in CI/CD pipelines.

**What it does:** Intercepts HTTP/HTTPS traffic and permanently caches downloaded files. When upstream vendors delete, move, or change files, the proxy continues serving cached copies indefinitely - ensuring build pipeline reliability.

## Quick Start

### Local Development
```bash
make setup  # Create venv and install dependencies
make run    # Start proxy on localhost:8080 (uses defaults, no .env needed)
make e2e    # Run end-to-end tests
```

**Configuration is optional** - runs with sensible defaults (`./data` cache, port 8080, no auth).
See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed developer documentation and customization.

### Production Deployment

Choose your deployment method:
- [Docker Compose](#docker-compose-deployment) - Portable, works anywhere
- [Systemd Quadlet](#quadlet-deployment-rhelfedora) - Native systemd integration for RHEL/Fedora

---

## Docker Compose Deployment

### Prerequisites
- Docker and Docker Compose installed
- Root or docker group access

### Quick Start (Using Defaults)

```bash
docker compose up -d
```

This runs with default settings:
- Cache: `./data`
- Port: `8080`
- Certificates: `./certs`
- Auth: None (no authentication)

### Production Installation

1. **Prepare directories:**
   ```bash
   sudo mkdir -p /var/lib/mitm-archiver/{data,certs}
   ```

2. **Configure (create .env for custom settings):**
   ```bash
   cp .env.example .env
   vi .env
   ```
   
   Update for production:
   ```bash
   CACHE_DIR=/var/lib/mitm-archiver/data
   LISTEN_PORT=42424
   CERTS_DIR=/var/lib/mitm-archiver/certs
   PROXY_AUTH=username:strongpassword
   ```

3. **Deploy:**
   ```bash
   docker compose up -d
   ```

4. **Verify:**
   ```bash
   docker compose logs -f
   curl -x localhost:42424 http://httpbin.org/get
   ```

### Management

```bash
# View logs
docker compose logs -f

# Restart
docker compose restart

# Stop
docker compose down

# Update configuration
vi .env
docker compose up -d  # Recreates with new config
```

---

## Quadlet Deployment (RHEL/Fedora)

### Prerequisites
- Podman 4.4+ with Quadlet support
- systemd
- Python 3.9+ (for Quadlet generation)

### Installation

1. **Prepare directories:**
   ```bash
   sudo mkdir -p /var/lib/mitm-archiver/{data,certs}
   
   # SELinux contexts (if enabled)
   sudo chcon -R -t container_file_t /var/lib/mitm-archiver
   ```

2. **Configure (.env is REQUIRED for Quadlet generation):**
   ```bash
   cp .env.example .env
   vi .env
   ```
   
   Update for production:
   ```bash
   CACHE_DIR=/var/lib/mitm-archiver/data
   LISTEN_PORT=42424
   CERTS_DIR=/var/lib/mitm-archiver/certs
   PROXY_AUTH=username:strongpassword
   ```

3. **Generate and install Quadlet:**
   ```bash
   make setup  # Install dependencies
   make quadlet  # Generate mitm-archiver.container from .env
   sudo cp mitm-archiver.container /etc/containers/systemd/
   sudo systemctl daemon-reload
   ```

4. **Start service:**
   ```bash
   sudo systemctl enable --now mitm-archiver.service
   ```

5. **Verify:**
   ```bash
   sudo systemctl status mitm-archiver.service
   sudo journalctl -u mitm-archiver.service -f
   curl -x localhost:42424 http://httpbin.org/get
   ```

### Management

```bash
# View logs
sudo journalctl -u mitm-archiver.service -f

# Restart
sudo systemctl restart mitm-archiver.service

# Stop
sudo systemctl stop mitm-archiver.service

# Update configuration
vi .env
make quadlet
sudo cp mitm-archiver.container /etc/containers/systemd/
sudo systemctl daemon-reload
sudo systemctl restart mitm-archiver.service
```

---

## Configuration

Settings can be customized via environment variables (in `.env` file or system environment).

### Configuration File Requirements

| Deployment Method | .env File | Defaults Used |
|-------------------|-----------|---------------|
| **Local Development** | Optional | ✅ Yes |
| **Docker Compose** | Optional | ✅ Yes |
| **Quadlet** | **Required** | ❌ No (for template generation) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_DIR` | `./data` | Directory for cached files |
| `LISTEN_PORT` | `8080` | Proxy listen port |
| `CERTS_DIR` | `./certs` | SSL certificates storage |
| `PROXY_AUTH` | _(empty)_ | Authentication (format: `username:password`) |

### Examples

**Local Development (using defaults):**
```bash
make run  # Uses: ./data, port 8080, ./certs, no auth
```

**Docker Compose (using defaults):**
```bash
docker compose up  # Uses: ./data, port 8080, ./certs, no auth
```

**Custom Configuration (any deployment):**
```bash
cp .env.example .env
vi .env  # Edit settings
make run  # or docker compose up, or make quadlet
```

## Security Considerations

- Always set `PROXY_AUTH` in production
- Use strong passwords
- Restrict network access with firewall rules
- Regularly update the mitmproxy image
- Monitor cache directory size

## Troubleshooting

**Port already in use:**
Change `LISTEN_PORT` in `.env` file

**Permission denied:**
Check directory ownership and SELinux contexts

**Certificate errors:**
Verify `CERTS_DIR` is writable and persistent

**Cache not persisting:**
Ensure `CACHE_DIR` is mounted correctly
