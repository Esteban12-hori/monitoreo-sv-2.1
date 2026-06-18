# 🖥️ Gestión Proxmox

El módulo de gestión Proxmox permite **operar** la infraestructura (no solo
monitorizarla) desde el panel `/admin/proxmox`. Está implementado **sin usar la
API HTTP de Proxmox**: el backend se conecta por **SSH** a cada nodo y ejecuta
los CLI nativos (`qm`, `pct`, `vzdump`, `pvesm`, `wg`).

## Funcionalidades

| # | Capacidad | Implementación |
|---|-----------|----------------|
| 1 | Modificar recursos hardware de VMs/LXC | `qm set` / `pct set` (cores, memoria) y `qm/pct resize` (disco) |
| 2 | Backups programados de servidores de BD | `vzdump` planificado con **APScheduler** (cron) + autodetección de BD |
| 3 | Snapshots de cualquier VM/LXC | `qm/pct snapshot · listsnapshot · rollback · delsnapshot` |
| 4 | Migración entre nodos por túnel cifrado | **WireGuard** + `vzdump → transferencia por el túnel → qmrestore/pct restore` |

## Modelo de seguridad

- **Solo administradores** pueden acceder a los endpoints `/api/proxmox/*`.
- **Credenciales cifradas en reposo** (Fernet, `ENCRYPTION_KEY`): contraseñas/claves
  SSH y claves privadas WireGuard. Nunca se devuelven en las respuestas de la API.
- **Prevención de inyección de comandos**: toda entrada se valida de forma
  estricta (vmid numérico; nombres `[A-Za-z0-9_.-]`; recursos con rango) y los
  comandos se construyen como listas de argumentos con `shlex.quote`. Las
  entradas peligrosas se rechazan con HTTP 422 **antes** de ejecutar nada.
- **Verificación de host key SSH (TOFU)**: la huella SHA256 del nodo se registra
  al darlo de alta; si cambia, la conexión se aborta (posible MITM).
- **Auditoría**: cada operación mutante queda registrada en `audit_logs`.

## Autodetección de servidores de base de datos

Los backups con `only_db = true` se aplican únicamente a los guests detectados
como bases de datos. La detección reutiliza los **servicios y procesos que el
agente ya reporta** (tabla `metrics`): se buscan firmas como `postgres`,
`mysqld`/`mariadb`, `mongod`, `redis`, `sqlservr`, `oracle`, y puertos típicos
(5432, 3306, 27017, 6379, 1433, 1521…). Un guest se asocia a un servidor
monitoreado por nombre (auto-vínculo al sincronizar, con override manual).

## Migración por túnel WireGuard

1. Se establece un túnel WireGuard `/30` entre el nodo origen y el destino
   (claves Curve25519 generadas por el backend; las privadas se guardan cifradas).
2. La migración hace `vzdump` en origen, transfiere el archivo al destino **por
   la IP del túnel** (rsync sobre SSH nodo→nodo) y restaura con
   `qmrestore`/`pct restore`. Todo el tráfico de datos viaja cifrado dentro del
   túnel (ChaCha20-Poly1305), garantizando confidencialidad e integridad.

## Requisitos en los nodos Proxmox

- Acceso SSH para el usuario configurado, con permiso para ejecutar
  `qm`, `pct`, `vzdump`, `pvesm` y `wg`/`wg-quick` (root, o `sudo` — marca
  "Usar sudo" al registrar el nodo).
- Paquete `wireguard-tools` instalado (para los túneles de migración).
- Para la migración: conectividad de red entre los nodos por el puerto WireGuard
  (por defecto UDP `51830`) y SSH nodo→nodo sobre la IP del túnel.

## Variables de entorno

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `ENCRYPTION_KEY` | — (obligatoria en producción) | Clave Fernet para cifrar secretos |
| `WG_TUNNEL_PREFIX` | `10.99.99` | Prefijo /24 del que se toma la /30 del túnel |
| `WG_LISTEN_PORT` | `51830` | Puerto UDP de WireGuard |

## Endpoints principales

```
POST   /api/proxmox/nodes                      Registrar nodo
POST   /api/proxmox/nodes/{id}/test            Probar SSH
POST   /api/proxmox/nodes/{id}/sync            Sincronizar inventario de guests
PUT    /api/proxmox/guests/{id}/resources      Modificar recursos hardware
GET/POST/.../snapshots                         Gestionar snapshots
GET/POST/PUT/DELETE /api/proxmox/backup-schedules   Programaciones de backup
POST   /api/proxmox/backups/run                Backup manual
POST   /api/proxmox/links                      Establecer túnel WireGuard
POST   /api/proxmox/migrate                    Migrar guest por el túnel
```

## Pruebas

`tests/test_proxmox.py` cubre validación/inyección, autorización, recursos,
snapshots, backups (incluida la regla "solo BD"), autodetección y migración. La
capa SSH/WireGuard se mockea (no requiere un Proxmox real):

```bash
PYTHONPATH=. ENV=testing pytest tests/test_proxmox.py -v
```
