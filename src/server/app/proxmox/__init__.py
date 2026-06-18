"""
Paquete de gestión Proxmox.

Implementa operaciones sobre nodos Proxmox VE ejecutando los CLI nativos
(qm, pct, vzdump, pvesm, wg) por SSH, sin depender de la API HTTP de Proxmox.

Submódulos:
- validators:   validación estricta de entradas (anti command-injection)
- ssh_executor: único punto que ejecuta comandos por SSH (mockeable en tests)
- service:      operaciones de alto nivel (recursos, snapshots, inventario, backups)
- dbdetect:     autodetección de guests de base de datos vía servicios monitoreados
- wireguard:    túnel cifrado y migración entre nodos
- scheduler:    programación de backups con APScheduler
"""
