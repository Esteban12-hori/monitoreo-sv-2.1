<#
.SYNOPSIS
Script de Instalación Automática para Windows - Agente de Monitoreo

.DESCRIPTION
Instala dependencias, configura el agente y establece persistencia mediante Tarea Programada.

.PARAMETER Server
URL del servidor de métricas (opcional, anula config.default.json).

.PARAMETER Interval
Intervalo de envío en segundos.
#>

param (
    [string]$Server = "",
    [int]$Interval = 0
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = Join-Path $ScriptDir "install.log"
$ConfigDefault = Join-Path $ScriptDir "config.default.json"
$AgentScript = Join-Path $ScriptDir "agent.py"
$InstallScript = Join-Path $ScriptDir "install.py"
$ReqFile = Join-Path $ScriptDir "requirements.txt"

function Write-Log {
    param ([string]$Message, [string]$Level="INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogLine = "$Timestamp [$Level] $Message"
    Write-Host $LogLine -ForegroundColor $(if ($Level -eq "ERROR") { "Red" } elseif ($Level -eq "WARN") { "Yellow" } else { "Cyan" })
    Add-Content -Path $LogFile -Value $LogLine
}

# Inicio
"=== Inicio de Instalación: $(Get-Date) ===" | Out-File -FilePath $LogFile -Encoding UTF8
Write-Log "Iniciando script de instalación en Windows..."

# 1. Verificar Permisos de Administrador
$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Write-Log "Este script requiere permisos de Administrador." "ERROR"
    Write-Error "Ejecuta PowerShell como Administrador."
}

# 2. Leer Configuración
$MetricsUrl = ""
$IntervalVal = 60

if (Test-Path $ConfigDefault) {
    Write-Log "Leyendo configuración de $ConfigDefault"
    try {
        $JsonContent = Get-Content $ConfigDefault -Raw | ConvertFrom-Json
        if ($JsonContent.server) { $MetricsUrl = $JsonContent.server }
        if ($JsonContent.interval) { $IntervalVal = $JsonContent.interval }
    } catch {
        Write-Log "Error leyendo JSON: $_" "WARN"
    }
} else {
    Write-Log "No se encontró config.default.json" "WARN"
}

# Argumentos tienen prioridad
if ($Server) { $MetricsUrl = $Server }
if ($Interval -gt 0) { $IntervalVal = $Interval }

if (-not $MetricsUrl) {
    Write-Log "No se especificó URL del servidor." "ERROR"
    Write-Error "Debes definir 'server' en config.default.json o pasar el parámetro -Server"
}

Write-Log "Configuración: URL=$MetricsUrl, Intervalo=$IntervalVal"

# 3. Verificar Python
Write-Log "Verificando Python..."
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonExe = (Get-Command "python").Source
    Write-Log "Python encontrado: $PythonExe"
} else {
    Write-Log "Python no encontrado en el PATH." "ERROR"
    Write-Error "Por favor instala Python 3.8+ y agrégalo al PATH."
}

# 4. Instalar Dependencias
Write-Log "Instalando dependencias..."
if (Test-Path $ReqFile) {
    try {
        & $PythonExe -m pip install --upgrade pip | Out-Null
        & $PythonExe -m pip install -r $ReqFile | Out-File -FilePath $LogFile -Append
        Write-Log "Dependencias instaladas."
    } catch {
        Write-Log "Error instalando dependencias: $_" "ERROR"
        exit 1
    }
} else {
    Write-Log "No se encontró requirements.txt" "WARN"
}

# 5. Ejecutar install.py
Write-Log "Ejecutando configuración del agente..."
try {
    $InstallArgs = @($InstallScript, "--server", $MetricsUrl, "--interval", "$IntervalVal", "--auto")
    & $PythonExe $InstallArgs | Out-File -FilePath $LogFile -Append
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Configuración exitosa."
    } else {
        throw "El script install.py falló con código $LASTEXITCODE"
    }
} catch {
    Write-Log "Error en configuración: $_" "ERROR"
    exit 1
}

# 6. Configurar Persistencia (Tarea Programada)
$TaskName = "MonitoreoAgent"
Write-Log "Configurando Tarea Programada: $TaskName"

# Limpiar tarea anterior si existe
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Acción: Ejecutar python con el script del agente
# Usamos pythonw.exe si existe para que no abra ventana, o python.exe
$PythonW = $PythonExe.Replace("python.exe", "pythonw.exe")
if (-not (Test-Path $PythonW)) { $PythonW = $PythonExe }

$Action = New-ScheduledTaskAction -Execute $PythonW -Argument """$AgentScript"" --config ""$ScriptDir\agent.config.json""" -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings | Out-Null
    Write-Log "Tarea programada registrada exitosamente."
    
    # Iniciar la tarea ahora
    Start-ScheduledTask -TaskName $TaskName
    Write-Log "Tarea iniciada."
} catch {
    Write-Log "Error creando tarea programada: $_" "ERROR"
    Write-Log "Intenta ejecutar manualmente: python agent.py" "WARN"
}

Write-Log "¡Instalación finalizada con éxito!"
