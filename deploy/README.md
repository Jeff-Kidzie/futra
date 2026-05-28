# Futra Dashboard — Deployment Guide

## Prerequisites

- Windows VPS (Windows Server 2019+ or Windows 10/11 Pro) with MT5 installed
- Domain name pointed to VPS IP (e.g., via DuckDNS, Cloudflare, or any registrar)
- Administrator access to the VPS

## 1. Install Dependencies

### Python 3.10+
Download and install from https://python.org. Check "Add Python to PATH".

### Node.js 18+
Download and install from https://nodejs.org (LTS version).

### Caddy (HTTPS reverse proxy)
Download from https://caddyserver.com/download (Windows binary).
Place `caddy.exe` in `C:\Caddy\` and add to PATH:
```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Caddy", "Machine")
```

## 2. Clone and Configure

```powershell
git clone <repo-url> C:\Futra
cd C:\Futra
```

## 3. Environment Configuration

Copy the environment template and fill in your values:
```powershell
copy .env.example .env
notepad .env
```

**Required values to set:**
- `FUTRA_MT5_LOGIN`, `FUTRA_MT5_PASSWORD`, `FUTRA_MT5_SERVER` — your MT5 credentials
- `FUTRA_DASHBOARD_DOMAIN` — your domain (e.g., `futra.duckdns.org`)
- `FUTRA_SESSION_SECRET` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`

## 4. Configure Caddy Domain

Edit `deploy/Caddyfile` and replace `dashboard.yourdomain.com` with your actual domain:
```caddyfile
your-actual-domain.com {
    reverse_proxy localhost:8000
    ...
}
```

## 5. Run Dashboard

### One-time start:
```powershell
# Run as Administrator (required for firewall rules)
powershell -ExecutionPolicy Bypass -File deploy/start-dashboard.ps1
```

### Run as Windows Service (auto-start on boot):

Using NSSM (Non-Sucking Service Manager):
```powershell
# Install NSSM
choco install nssm -y
# Or download from https://nssm.cc

# Create the service
nssm install FutraDashboard "C:\Futra\deploy\start-dashboard.ps1"
nssm set FutraDashboard AppDirectory "C:\Futra"
nssm set FutraDashboard Start SERVICE_AUTO_START
nssm start FutraDashboard
```

For Caddy as a service:
```powershell
nssm install FutraCaddy "C:\Caddy\caddy.exe" "run --config C:\Futra\deploy\Caddyfile --adapter caddyfile"
nssm set FutraCaddy AppDirectory "C:\Futra"
nssm set FutraCaddy Start SERVICE_AUTO_START
nssm start FutraCaddy
```

## 6. Verify

1. Open browser to `https://your-domain.com`
2. You should see the Futra login page
3. First startup creates a default admin user — credentials are logged to the Python console
4. Change the default password immediately after first login

## 7. Firewall Verification

Check firewall rules are active:
```powershell
netsh advfirewall firewall show rule name="Futra HTTPS"
netsh advfirewall firewall show rule name="Futra Block 8000"
```

Expected: port 443 is allowed inbound, port 8000 is blocked for external connections.

## Troubleshooting

### Caddy says "permission denied" on port 443
Run Caddy as Administrator or use `caddy run` (not `caddy start`).

### Let's Encrypt certificate fails
- Ensure port 80 and 443 are open and reachable from the internet
- Domain must resolve to the VPS IP (check with `nslookup your-domain.com`)
- Caddy requires port 80 for HTTP-01 challenge (temporarily open if blocked)

### Dashboard shows "Unable to load data"
- Verify MT5 is running and logged in
- Check FastAPI is running: visit `http://localhost:8000/docs` on the VPS
- Check Caddy logs: `C:\Futra\logs\caddy.log`

### Session expires immediately
- Ensure `FUTRA_SESSION_SECRET` is set in `.env` (not the default `change_me_...`)
- Without a persistent secret, tokens invalidate on every service restart
