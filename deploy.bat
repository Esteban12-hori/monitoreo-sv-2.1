@echo off
setlocal enabledelayedexpansion

echo 🚀 Iniciando despliegue de Monitoreo Server...

:: 1. Verificar prerrequisitos
echo 🔍 Verificando dependencias...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no encontrado. Por favor instálalo.
    exit /b 1
)

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js no encontrado. Por favor instálalo.
    exit /b 1
)

:: 2. Setup Backend
echo 📦 Configurando Backend...
cd src\server
if not exist venv (
    echo    Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate

echo    Instalando dependencias Python...
pip install -r requirements.txt >nul

:: 3. Setup Frontend
echo 🎨 Configurando Frontend...
cd ..\client
if not exist node_modules (
    echo    Instalando dependencias Node...
    call npm install >nul 2>&1
)

echo    Construyendo aplicación Vue...
call npm run build >nul

:: 4. Iniciar Servidor
echo ✅ Todo listo.
echo 🚀 Iniciando servidor en http://localhost:8000
cd ..\server

set PYTHONPATH=%CD%\..\..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

endlocal
