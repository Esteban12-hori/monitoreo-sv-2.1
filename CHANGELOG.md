# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-06-18

### Added
- **Gestión Proxmox (sin API HTTP)**: nuevo panel de administración (`/admin/proxmox`) que opera nodos Proxmox VE ejecutando los CLI nativos (`qm`, `pct`, `vzdump`, `wg`) por **SSH**:
  - Modificación de recursos hardware (cores/memoria/disco) de VMs (qemu) y contenedores (LXC).
  - **Snapshots**: creación, listado, restauración (rollback) y borrado.
  - **Backups programados** con APScheduler (cron) y **autodetección de servidores de base de datos** a partir de los servicios monitoreados; ejecución manual e historial.
  - **Migración entre nodos** por un **túnel WireGuard** cifrado (ChaCha20-Poly1305): `vzdump` → transferencia por el túnel → restore, sin depender de la API de Proxmox.
- **Endpoints** `/api/proxmox/*` (solo admin, con auditoría) y nuevos modelos (`ProxmoxNode`, `ProxmoxGuest`, `BackupSchedule`, `BackupJob`, `NodeLink`, `SnapshotRecord`).
- **Pruebas funcionales** (`tests/test_proxmox.py`) con SSH/WireGuard mockeados, incluyendo casos de prevención de inyección de comandos.
- Documentación: `docs/proxmox.md` y sección en el README.

### Security
- Credenciales SSH y claves privadas WireGuard cifradas en reposo (Fernet).
- Validación estricta de entradas (anti command-injection) y verificación de host key SSH (TOFU).

### Fixed
- `SMTPConfigResponse` ya no expone el campo `password`; `use_ssl`/`use_tls` tienen valores por defecto.

## [2.0.0] - 2026-01-14

### Added
- **UI/UX Redesign**: Complete overhaul of the frontend using TailwindCSS for a modern, responsive design.
- **Charts**: Interactive charts using Chart.js for CPU, Memory, and Disk metrics.
- **Filtering**: Added time range (1h, 6h, 24h) and server group filtering to the Dashboard.
- **Export**: Added functionality to export metrics data to CSV and JSON formats.
- **Deployment**: Added `ecosystem.config.js` for PM2 and `monitor-backend.service` for Systemd deployment.
- **Security**: Implemented secure session handling with `X-Dashboard-Token` headers and removed legacy hardcoded credentials.

### Changed
- **Architecture**: Refactored project structure to separate `src/client` (Frontend) and `src/server` (Backend).
- **Authentication**: Migrated all authentication to database-backed users. Removed `ALLOWED_USERS` config.
- **Performance**: Optimized metric polling and rendering.

### Fixed
- **Security**: Eliminated exposure of sensitive credentials in source code.
- **Stability**: Improved error handling in metric ingestion and history endpoints.

## [1.0.0] - Initial Release
- Basic monitoring functionality.
- Simple dashboard.
- SQLite database integration.
