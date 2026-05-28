<#
.SYNOPSIS
    Futra Dashboard -- Production Startup Script for Windows VPS
.DESCRIPTION
    Builds the SvelteKit frontend, starts the FastAPI backend, and launches
    the Caddy reverse proxy. Must be run as Administrator for firewall rules.
.PARAMETER Dev
    Run in development mode (Vite dev server + FastAPI, no Caddy).
.EXAMPLE
    .\deploy\start-dashboard.ps1
.EXAMPLE
    .\deploy\start-dashboard.ps1 -Dev
#>
param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Futra Dashboard -- Production Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Check prerequisites ---
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

# Check Python
try {
    $PythonVersion = python --version 2>&1
    Write-Host "  Python: $PythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "  ERROR: Python not found. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Check Node.js
try {
    $NodeVersion = node --version 2>&1
    Write-Host "  Node.js: $NodeVersion" -ForegroundColor Green
}
catch {
    Write-Host "  ERROR: Node.js not found. Install from https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Check Caddy (skip in dev mode)
if (-not $Dev) {
    try {
        $CaddyVersion = caddy version 2>&1
        Write-Host "  Caddy: $CaddyVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "  WARNING: Caddy not found. Install from https://caddyserver.com/download" -ForegroundColor Yellow
        Write-Host "  Dashboard will run on http://localhost:8000 (no HTTPS) until Caddy is installed." -ForegroundColor Yellow
    }
}

Write-Host ""

# --- Step 2: Install Python dependencies ---
Write-Host "[2/5] Installing Python dependencies..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    pip install -r requirements.txt --quiet
    Write-Host "  Python dependencies installed." -ForegroundColor Green
}
catch {
    Write-Host "  ERROR: Failed to install Python dependencies." -ForegroundColor Red
    Pop-Location
    exit 1
}

# --- Step 3: Build frontend ---
if (-not $Dev) {
    Write-Host "[3/5] Building SvelteKit frontend..." -ForegroundColor Yellow
    if (Test-Path "frontend") {
        Push-Location frontend
        try {
            npm install --silent
            npm run build
            Write-Host "  Frontend built to frontend/build/" -ForegroundColor Green
        }
        catch {
            Write-Host "  ERROR: Frontend build failed." -ForegroundColor Red
            Pop-Location
            Pop-Location
            exit 1
        }
        Pop-Location
    }
    else {
        Write-Host "  WARNING: frontend/ directory not found. Skipping frontend build." -ForegroundColor Yellow
    }
}
else {
    Write-Host "[3/5] Development mode -- skipping frontend build." -ForegroundColor Yellow
}
Write-Host ""

# --- Step 4: Configure firewall (production only) ---
if (-not $Dev) {
    Write-Host "[4/5] Configuring Windows Firewall..." -ForegroundColor Yellow

    # Check admin rights
    $IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $IsAdmin) {
        Write-Host "  WARNING: Not running as Administrator. Firewall rules cannot be configured." -ForegroundColor Yellow
        Write-Host "  Run this script as Administrator to configure firewall automatically," -ForegroundColor Yellow
        Write-Host "  or manually run the following commands:" -ForegroundColor Yellow
        Write-Host '    netsh advfirewall firewall add rule name="Futra HTTPS" dir=in action=allow protocol=TCP localport=443' -ForegroundColor Yellow
        Write-Host '    netsh advfirewall firewall add rule name="Futra Block 8000" dir=in action=block protocol=TCP localport=8000' -ForegroundColor Yellow
    }
    else {
        # Allow HTTPS (port 443)
        netsh advfirewall firewall add rule name="Futra HTTPS" dir=in action=allow protocol=TCP localport=443 2>$null
        Write-Host "  Firewall: Port 443 (HTTPS) -- ALLOWED" -ForegroundColor Green

        # Block direct FastAPI access (port 8000) from external
        netsh advfirewall firewall add rule name="Futra Block 8000" dir=in action=block protocol=TCP localport=8000 2>$null
        Write-Host "  Firewall: Port 8000 (FastAPI direct) -- BLOCKED externally" -ForegroundColor Green
    }
}
else {
    Write-Host "[4/5] Development mode -- skipping firewall configuration." -ForegroundColor Yellow
}
Write-Host ""

# --- Step 5: Start services ---
Write-Host "[5/5] Starting dashboard services..." -ForegroundColor Yellow
Pop-Location

if ($Dev) {
    Write-Host "  Development mode -- start these in separate terminals:" -ForegroundColor Cyan
    Write-Host "    Terminal 1: cd python; python -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000 --reload" -ForegroundColor White
    Write-Host "    Terminal 2: cd frontend; npm run dev" -ForegroundColor White
}
else {
    Write-Host "  Starting FastAPI on http://localhost:8000 ..." -ForegroundColor Green
    Write-Host ""

    # Check for .env file
    if (-not (Test-Path ".env")) {
        Write-Host "  WARNING: No .env file found. Copy .env.example to .env and configure it." -ForegroundColor Yellow
        Write-Host "  Using default values -- sessions will invalidate on restart." -ForegroundColor Yellow
    }

    # Start FastAPI
    $Env:FUTRA_DASHBOARD_DEV = "false"
    Start-Process python -ArgumentList "-m", "uvicorn", "dashboard.main:app", "--host", "127.0.0.1", "--port", "8000" -NoNewWindow

    Start-Sleep -Seconds 3

    # Start Caddy (if available)
    try {
        $null = caddy version 2>&1
        Write-Host "  Starting Caddy reverse proxy on port 443..." -ForegroundColor Green
        Start-Process caddy -ArgumentList "run", "--config", "deploy/Caddyfile", "--adapter", "caddyfile" -NoNewWindow
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Green
        Write-Host "  Dashboard is running!" -ForegroundColor Green
        Write-Host "  HTTPS: https://$($env:FUTRA_DASHBOARD_DOMAIN)" -ForegroundColor Green
        Write-Host "  (Or https://localhost if domain not configured)" -ForegroundColor Green
        Write-Host "============================================" -ForegroundColor Green
    }
    catch {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Yellow
        Write-Host "  FastAPI running on http://localhost:8000" -ForegroundColor Yellow
        Write-Host "  Install Caddy for HTTPS: https://caddyserver.com/download" -ForegroundColor Yellow
        Write-Host "============================================" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Press Ctrl+C to stop all services." -ForegroundColor Gray
