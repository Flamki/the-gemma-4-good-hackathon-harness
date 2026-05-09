$ErrorActionPreference = "Stop"

function Test-DockerDaemon {
  try {
    docker info *> $null
    return $true
  }
  catch {
    return $false
  }
}

if (Test-DockerDaemon) {
  Write-Host "Stopping RescueLoop container (if running)..."
  docker compose down
}

$root = Resolve-Path "$PSScriptRoot\.."
$pidPath = Join-Path $root ".run\uvicorn.pid"
if (Test-Path $pidPath) {
  $pidValue = Get-Content $pidPath -ErrorAction SilentlyContinue
  if ($pidValue) {
    try {
      Stop-Process -Id $pidValue -Force -ErrorAction Stop
      Write-Host "Stopped local Python server PID: $pidValue"
    }
    catch {
      Write-Host "Local PID file found but process is not running."
    }
  }
  Remove-Item $pidPath -Force
}
