$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Join-Path $ProjectRoot "Accordance"

Write-Host ""
Write-Host "Accordance local mobile web"
Write-Host "----------------------------------------"
Write-Host "Keep this terminal open while using the phone site."
Write-Host "If this terminal closes, the phone page will stop working."
Write-Host ""

$ips = @()
try {
    $ips = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.PrefixOrigin -ne "WellKnown" -and
            $_.AddressState -eq "Preferred" -and
            -not $_.SkipAsSource -and
            $_.InterfaceAlias -notmatch "vEthernet|WSL|Docker"
        } |
        Select-Object -ExpandProperty IPAddress -Unique
} catch {
    $ips = @()
}

if ($ips.Count -gt 0) {
    Write-Host "Phone URLs to try on the same Wi-Fi/hotspot:"
    foreach ($ip in $ips) {
        Write-Host "  http://$ip`:8000"
    }
} else {
    Write-Host "Could not detect a LAN IP. On your phone, use:"
    Write-Host "  http://电脑局域网IP:8000"
}

Write-Host ""
Write-Host "Local computer URL:"
Write-Host "  http://127.0.0.1:8000"
Write-Host ""

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found in PATH."
    exit 1
}

Set-Location $ProjectRoot
python -B -c "import fastapi, uvicorn, jinja2, multipart" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Web dependencies are missing. Run this once:"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

try {
    $portListener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
} catch {
    $portListener = $null
}
if ($portListener) {
    Write-Host "Port 8000 is already in use. Close the existing service, then run this script again."
    exit 1
}

Set-Location $AppDir
python -B -m uvicorn web.app:app --host 0.0.0.0 --port 8000
