param(
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

Write-Host "=== Iniciando UpKeep (backend + frontend) ===" -ForegroundColor Cyan

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "src\server"
$FrontendDir = Join-Path $RootDir "src\client"
$AgentDir = Join-Path $RootDir "agent\python"
$VenvDir = Join-Path $RootDir ".venv"

Write-Host "Directorio raíz: $RootDir"

if (!(Test-Path $BackendDir)) {
    throw "No se encontró el backend en $BackendDir"
}
if (!(Test-Path $FrontendDir)) {
    throw "No se encontró el frontend en $FrontendDir"
}
if (!(Test-Path $AgentDir)) {
    throw "No se encontró el agente en $AgentDir"
}

if (!(Test-Path $VenvDir)) {
    Write-Host "Creando entorno virtual de Python en .venv..." -ForegroundColor Yellow
    python -m venv $VenvDir
}

$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
if (!(Test-Path $PythonExe)) {
    throw "No se encontró el intérprete de Python en $PythonExe"
}

if (-not $NoInstall) {
    Write-Host "Instalando dependencias de backend y agente..." -ForegroundColor Yellow
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt")
    & $PythonExe -m pip install -r (Join-Path $AgentDir "requirements.txt")
}

Write-Host "Lanzando backend (FastAPI + Uvicorn) en segundo plano..." -ForegroundColor Green
$BackendArgs = @(
    "-m", "uvicorn",
    "src.server.app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
)
Start-Process -FilePath $PythonExe -ArgumentList $BackendArgs -WorkingDirectory $RootDir

# Esperar a que el backend inicie para registrar el servidor local
Write-Host "Esperando 5 segundos para inicio del backend..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Auto-registrar servidor local
$LocalServerId = "local-pc"
$LocalToken = "local-token-secret"
$AgentConfigPath = Join-Path $AgentDir "agent.config.json"

Write-Host "Registrando '$LocalServerId' en el backend..." -ForegroundColor Yellow
try {
    $Body = @{
        server_id = $LocalServerId
        token = $LocalToken
    } | ConvertTo-Json

    Invoke-RestMethod -Uri "http://localhost:8000/api/register" -Method Post -Body $Body -ContentType "application/json"
    Write-Host "Servidor registrado exitosamente." -ForegroundColor Green
} catch {
    Write-Host "No se pudo registrar el servidor (¿Backend no listo?): $_" -ForegroundColor Red
}

# Crear configuración del agente si no existe
if (!(Test-Path $AgentConfigPath)) {
    Write-Host "Creando configuración predeterminada para el agente ($AgentConfigPath)..." -ForegroundColor Yellow
    $ConfigContent = @{
        server = "http://localhost:8000"
        server_id = $LocalServerId
        token = $LocalToken
        interval = 5
        verify = "false"
    } | ConvertTo-Json
    Set-Content -Path $AgentConfigPath -Value $ConfigContent
}

if (-not $NoInstall) {
    Write-Host "Instalando dependencias del frontend (npm install)..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

Write-Host "Lanzando frontend (npm run dev) en segundo plano..." -ForegroundColor Green
Push-Location $FrontendDir
Start-Process "npm" "run dev"
Pop-Location

Write-Host "Lanzando agente (agent.py) en segundo plano..." -ForegroundColor Green
Start-Process -FilePath $PythonExe -ArgumentList "agent.py" -WorkingDirectory $AgentDir

Write-Host ""
Write-Host "=== Todo listo ===" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000"
Write-Host "Frontend: http://localhost:5173"
Write-Host "Agente:   ejecutándose en segundo plano usando agent.config.json" 
Write-Host ""
Write-Host "Puedes volver a usar este script con -NoInstall para evitar reinstalar dependencias." -ForegroundColor DarkGray
