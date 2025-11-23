# Mitm Archiver

A mitm proxy that archives downloads (download once) - acting as a permanent "Lazy Mirror" for external assets used in CI/CD pipelines.

**What it does:** Intercepts HTTP/HTTPS traffic and permanently caches downloaded files. When upstream vendors delete, move, or change files, the proxy continues serving cached copies indefinitely - ensuring build pipeline reliability.

## Quick Start

### Local Development
```bash
make setup  # Create venv and install dependencies
make run    # Start proxy on localhost:8080
make test   # Test with sample requests
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed developer documentation.

### Production Deployment

Choose your deployment method:
- [Docker Compose](#docker-compose-deployment) - Portable, works anywhere
- [Systemd Quadlet](#quadlet-deployment-rhelfedora) - Native systemd integration for RHEL/Fedora

---

## Docker Compose Deployment

### Prerequisites
- Docker and Docker Compose installed
- Root or docker group access

### Installation

1. **Prepare directories:**
   ```bash
   sudo mkdir -p /var/lib/mitm-archiver/{data,certs}
   ```

2. **Configure:**
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

### Installation

1. **Prepare directories:**
   ```bash
   sudo mkdir -p /var/lib/mitm-archiver/{data,certs}
   
   # SELinux contexts (if enabled)
   sudo chcon -R -t container_file_t /var/lib/mitm-archiver
   ```

2. **Configure:**
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
   python3 scripts/generate-quadlet.py
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
python3 scripts/generate-quadlet.py
sudo cp mitm-archiver.container /etc/containers/systemd/
sudo systemctl daemon-reload
sudo systemctl restart mitm-archiver.service
```

---

## Configuration

All settings are controlled via environment variables in `.env` file:

| Variable | Description | Example |
|----------|-------------|---------|
| `CACHE_DIR` | Directory for cached files | `/var/lib/mitm-archiver/data` |
| `LISTEN_PORT` | Proxy listen port | `42424` |
| `CERTS_DIR` | SSL certificates storage | `/var/lib/mitm-archiver/certs` |
| `PROXY_AUTH` | Authentication (optional) | `username:password` |

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
