#!/bin/bash
set -e

echo "🔧 Iniciando reparación del despliegue..."

# 1. Ajustar Permisos
echo "🔑 Ajustando permisos de carpetas..."
sudo chown -R azureuser:azureuser /opt/monitoreo-sv-2.1
sudo chmod -R 775 /opt/monitoreo-sv-2.1

# 2. Recrear Base de Datos y Usuario
echo "🗑️ Limpiando bases de datos antiguas..."
# Intentar borrar todas las variantes posibles
sudo rm -f /opt/monitoreo-sv-2.1/data.db
sudo rm -f /opt/monitoreo-sv-2.1/data/monitor.db
sudo rm -f /opt/monitoreo-sv-2.1/monitor.db
sudo rm -f /opt/monitoreo-sv-2.1/src/server/data.db
sudo rm -f /opt/monitoreo-sv-2.1/src/server/monitor.db

echo "👤 Creando usuario Admin (admin@example.com / 123456)..."
cd /opt/monitoreo-sv-2.1/src/server
# Ejecutar script de creación de usuario con PYTHONPATH correcto
# Usamos -m para ejecutar como módulo y evitar problemas de imports
sudo -u azureuser PYTHONPATH=/opt/monitoreo-sv-2.1 /opt/monitoreo-sv-2.1/src/server/.venv/bin/python -m scripts.create_users_manual --email admin@example.com --name Admin --admin <<EOF
123456
123456
EOF

# 3. Copiar archivo de servicio corregido
if [ -f "/opt/monitoreo-sv-2.1/deploy/systemd/monitor-backend.service" ]; then
    echo "⚙️ Actualizando servicio systemd..."
    sudo cp /opt/monitoreo-sv-2.1/deploy/systemd/monitor-backend.service /etc/systemd/system/monitor-backend.service
    sudo systemctl daemon-reload
fi

# 4. Copiar configuración de Nginx
if [ -f "/opt/monitoreo-sv-2.1/nginx_linux.conf" ]; then
    echo "🌐 Actualizando configuración de Nginx..."
    sudo cp /opt/monitoreo-sv-2.1/nginx_linux.conf /etc/nginx/conf.d/upkeep.conf
    sudo systemctl restart nginx
fi

# 5. Reiniciar Servicios Backend
echo "🔄 Reiniciando backend..."
sudo systemctl restart monitor-backend

echo "✅ Reparación completada. Intenta loguearte ahora en http://<TU_IP>:9090"
