# 📊 UpKeep

Sistema de monitoreo de servidores profesional, moderno y fácil de desplegar. Diseñado para proporcionar visibilidad completa sobre tu infraestructura con una experiencia de usuario intuitiva.

## 🚀 Características Principales

- **Dashboard Moderno**: Interfaz responsive construida con Vue 3 y TailwindCSS (Soporte Dark Mode).
- **Detección de SO**: Identificación automática de Linux/Windows basada en procesos activos.
- **Métricas en Tiempo Real**: CPU, RAM, Disco, Red y estado de servicios (Docker, Redis, etc.).
- **Agente Ligero**: Agente en Python optimizado con instalación interactiva fácil.
- **Alertas Inteligentes**: Notificaciones SMTP configurables.
- **Seguridad**: Autenticación JWT y gestión de roles.
- **Fácil Despliegue**: Soporte completo para Docker y scripts de instalación automatizados.

## 🛠 Stack Tecnológico

- **Frontend**: Vue 3, TailwindCSS, Chart.js, Vite.
- **Backend**: Python FastAPI, SQLAlchemy, SQLite (por defecto).
- **Agente**: Python (psutil, requests).
- **Infraestructura**: Docker, Docker Compose, Nginx.

---

## 🐳 Despliegue Rápido (Docker Compose) - ¡Recomendado!

La forma más sencilla de iniciar el servidor (Backend + Frontend).

1. **Requisitos**: Tener Docker y Docker Compose instalados.
2. **Ejecutar**:
   ```bash
   docker-compose up -d --build
   ```
3. **Acceder**:
   - Dashboard: [http://localhost](http://localhost)
   - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 🔑 Credenciales por Defecto
- **Usuario**: `admi@gmial.com`
- **Contraseña**: `admin`

---

## 🖥️ Instalación del Agente (En servidores a monitorear)

El agente debe instalarse en cada servidor que desees monitorear.

### Opción A: Script Interactivo (Fácil)

1. Copia la carpeta `agent/python` al servidor destino.
2. Ejecuta el script de instalación:
   
   **Windows:**
   ```cmd
   cd agent/python
   setup_agent.bat
   ```
   
   **Linux:**
   ```bash
   cd agent/python
   chmod +x setup_agent.sh
   ./setup_agent.sh
   ```

3. Sigue las instrucciones en pantalla para configurar la URL del servidor y el Token.

### Opción B: Docker

```bash
docker run -d \
  --name monitor-agent \
  --network host \
  -e SERVER_URL="http://TU_IP_SERVIDOR:8000" \
  -e SERVER_ID="mi-servidor-01" \
  -e TOKEN="TU_TOKEN_DE_AGENTE" \
  monitor-agent-image
```
*(Nota: Debes construir la imagen del agente primero usando `agent/python/Dockerfile`)*

---

## 🔧 Instalación Manual (Desarrollo)

Si prefieres ejecutarlo localmente sin Docker para desarrollo.

### 1. Backend
```bash
cd src/server
python -m venv venv
# Windows: venv\Scripts\activate
# Linux: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn src.server.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd src/client
npm install
npm run dev
```

---

## 📄 Estructura del Proyecto

```
.
├── agent/                  # Código del agente de monitoreo
│   └── python/             # Implementación en Python + Scripts de instalación
├── src/
│   ├── client/             # Frontend (Vue 3 + Vite)
│   └── server/             # Backend (FastAPI)
├── docker-compose.yml      # Orquestación de contenedores
└── README.md               # Documentación
```

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Por favor, abre un issue o un pull request para mejoras y correcciones.
