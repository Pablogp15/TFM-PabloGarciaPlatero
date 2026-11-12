# Ejecutar desde Anaconda Prompt: powershell -NoProfile -File .\scripts\run_gpu_service.ps1
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "local-config.ps1")
Set-Location $root
$gpuPython = Initialize-GpuConfiguration
Write-Host "Servicio GPU local en http://localhost:$env:GPU_SERVICE_PORT"
& $gpuPython -m uvicorn gpu_service.main:app --host $env:GPU_SERVICE_HOST --port $env:GPU_SERVICE_PORT --workers 1
exit $LASTEXITCODE
