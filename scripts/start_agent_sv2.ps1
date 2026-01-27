param(
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AgentDir = Join-Path $RootDir "agent\python"
$VenvDir = Join-Path $RootDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (!(Test-Path $PythonExe)) {
    throw "No se encontró el entorno virtual. Ejecuta start_all.ps1 primero."
}

# Configuración para SV2
$ServerId = "sv2"
$Token = "sv2-secret-token"
$ConfigPath = Join-Path $AgentDir "agent_sv2.config.json"

Write-Host "=== Iniciando Agente SV2 (Simulación) ===" -ForegroundColor Cyan

# 1. Registrar SV2 en Backend
try {
    Write-Host "Registrando '$ServerId' en el backend..." -ForegroundColor Yellow
    $Body = @{
        server_id = $ServerId
        token = $Token
    } | ConvertTo-Json

    Invoke-RestMethod -Uri "http://localhost:8000/api/register" -Method Post -Body $Body -ContentType "application/json"
    Write-Host "Servidor SV2 registrado." -ForegroundColor Green
} catch {
    Write-Host "Advertencia: No se pudo registrar SV2 (asegúrate de que start_all.ps1 esté corriendo): $_" -ForegroundColor Red
}

# 2. Crear Config
if (!(Test-Path $ConfigPath)) {
    Write-Host "Creando configuración para $ServerId..." -ForegroundColor Yellow
    $ConfigContent = @{
        server = "http://localhost:8000"
        server_id = $ServerId
        token = $Token
        interval = 10  # Intervalo diferente para probar independencia
        verify = "false"
    } | ConvertTo-Json
    Set-Content -Path $ConfigPath -Value $ConfigContent
}

# 3. Ejecutar Agente
Write-Host "Ejecutando agente para $ServerId..." -ForegroundColor Green
Start-Process -FilePath $PythonExe -ArgumentList "agent.py", "--config", "agent_sv2.config.json" -WorkingDirectory $AgentDir

Write-Host "Agente SV2 iniciado en segundo plano." -ForegroundColor Cyan
