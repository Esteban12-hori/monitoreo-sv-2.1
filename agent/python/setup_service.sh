#!/bin/bash
set -e

# Detectar directorio actual (donde está este script y agent.py)
AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="monitoreo-agent.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
CURRENT_USER=$(whoami)
# Detectar Python (preferir venv)
if [ -f "$AGENT_DIR/venv/bin/python" ]; then
    PYTHON_EXEC="$AGENT_DIR/venv/bin/python"
    echo "✅ Entorno virtual detectado: $PYTHON_EXEC"
elif [ -f "$AGENT_DIR/venv/bin/python3" ]; then
    PYTHON_EXEC="$AGENT_DIR/venv/bin/python3"
    echo "✅ Entorno virtual detectado: $PYTHON_EXEC"
else
    PYTHON_EXEC=$(which python3)
    echo "⚠️  Usando Python del sistema: $PYTHON_EXEC"
fi

echo "=== Instalación del Servicio del Agente ==="
echo "Directorio del Agente: $AGENT_DIR"
echo "Usuario de ejecución: $CURRENT_USER"
echo "Python: $PYTHON_EXEC"

# Verificar que agent.config.json existe
if [ ! -f "$AGENT_DIR/agent.config.json" ]; then
    echo "⚠️  No se encontró 'agent.config.json'."
    echo "Ejecutando instalador para generar configuración..."
    python3 "$AGENT_DIR/install.py"
    
    # Verificar de nuevo
    if [ ! -f "$AGENT_DIR/agent.config.json" ]; then
        echo "❌ Error: La configuración no fue creada. Abortando."
        exit 1
    fi
else
    echo "✅ Archivo de configuración encontrado."
fi

# Crear archivo de servicio
echo "📝 Creando archivo de servicio en $SERVICE_PATH..."
sudo bash -c "cat > $SERVICE_PATH" <<EOF
[Unit]
Description=Monitoreo Agent Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$AGENT_DIR
ExecStart=$PYTHON_EXEC -u $AGENT_DIR/agent.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Recargar y habilitar
echo "🔄 Recargando systemd..."
sudo systemctl daemon-reload
echo "✅ Habilitando servicio..."
sudo systemctl enable $SERVICE_NAME
echo "🚀 Iniciando servicio..."
sudo systemctl restart $SERVICE_NAME

echo ""
echo "=== Instalación Completada ==="
echo "El agente se está ejecutando en segundo plano."
echo "Comandos útiles:"
echo "  Ver estado: sudo systemctl status $SERVICE_NAME"
echo "  Ver logs:   journalctl -u $SERVICE_NAME -f"
echo "  Parar:      sudo systemctl stop $SERVICE_NAME"
echo "  Reiniciar:  sudo systemctl restart $SERVICE_NAME"
