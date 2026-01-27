#!/bin/bash

# Script de actualización automática para el servidor de monitoreo (Producción)
# Uso: ./scripts/update_prod.sh

set -e # Detener script si hay error

echo "========================================"
echo "🚀 Iniciando actualización del Servidor"
echo "========================================"

# Obtener directorio raíz del proyecto (padre de scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "📂 Directorio del proyecto: $PROJECT_ROOT"

# 1. Descargar últimos cambios
echo "📥 1. Sincronizando código fuente (git reset --hard)..."
git fetch origin
git reset --hard origin/main

# 2. Backend: Entorno Virtual y Dependencias
echo "📦 2. Actualizando Backend..."
cd src/server

if [ ! -d ".venv" ]; then
    echo "   ⚠️  No se encontró .venv, creando entorno virtual..."
    python3 -m venv .venv
fi

echo "   🔌 Activando entorno virtual..."
source .venv/bin/activate

echo "   📥 Instalando dependencias (pip)..."
pip install -r requirements.txt

# 3. Aplicar migraciones
echo "🗄️  3. Verificando base de datos..."
# Ejecutamos el script de migración más reciente o el manual de fix
if [ -f "scripts/fix_db_schema_manual.py" ]; then
    python scripts/fix_db_schema_manual.py
else
    # Fallback a creación básica de tablas
    python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
fi

# 4. Frontend: Reconstruir (Opcional, si hay cambios)
echo "🎨 4. Reconstruyendo Frontend..."
cd ../client
if command -v npm >/dev/null; then
    npm install
    npm run build
else
    echo "   ⚠️  npm no encontrado, saltando build de frontend."
fi

# 5. Reiniciar servicios
echo "🔄 5. Reiniciando servicios..."
if systemctl is-active --quiet monitor-backend; then
    echo "   - Reiniciando servicio Systemd 'monitor-backend'..."
    sudo systemctl restart monitor-backend
    echo "   ✅ Servicio backend reiniciado."
elif systemctl is-active --quiet monitoreo-backend; then
    # Por si acaso el nombre antiguo
    echo "   - Reiniciando servicio Systemd 'monitoreo-backend'..."
    sudo systemctl restart monitoreo-backend
    echo "   ✅ Servicio backend reiniciado."
else
    echo "   ⚠️  No se detectó servicio systemd activo."
    echo "   Si estás ejecutando manualmente, por favor reinicia el proceso."
fi

echo "========================================"
echo "✅ Actualización completada con éxito"
echo "========================================"
