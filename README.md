# 📊 UpKeep

<div align="center">
  <img src="src/client/src/assets/logo.png" alt="UpKeep Logo" width="120" />
</div>

Sistema de monitoreo de servidores profesional, moderno y fácil de desplegar. Diseñado para proporcionar visibilidad completa sobre tu infraestructura con una experiencia de usuario intuitiva.

## 🚀 Características Principales

- **Dashboard Moderno**: Interfaz responsive construida con Vue 3 y TailwindCSS (Soporte Dark Mode).
- **Detección de SO**: Identificación automática de Linux/Windows basada en procesos activos.
- **Métricas en Tiempo Real**: CPU, RAM, Disco, Red y estado de servicios (Docker, Redis, etc.).
- **Agente Ligero**: Agente en Python optimizado con instalación interactiva fácil.
- **Alertas Inteligentes**: Notificaciones SMTP configurables.
- **Seguridad**: Autenticación basada en tokens de sesión (persistidos en BD, con expiración configurable) y gestión de roles.
- **Fácil Despliegue**: Soporte completo para Docker y scripts de instalación automatizados.

## 🧩 Personalización por Usuario (Nuevo)

- **Umbrales Personales**: Cada usuario puede configurar sus propios límites de alerta para CPU, RAM y Disco.
- **Suscripción Selectiva**: Activa o desactiva alertas para servidores específicos sin afectar a otros usuarios.
- **Preferencias de visualización**: Tema, tipo de gráficos, idioma.
- **Vistas guardadas**: (por ejemplo: “vista nocturna”, “solo producción”).

## 🌐 Sistema de Agentes Distribuido

- Agentes instalables en Linux y Windows.
- Envío automático y periódico de métricas al servidor central.
- Comunicación segura mediante TLS y tokens por agente.
- Soporte para métricas personalizadas a través de plugins.

## 🚨 Alertas Avanzadas y Escalables

- Triggers configurables (por ejemplo: CPU > 80 % durante 5 min, disco < 10 %).
- Niveles de severidad: informativo, advertencia y crítico.
- Escalado de alertas si no hay respuesta (otro canal o destinatario).
- Historial de alertas, estado y ACK (alertas reconocidas).

## 📣 Notificaciones Multicanal

- Email mejorado con plantillas y pruebas desde el panel.
- Integraciones planeadas: Telegram, Discord, Slack.
- Webhooks para integrarse con otros sistemas.
- Integración con sistemas de tickets (roadmap).

## 📈 Dashboards Avanzados

- Widgets configurables: gráficos, tablas, estados y mapas.
- Comparación histórica (día vs semana vs mes).
- Vistas por servidor, servicio y entorno (producción / desarrollo / test).
- Mapas visuales de infraestructura.

## 🏗 Arquitectura Escalable

- Soporte actual en SQLite con roadmap hacia PostgreSQL/MariaDB.
- Separación lógica de servicios: API, colector y frontend.
- Preparado para crecer a cientos o miles de hosts.

## 📚 Histórico y Análisis de Datos

- Retención de métricas configurable.
- Agregaciones de datos (promedios, máximos, picos).
- Exportación de datos a CSV y JSON.

## 🧩 Monitoreo de Servicios

- Servicios de infraestructura: Nginx, Apache, bases de datos y Redis.
- Contenedores Docker y puertos TCP/HTTP.
- Estados de servicios del sistema.

## 🌐 Monitoreo de Red

- Latencia mediante ping.
- Tráfico por interfaz de red.
- Paquetes perdidos y métricas vía SNMP para switches y routers.

## 📡 Monitoreo agentless y Notificaciones (Nuevo)

Panel `/admin/monitoring` (admin):

- **Checks agentless**: monitoriza endpoints **HTTP/TCP/ICMP** desde el propio
  servidor, sin instalar agente en el destino. Configurables desde la UI, con
  ejecución programada, estado/latencia e historial.
- **Canales de notificación**: Slack, Discord, Telegram y webhook genérico que
  reciben las alertas además del correo (secretos cifrados; botón de prueba).
- **Retención de datos**: purga automática (diaria) y manual de históricos.
  Variables: `METRICS_RETENTION_DAYS` (def. 30) y `CHECK_RESULTS_RETENTION_DAYS`.

## 🖥️ Gestión Proxmox (Nuevo)

Operación de infraestructura Proxmox VE desde el panel `/admin/proxmox`, **sin
usar la API HTTP**: el backend ejecuta los CLI nativos (`qm`, `pct`, `vzdump`,
`wg`) por SSH. Ver la [documentación completa](docs/proxmox.md).

- **Recursos hardware**: modifica cores/memoria/disco de VMs (qemu) y contenedores (LXC).
- **Snapshots**: crea, lista, restaura (rollback) y elimina instantáneas de cualquier guest.
- **Backups programados**: `vzdump` con cron (APScheduler) y **autodetección de
  servidores de base de datos** a partir de los servicios monitoreados.
- **Migración segura**: vincula nodos mediante un **túnel WireGuard** cifrado y
  migra cargas de trabajo (vzdump → transferencia por el túnel → restore),
  garantizando confidencialidad e integridad de los datos.

> Seguridad: solo admin, credenciales y claves privadas cifradas (Fernet),
> validación estricta anti-inyección, verificación de host key SSH (TOFU) y
> auditoría de todas las operaciones.

## 🔐 Seguridad y Control de Acceso

- Roles definidos: Admin, Operador y Usuario.
- Permisos por servidor y entorno.
- Tokens dedicados por agente.
- Auditoría de cambios (quién hizo qué y cuándo).

## 🛠 Stack Tecnológico

- **Frontend**: Vue 3, TailwindCSS, Chart.js, Vite.
- **Backend**: Python FastAPI, SQLAlchemy, SQLite (por defecto).
- **Agente**: Python (psutil, requests).
- **Infraestructura**: Docker, Docker Compose, Nginx.

---

## 📥 Descarga y Actualización

### Descargar por primera vez
Para obtener la última versión del proyecto, clona el repositorio:

```bash
git clone <URL_DEL_REPOSITORIO>
cd upkeep
```

### Actualizar a la última versión
Si ya tienes el proyecto descargado y quieres actualizarlo:

```bash
# 1. Obtener los últimos cambios
git pull origin main

# 2. Actualizar dependencias del Backend (desde la raíz del repositorio)
pip install -r src/server/requirements.txt

# 3. Aplicar migraciones de base de datos (si las hay)
PYTHONPATH=. python src/server/scripts/migrate_db.py  # o el script correspondiente

# 4. Actualizar dependencias del Frontend
cd src/client
npm install
npm run build
```

---

## 🐳 Despliegue Rápido (Docker Compose) - ¡Recomendado!

La forma más sencilla de iniciar el servidor (Backend + Frontend).

1. **Requisitos**: Tener Docker y Docker Compose instalados.
2. **Ejecutar**:
   ```bash
   docker-compose up -d --build
   ```
3. **Acceder**:
   - Frontend: `http://localhost` (o el puerto configurado)
   - Backend API: `http://localhost:8000/docs`

## 🔧 Instalación Manual (Desarrollo)

### Backend
> El backend importa `config.settings` desde la raíz del proyecto, por lo que
> debe ejecutarse **desde la raíz del repositorio** (con `PYTHONPATH=.`), no desde `src/server`.

```bash
# Desde la raíz del repositorio
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r src/server/requirements.txt

# Iniciar el servidor (el módulo es una app FastAPI, se sirve con uvicorn)
PYTHONPATH=. uvicorn src.server.app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Variables de entorno recomendadas en producción:**
> - `ENV=production`
> - `ENCRYPTION_KEY` (obligatoria en producción; genérala con
>   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
> - `ALLOWED_ORIGINS` (dominios concretos del frontend, separados por comas)
> - `ALLOWED_HOSTS` (hosts permitidos, separados por comas)
> - `SESSION_TTL_HOURS` (vida de las sesiones; por defecto 168 = 7 días)
> - `ADMIN_EMAIL` / `ADMIN_PASSWORD` (para el admin inicial; se forzará el cambio de contraseña en el primer login)
> - `WG_TUNNEL_PREFIX` / `WG_LISTEN_PORT` (túnel WireGuard de migración Proxmox; ver [docs/proxmox.md](docs/proxmox.md))
> - `METRICS_RETENTION_DAYS` / `CHECK_RESULTS_RETENTION_DAYS` (retención de históricos; por defecto 30 días)

### Frontend
```bash
cd src/client
npm install
npm run dev
```
