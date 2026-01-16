# Guía de Instalación del Agente de Monitoreo

Este documento describe cómo instalar y configurar el Agente de Monitoreo en servidores Linux, macOS y Windows.

## Requisitos Previos

- **Sistema Operativo**:
  - Linux (Ubuntu, Debian, CentOS, RHEL, etc.)
  - macOS
  - Windows 10/11 o Windows Server 2016+
- **Python**: Versión 3.8 o superior instalada.
- **Red**: Acceso HTTP/HTTPS al servidor de monitoreo.

## Estructura de Archivos

El paquete de instalación incluye:
- `install.sh`: Script de instalación para Linux/macOS.
- `install.ps1`: Script de instalación para Windows (PowerShell).
- `config.default.json`: Archivo de configuración predeterminada.
- `install.py`: Script interno de configuración.
- `requirements.txt`: Dependencias de Python.

---

## Configuración Automática

Antes de instalar, puedes editar el archivo `config.default.json` para predefinir la configuración y realizar una instalación desatendida.

**Ejemplo de `config.default.json`:**
```json
{
  "server": "http://20.153.165.55",
  "interval": 60,
  "server_id": "servidor-produccion-01"
}
```
- `server`: URL del servidor donde se enviarán las métricas.
- `interval`: Frecuencia de envío en segundos (defecto: 60).
- `server_id`: (Opcional) Identificador único del servidor. Si se omite, se usa el nombre del host.

---

## Instalación en Linux / macOS

1.  **Abrir terminal** y navegar al directorio del agente:
    ```bash
    cd agent/python
    ```

2.  **Dar permisos de ejecución**:
    ```bash
    chmod +x install.sh
    ```

3.  **Ejecutar el instalador**:
    ```bash
    # Instalación estándar (usa config.default.json)
    sudo ./install.sh

    # O especificar servidor manualmente
    sudo ./install.sh --server http://mi-servidor.com
    ```

**Nota**: Se recomienda usar `sudo` para que el script pueda configurar el servicio `systemd` automáticamente.

---

## Instalación en Windows / Windows Server

1.  **Abrir PowerShell como Administrador**.

2.  **Navegar al directorio del agente**:
    ```powershell
    cd C:\ruta\al\agent\python
    ```

3.  **Ejecutar el script**:
    ```powershell
    # Instalación estándar (usa config.default.json)
    .\install.ps1

    # O especificar servidor manualmente
    .\install.ps1 -Server "http://mi-servidor.com"
    ```

El script configurará una **Tarea Programada** llamada `MonitoreoAgent` que se ejecutará automáticamente al iniciar el sistema (como SYSTEM).

---

## Verificación Post-Instalación

### Linux
Verificar el estado del servicio:
```bash
sudo systemctl status monitoreo-agent.service
```

Verificar logs:
```bash
tail -f install.log
journalctl -u monitoreo-agent.service -f
```

### Windows
Verificar la tarea programada:
```powershell
Get-ScheduledTask -TaskName MonitoreoAgent
```

Verificar si el proceso está corriendo:
```powershell
Get-Process python*
```

Revisar logs en el archivo `install.log` dentro del directorio.

## Solución de Problemas

- **Error de permisos**: Asegúrate de ejecutar con `sudo` (Linux) o "Ejecutar como Administrador" (Windows).
- **Python no encontrado**: Instala Python 3.8+ y asegúrate de marcar "Add Python to PATH" durante la instalación en Windows.
- **Fallo de conexión**: Verifica que la URL del servidor en `config.default.json` sea accesible desde el servidor agente (`curl -v URL`).
