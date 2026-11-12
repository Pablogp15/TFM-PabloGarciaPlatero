# Pruebas de lectura y precedencia; no inicia servicios ni carga modelos.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "local-config.ps1")
$testEnvFile = [IO.Path]::GetTempFileName()
$originalEnvFile = $envFile
$variableName = "MINIPAINT_CONFIG_TEST"
try {
    $envFile = $testEnvFile
    [IO.File]::WriteAllText($testEnvFile, "MINIPAINT_CONFIG_TEST='from-file'`n")
    if ((Get-DotEnvValue $variableName) -ne "from-file") { throw "Lectura .env incorrecta" }
    [Environment]::SetEnvironmentVariable($variableName, "from-terminal", "Process")
    if ((Set-EnvFromFile $variableName "default") -ne "from-terminal") {
        throw "La terminal debe prevalecer sobre .env"
    }
    [Environment]::SetEnvironmentVariable($variableName, $null, "Process")
    [IO.File]::WriteAllText($testEnvFile, "")
    if ((Set-EnvFromFile $variableName "default") -ne "default") {
        throw "No se aplica el valor predeterminado"
    }
    if ((Resolve-LocalPath "..\AI\qwenImageEdit\models") -ne
        [IO.Path]::GetFullPath((Join-Path $root "..\AI\qwenImageEdit\models"))) {
        throw "Ruta relativa incorrecta"
    }
    Write-Host "4 comprobaciones de configuración superadas."
} finally {
    $envFile = $originalEnvFile
    [Environment]::SetEnvironmentVariable($variableName, $null, "Process")
    Remove-Item -LiteralPath $testEnvFile
}
