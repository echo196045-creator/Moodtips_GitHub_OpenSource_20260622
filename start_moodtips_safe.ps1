$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$pythonLauncher = "py"
$pythonPrefix = @("-3")
try {
  & $pythonLauncher @pythonPrefix -c "import sys; print(sys.version)" | Out-Null
} catch {
  $pythonLauncher = "python"
  $pythonPrefix = @()
}

$port = $null
foreach ($candidate in 8000..8020) {
  $listener = Get-NetTCPConnection -LocalPort $candidate -State Listen -ErrorAction SilentlyContinue
  if (-not $listener) {
    $port = $candidate
    break
  }
}

if (-not $port) {
  Write-Host "No free port found between 8000 and 8020." -ForegroundColor Red
  exit 1
}

$env:HOST = "127.0.0.1"
$env:PORT = [string]$port
$url = "http://127.0.0.1:$port/app/"

Write-Host ""
Write-Host "Moodtips will start at:" -ForegroundColor Cyan
Write-Host $url -ForegroundColor Green
Write-Host ""
Write-Host "Installing/checking dependencies..."
& $pythonLauncher @pythonPrefix -m pip install -r "04_code\05_product_demo\requirements_product_demo_20260404.txt"

Write-Host ""
Write-Host "Starting Moodtips. Keep this window open while using the app." -ForegroundColor Cyan
Write-Host "If the browser opens too early, refresh it after a few seconds." -ForegroundColor DarkGray
Start-Job -ScriptBlock {
  param($targetUrl)
  Start-Sleep -Seconds 4
  Start-Process $targetUrl
} -ArgumentList $url | Out-Null

& $pythonLauncher @pythonPrefix serve_moodsips.py
