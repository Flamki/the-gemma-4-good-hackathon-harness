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
  Write-Host "[1/3] Building and starting RescueLoop container..."
  docker compose up --build -d
}
else {
  Write-Host "[1/3] Docker daemon unavailable. Falling back to local Python server..."
  powershell -ExecutionPolicy Bypass -File scripts\deploy_local_python.ps1
}

Write-Host "[2/3] Waiting for service health..."
Start-Sleep -Seconds 3

try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 20
  Write-Host "[3/3] Service is up."
  $health | ConvertTo-Json -Depth 6
}
catch {
  Write-Host "Health check failed."
  Write-Host "If Docker mode was used, inspect with: docker compose logs --tail 200"
  Write-Host "If Python mode was used, inspect console by running uvicorn manually."
  throw
}
