#!/bin/bash
set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando despliegue de Monitoreo Server...${NC}"

# 1. Verificar prerrequisitos
echo "🔍 Verificando dependencias..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 no encontrado. Por favor instálalo.${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js no encontrado. Por favor instálalo.${NC}"
    exit 1
fi

# 2. Setup Backend
echo -e "${GREEN}📦 Configurando Backend...${NC}"
cd src/server
if [ ! -d "venv" ]; then
    echo "   Creando entorno virtual..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "   Instalando dependencias Python..."
pip install -r requirements.txt > /dev/null

# 3. Setup Frontend
echo -e "${GREEN}🎨 Configurando Frontend...${NC}"
cd ../client
if [ ! -d "node_modules" ]; then
    echo "   Instalando dependencias Node..."
    npm install > /dev/null 2>&1
fi

echo "   Construyendo aplicación Vue..."
npm run build > /dev/null

# 4. Iniciar Servidor
echo -e "${GREEN}✅ Todo listo.${NC}"
echo -e "${GREEN}🚀 Iniciando servidor en http://localhost:8000${NC}"
cd ../server

# Usamos nohup para que siga corriendo si se cierra la terminal (opcional, pero util para despliegue basico)
# Pero como dice "ejecuta", lo haremos en foreground para que el usuario vea los logs.
# Asegurar PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/../..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
