$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\.."
$pidPath = Join-Path $root ".run\tunnel.pid"

if (-not (Test-Path $pidPath)) {
  Write-Host "No tunnel PID file found."
  exit 0
}

$pidValue = Get-Content $pidPath -ErrorAction SilentlyContinue
if ($pidValue) {
  try {
    Stop-Process -Id $pidValue -Force -ErrorAction Stop
    Write-Host "Stopped tunnel PID: $pidValue"
  }
  catch {
    Write-Host "Tunnel process not running."
  }
}

Remove-Item $pidPath -Force
