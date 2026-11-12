# Configuración compartida: terminal > .env > valores predeterminados.
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"

function Get-DotEnvValue([string]$name) {
    $current = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($current) { return $current }
    if (Test-Path -LiteralPath $envFile) {
        $pattern = "^\s*" + [regex]::Escape($name) + "\s*=(.*)$"
        foreach ($line in Get-Content -LiteralPath $envFile -Encoding UTF8) {
            if ($line -match $pattern) {
                return $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
    return $null
}

function Set-EnvFromFile([string]$name, [string]$defaultValue) {
    $value = Get-DotEnvValue $name
    if (-not $value) { $value = $defaultValue }
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
    return $value
}

function Resolve-LocalPath([string]$value) {
    if (-not [IO.Path]::IsPathRooted($value)) { $value = Join-Path $root $value }
    return [IO.Path]::GetFullPath($value)
}

function Initialize-GpuConfiguration {
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $env:GPU_SERVICE_TOKEN = Set-EnvFromFile "GENERATION_SERVICE_TOKEN" ""
    if ($env:GPU_SERVICE_TOKEN.Length -lt 32 -or
        $env:GPU_SERVICE_TOKEN -match "^(cambia-|reemplazar_)") {
        throw "Configura GENERATION_SERVICE_TOKEN con un secreto de al menos 32 caracteres."
    }
    $env:GPU_MODEL_NAME = Set-EnvFromFile "GENERATION_MODEL_NAME" "Qwen-Image-Edit-2511"
    $env:GPU_PRELOAD = Set-EnvFromFile "GPU_PRELOAD" "true"
    $env:GPU_SERVICE_HOST = Set-EnvFromFile "GPU_SERVICE_HOST" "0.0.0.0"
    $serviceUrl = Set-EnvFromFile "GENERATION_SERVICE_URL" "http://host.docker.internal:8188"
    $uri = $null
    if (-not [Uri]::TryCreate($serviceUrl, [UriKind]::Absolute, [ref]$uri) -or
        $uri.Scheme -ne "http" -or
        $uri.Host -notin @("host.docker.internal", "127.0.0.1", "localhost")) {
        throw "GENERATION_SERVICE_URL debe apuntar al servicio HTTP de este equipo."
    }
    $env:GPU_SERVICE_PORT = [string]$uri.Port
    $env:DIFFSYNTH_MODEL_BASE_PATH = Resolve-LocalPath (
        Set-EnvFromFile "DIFFSYNTH_MODEL_BASE_PATH" "..\AI\qwenImageEdit\models")
    $env:DIFFSYNTH_SKIP_DOWNLOAD = "true"
    foreach ($name in @("GPU_MAX_INPUT_BYTES", "GPU_RESULT_TTL_SECONDS")) {
        $value = Get-DotEnvValue $name
        if ($value) { [Environment]::SetEnvironmentVariable($name, $value, "Process") }
    }
    $condaRoot = Resolve-LocalPath (Set-EnvFromFile "MINICONDA_ROOT" "..\miniconda3")
    $condaEnv = Set-EnvFromFile "GPU_CONDA_ENV" "qwen2511"
    $pythonSetting = Get-DotEnvValue "MINICONDA_PYTHON"
    if ($pythonSetting) { $gpuPython = Resolve-LocalPath $pythonSetting }
    else { $gpuPython = Join-Path $condaRoot "envs\$condaEnv\python.exe" }
    if (-not (Test-Path -LiteralPath $gpuPython -PathType Leaf)) {
        throw "No se encuentra el intérprete GPU. Configura MINICONDA_PYTHON."
    }
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Any, $uri.Port)
    try { $listener.Start() }
    catch { throw "El puerto GPU $($uri.Port) ya está ocupado. No se iniciará otra instancia." }
    finally { $listener.Stop() }
    & $gpuPython -m gpu_service.preflight | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "La comprobación del entorno GPU ha fallado." }
    return $gpuPython
}
