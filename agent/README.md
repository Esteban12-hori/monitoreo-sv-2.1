# Agente de Monitoreo de Servidores

Este directorio contiene el agente ligero en Python que se instala en cada servidor (Linux o Windows / Windows Server) para enviar métricas al sistema de monitoreo web.

Compatibilidad:
- Linux (incluyendo distribuciones orientadas a servidor)
- Windows y Windows Server con Python instalado

## 🚀 Instalación Automática Recomendada

La forma más sencilla y robusta de instalar el agente en un servidor es usando los instaladores automáticos multiplataforma. Estos scripts se apoyan en `install.py`, leen la configuración por defecto y dejan el agente listo para ejecutarse como servicio o tarea programada.

### 1. Preparar archivos en el servidor

1. Copia la carpeta `agent/` a tu servidor (por ejemplo usando `scp` o `WinSCP`).
2. En el servidor, sitúate dentro de la carpeta del agente:

```bash
cd agent/python
```

### 2. Linux / Linux Server / macOS

En la carpeta `agent/python` ejecuta:

```bash
chmod +x install.sh
sudo ./install.sh
```

Opcionalmente puedes indicar la URL del backend de monitoreo:

```bash
sudo ./install.sh --server http://mi-servidor-monitor.com
```

El script:
- Detecta el sistema operativo y arquitectura.
- Verifica Python 3 e instala dependencias desde `requirements.txt`.
- Llama a `install.py` en modo automático (`--auto`) para registrar el servidor y crear `agent.config.json`.
- Intenta configurar un servicio `systemd` usando `setup_service.sh` en Linux.

En macOS se realiza la configuración básica y se deja el agente listo para ejecución manual.

### 3. Windows / Windows Server

1. Abre **PowerShell como Administrador**.
2. Navega a la carpeta `agent\python`:

```powershell
cd C:\ruta\al\agent\python
```

3. Ejecuta el instalador:

```powershell
.\install.ps1
# o indicando el servidor de monitoreo:
.\install.ps1 -Server "http://mi-servidor-monitor.com"
```

El script:
- Verifica que se está ejecutando con permisos de administrador.
- Comprueba que Python está disponible en el PATH.
- Instala dependencias desde `requirements.txt`.
- Ejecuta `install.py` en modo automático.
- Crea una **Tarea Programada** llamada `MonitoreoAgent` que se ejecuta al iniciar el sistema como usuario `SYSTEM`.

## ⚡ Instalación rápida clásica

Si prefieres una instalación más simple basada en los scripts rápidos originales, puedes usarlos así:

### Linux (incluido Linux Server)

En la carpeta `agent/python` ejecuta:

```bash
bash quick_install.sh
```

Este script:
- Instala las dependencias del agente (psutil, requests, etc.).
- Comprueba la salud del backend en `/api/health`.
- Registra el servidor en `/api/register`.
- Crea el archivo `agent.config.json` con la configuración.

### Windows / Windows Server

En la carpeta `agent\python` del servidor ejecuta el script:

```bat
quick_install.bat
```

Este script realiza los mismos pasos que en Linux, pero usando `python` en Windows.

> Asegúrate de tener Python 3 instalado y accesible en el PATH del sistema.

## ▶️ Ejecución del agente

El archivo principal del agente es `agent.py`. Una vez creada la configuración, puedes ejecutarlo así:

```bash
cd agent/python
python agent.py --config agent.config.json
```

Si quieres pasar parámetros manualmente:

```bash
python agent.py \
  --server https://mi-dominio \
  --server-id srv-01 \
  --token TOKEN \
  --interval 60 \
  --verify /ruta/a/ca.crt
```

## 🧪 Scripts útiles

Desde `agent/python` dispones de:

- `diagnose.py`: comprueba `/api/health` y envía una métrica de prueba.
- `local_test_runner.py`: genera métricas de prueba con distintos escenarios de carga.

Ejemplo de diagnóstico rápido:

```bash
cd agent/python
python diagnose.py
```

## 📓 Más detalles

En [`agent/python/README.md`](./python/README.md) encontrarás una guía más extensa sobre:
- Configuración manual del `agent.config.json`.
- Uso de `local_test_runner.py` para pruebas de carga.
- Ejecución del agente como servicio en Linux mediante systemd.
