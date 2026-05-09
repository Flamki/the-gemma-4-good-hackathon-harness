$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\.."
$runDir = Join-Path $root ".run"
if (-not (Test-Path $runDir)) {
  New-Item -Path $runDir -ItemType Directory | Out-Null
}

$pidPath = Join-Path $runDir "tunnel.pid"
$logPath = Join-Path $runDir "tunnel.log"
$errPath = Join-Path $runDir "tunnel.err"

if (Test-Path $pidPath) {
  $existingPid = Get-Content $pidPath -ErrorAction SilentlyContinue
  if ($existingPid) {
    try {
      $proc = Get-Process -Id $existingPid -ErrorAction Stop
      Write-Host "Tunnel already running (PID $($proc.Id))."
      if (Test-Path $logPath) {
        Get-Content $logPath
      }
      exit 0
    }
    catch {
      Remove-Item $pidPath -Force
    }
  }
}

if (Test-Path $logPath) { Remove-Item $logPath -Force }
if (Test-Path $errPath) { Remove-Item $errPath -Force }

Write-Host "Starting background public tunnel..."
$proc = Start-Process `
  -FilePath "cmd.exe" `
  -ArgumentList "/c", "npx --yes localtunnel --port 8000" `
  -WorkingDirectory $root `
  -RedirectStandardOutput $logPath `
  -RedirectStandardError $errPath `
  -WindowStyle Hidden `
  -PassThru

$proc.Id | Set-Content $pidPath
Start-Sleep -Seconds 3

if (Test-Path $logPath) {
  $log = Get-Content $logPath
  $url = $log | Where-Object { $_ -match "https?://" } | Select-Object -First 1
  if ($url) {
    Write-Host "Tunnel URL: $url"
    exit 0
  }
}

Write-Host "Tunnel started (PID $($proc.Id)). URL not yet detected; check .run/tunnel.log"
