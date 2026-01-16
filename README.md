# Monitor Integral

Sistema de monitoreo de servidores profesional, moderno y seguro. Diseñado para proporcionar visibilidad completa sobre la infraestructura con una experiencia de usuario intuitiva.

## 🚀 Características Principales

- **Dashboard Moderno**: Interfaz responsive construida con Vue 3 y TailwindCSS.
- **Visualización de Datos**: Gráficos interactivos (Chart.js) para CPU, RAM y Disco.
- **Filtrado y Exportación**: Filtros por tiempo y grupo, exportación a CSV/JSON.
- **Alertas Inteligentes**: Notificaciones por correo (SMTP) con umbrales configurables.
- **Seguridad Robusta**: Autenticación JWT, gestión de roles y auditoría de acciones.
- **Arquitectura Escalable**: Backend FastAPI asíncrono y base de datos optimizada.

## 🛠 Stack Tecnológico

- **Frontend**: 
  - Vue.js 3 (Composition API)
  - TailwindCSS (Diseño)
  - Chart.js / vue-chartjs (Gráficos)
  - Axios (Cliente HTTP)
- **Backend**: 
  - Python 3.10+
  - FastAPI (API REST)
  - SQLAlchemy (ORM)
  - Pydantic (Validación)
- **Infraestructura**:
  - SQLite (Base de datos por defecto)
  - Docker / PM2 / Systemd (Despliegue)

## 📦 Instalación

### Prerrequisitos
- Python 3.10 o superior
- Node.js 18 o superior
- Git

### 🚀 Despliegue Rápido (Recomendado)

Simplemente ejecuta el script de despliegue correspondiente a tu sistema operativo. Este script configurará el entorno, instalará dependencias, construirá el frontend e iniciará el servidor.

**Linux / macOS:**
```bash
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

### Instalación Manual (Paso a Paso)

### 1. Preparación del Entorno
```bash
git clone <repository-url>
cd monitor-integral
```

### 2. Configuración del Backend
```bash
cd src/server
python -m venv .venv

# Linux/Mac
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configuración del Frontend
```bash
cd src/client
npm install
npm run build  # Genera los archivos estáticos en dist/
```

## 🚀 Despliegue en Producción

### Opción A: PM2 (Node.js Process Manager)
Ideal para entornos que ya usan Node.js.

1. Instalar PM2: `npm install -g pm2`
2. Iniciar el ecosistema:
   ```bash
   pm2 start ecosystem.config.js
   ```
3. Configurar inicio automático:
   ```bash
   pm2 save
   pm2 startup
   ```

### Opción B: Systemd (Linux Service)
Para integración nativa con el sistema operativo.

1. Ajustar rutas en `deploy/systemd/monitor-backend.service`.
2. Instalar el servicio:
   ```bash
   sudo cp deploy/systemd/monitor-backend.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now monitor-backend
   ```

### Opción C: Docker
Despliegue contenerizado completo.

```bash
docker-compose up -d --build
```

## 📡 Agente de Monitoreo

El agente es un pequeño servicio en Python que se instala en cada servidor (Linux o Windows / Windows Server) y envía métricas al backend.

### Instalación automática recomendada

La forma más sencilla de desplegar el agente en cualquier servidor es mediante los instaladores automáticos multiplataforma.

1. Copia la carpeta `agent/` a tu servidor (por ejemplo con `scp` o `WinSCP`).
2. En el servidor, entra a la carpeta del agente:
   ```bash
   cd agent/python
   ```
3. Ejecuta según el sistema operativo:
   - **Linux / Linux Server / macOS** (instalación automática y desatendida):
     ```bash
     chmod +x install.sh
     sudo ./install.sh
     ```
     Opcionalmente puedes especificar la URL del backend:
     ```bash
     sudo ./install.sh --server http://mi-servidor-monitor.com
     ```
   - **Windows / Windows Server** (PowerShell como Administrador):
     ```powershell
     .\install.ps1
     # o indicando el servidor
     .\install.ps1 -Server "http://mi-servidor-monitor.com"
     ```

### Instalación rápida clásica

Si prefieres usar los scripts rápidos originales:

1. En el servidor, entra a la carpeta del agente:
   ```bash
   cd agent/python
   ```
2. Ejecuta según el sistema operativo:
   - **Linux / Linux Server**:
     ```bash
     bash quick_install.sh
     ```
   - **Windows / Windows Server** (desde una consola en `agent\python`):
     ```bat
     quick_install.bat
     ```
4. El instalador:
   - Verifica dependencias.
   - Comprueba `/api/health`.
   - Registra el servidor en `/api/register`.
   - Crea `agent.config.json` con la configuración.

Para más detalles avanzados (configuración manual, pruebas de carga, ejecución como servicio y opciones de instalación automática), consulta:
- [`agent/README.md`](agent/README.md)
- [`agent/python/README.md`](agent/python/README.md)

## 🛡 Seguridad

- **Credenciales**: Nunca use credenciales por defecto en producción. Cambie la contraseña de administrador inmediatamente.
- **Variables de Entorno**: Configure `ENCRYPTION_KEY` y `DASHBOARD_TOKEN` en un archivo `.env` seguro.
- **HTTPS**: Se recomienda encarecidamente usar un proxy inverso (Nginx/Apache) con SSL para exponer el servicio.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.
