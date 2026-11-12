# Arranca la aplicación local y el servicio GPU. Ctrl+C detiene ambos.
# Uso: .\scripts\start-local.ps1

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$envFile = Join-Path $root ".env"

# DiffSynth imprime caracteres Unicode que cp1252 no puede codificar.
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

if (-not (Test-Path $envFile)) {
    throw "No se encontró .env. Copia .env.example a .env y configura los secretos y rutas locales."
}

. (Join-Path $PSScriptRoot "local-config.ps1")

$secretKey = Get-DotEnvValue "SECRET_KEY"
$serviceToken = Get-DotEnvValue "GENERATION_SERVICE_TOKEN"
$migratorPassword = Get-DotEnvValue "POSTGRES_MIGRATOR_PASSWORD"
$appPassword = Get-DotEnvValue "POSTGRES_APP_PASSWORD"
if (-not $secretKey -or $secretKey.Length -lt 32 -or $secretKey -match "^(cambia-|reemplazar_)") {
    throw "Configura SECRET_KEY en .env con un secreto aleatorio de al menos 32 caracteres."
}
if (-not $serviceToken -or $serviceToken.Length -lt 32 -or $serviceToken -match "^(cambia-|reemplazar_)") {
    throw "Configura GENERATION_SERVICE_TOKEN en .env con un secreto aleatorio de al menos 32 caracteres."
}
if (-not $migratorPassword -or $migratorPassword -match "^(cambia-|reemplazar_)" -or
    -not $appPassword -or $appPassword -match "^(cambia-|reemplazar_)") {
    throw "Configura contraseñas propias para PostgreSQL en .env."
}

$provider = Set-EnvFromFile "GENERATION_PROVIDER" "http"
if ($provider -ne "http") {
    throw "start-local.ps1 requiere GENERATION_PROVIDER=http para ejecutar la generación GPU."
}

$gpuPython = Initialize-GpuConfiguration
$gpuPort = [int]$env:GPU_SERVICE_PORT
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "No se encuentra Docker Desktop."
}

$logsPath = Join-Path $env:TEMP "MiniPaintAI"
New-Item -ItemType Directory -Force -Path $logsPath | Out-Null
$logSuffix = Get-Date -Format "yyyyMMdd-HHmmss"
$stdoutLog = Join-Path $logsPath "gpu-service-$logSuffix.log"
$stderrLog = Join-Path $logsPath "gpu-service-$logSuffix-error.log"
$gpuProcess = $null
$composeStarted = $false

try {
    Write-Host "Iniciando servicio GPU local en el puerto $gpuPort..."
    $gpuProcess = Start-Process `
        -FilePath $gpuPython `
        -ArgumentList @(
            "-m", "uvicorn", "gpu_service.main:app",
            "--host", $env:GPU_SERVICE_HOST,
            "--port", [string]$gpuPort
        ) `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog

    $startupTimeout = 1800
    $configuredTimeout = Get-DotEnvValue "GPU_STARTUP_TIMEOUT_SECONDS"
    if ($configuredTimeout -and $configuredTimeout -match "^\d+$") {
        $startupTimeout = [int]$configuredTimeout
    }
    $deadline = (Get-Date).AddSeconds($startupTimeout)
    $gpuReady = $false

    while ((Get-Date) -lt $deadline) {
        if ($gpuProcess.HasExited) {
            throw "El servicio GPU terminó al arrancar. Revisa los logs: $stderrLog"
        }
        try {
            $health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:$gpuPort/healthz" `
                -TimeoutSec 3
            if ($health.model -eq "error") {
                throw "El servicio GPU no pudo cargar el modelo. Revisa los logs: $stderrLog"
            }
            $preloadModel = $env:GPU_PRELOAD -match "^(?i:true|1|yes|on)$"
            if ($health.status -eq "ok" -and
                (-not $preloadModel -or $health.model -eq "ready")) {
                $gpuReady = $true
                break
            }
        } catch {
            if ($_.Exception.Message -like "El servicio GPU no pudo cargar*") {
                throw
            }
        }
        Start-Sleep -Seconds 2
    }
    if (-not $gpuReady) {
        throw "El servicio GPU no estuvo listo en $startupTimeout segundos. Revisa los logs: $stderrLog"
    }

    Write-Host "Servicio GPU listo."
    Write-Host "Iniciando MiniPaint AI. Abre http://localhost:8080"
    Write-Host "Pulsa Ctrl+C para detener la aplicación y el servicio GPU."
    $composeStarted = $true
    & docker compose up --build
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up terminó con código $LASTEXITCODE."
    }
} finally {
    if ($composeStarted) {
        Write-Host "Deteniendo los servicios Docker..."
        & docker compose down
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "docker compose down terminó con código $LASTEXITCODE."
        }
    }
    if ($gpuProcess -and -not $gpuProcess.HasExited) {
        Write-Host "Deteniendo el servicio GPU..."
        Stop-Process -Id $gpuProcess.Id
        $gpuProcess.WaitForExit(10000) | Out-Null
    }
}
