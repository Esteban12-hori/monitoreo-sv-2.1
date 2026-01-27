#!/bin/bash
echo "🔍 Diagnóstico de arranque manual..."
echo "Usuario actual: $(whoami)"
echo "Directorio: /opt/monitoreo-sv-2.1"

cd /opt/monitoreo-sv-2.1

# Verificar si existe el entorno virtual
if [ -d "src/server/.venv" ]; then
    echo "✅ Entorno .venv encontrado."
    VENV_PYTHON="src/server/.venv/bin/python"
elif [ -d "src/server/venv" ]; then
    echo "⚠️ Entorno 'venv' encontrado (no .venv). Ajustando..."
    VENV_PYTHON="src/server/venv/bin/python"
else
    echo "❌ No se encuentra el entorno virtual en src/server/.venv ni src/server/venv"
    exit 1
fi

echo "🚀 Intentando iniciar uvicorn manualmente..."
export PYTHONPATH=/opt/monitoreo-sv-2.1
$VENV_PYTHON -m uvicorn src.server.app.main:app --host 0.0.0.0 --port 8001

