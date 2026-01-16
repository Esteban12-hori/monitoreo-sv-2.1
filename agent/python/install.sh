#!/bin/bash

# =============================================================================
# Script de Instalación Automática Multiplataforma (Linux/macOS)
# Agente de Monitoreo
# =============================================================================

set -e

# Colores para salida
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorios y Archivos
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DEFAULT="$BASE_DIR/config.default.json"
LOG_FILE="$BASE_DIR/install.log"

log() {
    local level=$1
    local msg=$2
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} [${level}] ${msg}" | tee -a "$LOG_FILE"
}

info() {
    log "INFO" "${BLUE}$1${NC}"
}

success() {
    log "SUCCESS" "${GREEN}$1${NC}"
}

warn() {
    log "WARN" "${YELLOW}$1${NC}"
}

error() {
    log "ERROR" "${RED}$1${NC}"
    exit 1
}

# Inicio del log
echo "=== Inicio de Instalación: $(date) ===" > "$LOG_FILE"
info "Iniciando script de instalación..."

# 1. Detección del Sistema Operativo
OS="$(uname -s)"
ARCH="$(uname -m)"
info "Sistema detectado: $OS ($ARCH)"

if [ "$OS" != "Linux" ] && [ "$OS" != "Darwin" ]; then
    error "Este script solo soporta Linux y macOS."
fi

# 2. Verificación de Permisos (Root/Sudo)
if [ "$EUID" -ne 0 ]; then
    warn "No se está ejecutando como root. Algunas tareas (como crear servicios) requerirán sudo."
    # No forzamos exit, pero pediremos sudo más adelante
fi

# 4. Verificación de Dependencias (Python 3)
info "Verificando Python 3..."
if command -v python3 &>/dev/null; then
    PYTHON_BIN=$(command -v python3)
    info "Python 3 encontrado en: $PYTHON_BIN"
else
    error "Python 3 no está instalado. Por favor instálalo antes de continuar."
fi

# 3. Lectura de Configuración por Defecto
METRICS_URL=""
INTERVAL=60

if [ -f "$CONFIG_DEFAULT" ]; then
    info "Leyendo configuración por defecto de $CONFIG_DEFAULT..."
    # Usar Python para leer JSON de forma segura
    METRICS_URL=$($PYTHON_BIN -c "import json; print(json.load(open('$CONFIG_DEFAULT')).get('server', ''))")
    INTERVAL_VAL=$($PYTHON_BIN -c "import json; print(json.load(open('$CONFIG_DEFAULT')).get('interval', ''))")
    
    if [ -n "$INTERVAL_VAL" ]; then
        INTERVAL=$INTERVAL_VAL
    fi
else
    warn "No se encontró $CONFIG_DEFAULT. Se usarán valores predeterminados."
fi

# Argumentos de línea de comandos pueden sobreescribir
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --server) METRICS_URL="$2"; shift ;;
        --interval) INTERVAL="$2"; shift ;;
        *) echo "Desconocido: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$METRICS_URL" ]; then
    error "No se especificó URL del servidor (server) en config.default.json ni en argumentos."
fi

info "Configuración: URL=$METRICS_URL, Intervalo=$INTERVAL"

# 5. Instalación de Dependencias Python
info "Instalando dependencias de Python..."
if [ -f "$BASE_DIR/requirements.txt" ]; then
    $PYTHON_BIN -m pip install --upgrade pip >> "$LOG_FILE" 2>&1
    if $PYTHON_BIN -m pip install -r "$BASE_DIR/requirements.txt" >> "$LOG_FILE" 2>&1; then
        success "Dependencias instaladas correctamente."
    else
        warn "Fallo en instalación estándar. Intentando con --break-system-packages (para distros nuevas)..."
        if $PYTHON_BIN -m pip install -r "$BASE_DIR/requirements.txt" --break-system-packages >> "$LOG_FILE" 2>&1; then
            success "Dependencias instaladas con --break-system-packages."
        else
            error "Error instalando dependencias. Revisa $LOG_FILE."
        fi
    fi
else
    warn "No se encontró requirements.txt."
fi

# 6. Ejecución del Script de Configuración (install.py)
info "Ejecutando configuración del agente..."
$PYTHON_BIN "$BASE_DIR/install.py" --server "$METRICS_URL" --interval "$INTERVAL" --auto >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    success "Configuración del agente completada."
else
    error "Error durante la configuración del agente. Revisa $LOG_FILE."
fi

# 7. Configuración del Servicio (Persistencia)
info "Configurando servicio del sistema..."

if [ "$OS" == "Linux" ]; then
    # Usar setup_service.sh si existe, o lógica inline
    SERVICE_SCRIPT="$BASE_DIR/setup_service.sh"
    if [ -f "$SERVICE_SCRIPT" ]; then
        chmod +x "$SERVICE_SCRIPT"
        # setup_service.sh usa sudo internamente, así que lo llamamos directo
        if "$SERVICE_SCRIPT" >> "$LOG_FILE" 2>&1; then
            success "Servicio systemd configurado e iniciado."
        else
            error "Error configurando el servicio systemd."
        fi
    else
        warn "No se encontró setup_service.sh. No se configuró el servicio automático."
    fi
elif [ "$OS" == "Darwin" ]; then
    # Lógica básica para macOS (LaunchAgent) si fuera necesario
    warn "Configuración automática de servicio en macOS no implementada en este script."
    info "Puedes ejecutar el agente manualmente: python3 agent.py"
fi

# 8. Validación Post-Instalación
info "Validando instalación..."
# Verificar si el proceso está corriendo
if pgrep -f "agent.py" > /dev/null; then
    success "El agente se está ejecutando."
else
    warn "El agente no parece estar ejecutándose. Intenta iniciarlo manualmente."
fi

success "¡Instalación finalizada con éxito!"
echo "Log completo en: $LOG_FILE"
