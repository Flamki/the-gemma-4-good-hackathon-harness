$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\.."
$runDir = Join-Path $root ".run"
if (-not (Test-Path $runDir)) {
  New-Item -Path $runDir -ItemType Directory | Out-Null
}

$pidPath = Join-Path $runDir "uvicorn.pid"
if (Test-Path $pidPath) {
  $existingPid = Get-Content $pidPath -ErrorAction SilentlyContinue
  if ($existingPid) {
    try {
      $proc = Get-Process -Id $existingPid -ErrorAction Stop
      Write-Host "Local server already running (PID $($proc.Id))."
      exit 0
    }
    catch {
      Remove-Item $pidPath -Force
    }
  }
}

Write-Host "Starting local production server on port 8000..."
$process = Start-Process `
  -FilePath "python" `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
  -WorkingDirectory $root `
  -WindowStyle Hidden `
  -PassThru

$process.Id | Set-Content $pidPath
Write-Host "Started local server PID: $($process.Id)"
