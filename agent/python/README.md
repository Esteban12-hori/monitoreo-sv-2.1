# Agente de Monitoreo

Este agente es un script ligero en Python diseñado para recolectar métricas del sistema (CPU, RAM, Disco, Docker) y enviarlas a un servidor central de monitoreo.

## 🚀 Características
- **Ligero**: Consume mínimos recursos.
- **Intervalo Configurable**: Por defecto envía datos cada **40 minutos** (2400 segundos), pero es ajustable.
- **Seguro**: Autenticación mediante Tokens y soporte para TLS/SSL.
- **Métricas**:
  - Uso de CPU (Total y por núcleo).
  - Uso de Memoria RAM.
  - Uso de Disco.
  - Estado de contenedores Docker (si está instalado).

---

## 📦 Instalación y Configuración

Existen dos formas de instalar el agente:

### Opción A: Instalación Automática (Recomendada)
El script `install.py` te guiará paso a paso para instalar dependencias, registrar el servidor y crear la configuración.

1. Abre una terminal en la carpeta del agente:
   ```bash
   cd agent/python
   ```
2. Ejecuta el instalador:
   ```bash
   python install.py
   ```
3. Sigue las instrucciones en pantalla:
   - Ingresa la URL de tu servidor (ej: `http://20.153.165.55`).
   - Asigna un nombre a este servidor (ej: `servidor-produccion-01`).
   - El instalador guardará el token automáticamente.

### Opción B: Configuración Manual
Si prefieres configurar todo manualmente o automatizarlo con scripts:

1. **Instalar Dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
   *(O manualmente: `pip install requests psutil`)*

2. **Registrar el Agente** (Obtener Token):
   Ejecuta este comando para obtener tu token de acceso desde el servidor:
   ```bash
   curl -X POST http://TU_IP_SERVIDOR/api/register \
        -H "Content-Type: application/json" \
        -d "{\"server_id\": \"NOMBRE_DE_TU_SERVIDOR\"}"
   ```
   Copia el `token` que recibirás en la respuesta JSON.

3. **Crear Archivo de Configuración**:
   Crea un archivo llamado `agent.config.json` en la misma carpeta que `agent.py` con el siguiente contenido:
   ```json
   {
     "server": "http://TU_IP_SERVIDOR",
     "server_id": "NOMBRE_DE_TU_SERVIDOR",
     "token": "PEGA_AQUI_TU_TOKEN",
     "interval": 2400,
     "verify": ""
   }
   ```
   - `interval`: Tiempo en segundos entre reportes (2400s = 40 minutos).
   - `verify`: Ruta al certificado SSL (déjalo vacío `""` para HTTP o HTTPS estándar).

---

## ▶️ Ejecución

Para iniciar el agente simplemente ejecuta:

```bash
python agent.py
```

Deberías ver un mensaje indicando que el agente ha iniciado. El script se mantendrá en ejecución enviando datos cada 40 minutos.

---

## 🧪 Pruebas locales de métricas (modo standalone)

Para hacer pruebas locales sin depender de entornos externos puedes usar el simulador `local_test_runner.py`, que:
- Registra servidores de prueba en el backend.
- Genera métricas realistas en varios escenarios.
- Envía solo métricas (sin login ni autenticación de usuario).
- Valida automáticamente que las métricas se almacenen en el backend.

### Requisitos previos

- Backend de monitoreo ejecutándose en `http://localhost:8000` (por ejemplo con `python -m uvicorn src.server.app.main:app --reload --port 8000` o `docker-compose up` en la raíz del proyecto).
- Dependencias del agente instaladas:

```bash
cd agent/python
pip install -r requirements.txt
```

### Ejecutar simulación local básica

Desde `agent/python`:

```bash
python local_test_runner.py
```

Esto lanzará por defecto:
- 3 servicios simulados (`local-test-service-1`, `-2`, `-3`).
- Intervalo de envío de 5 segundos.
- 60 muestras por servicio.
- Escenario de carga `normal`.

Las métricas se envían a `http://localhost:8000/api/metrics` y el script genera un log detallado en `agent/python/logs/local_test.log`.

Al finalizar, el script consulta `/api/metrics/history` para cada servicio y verifica que se hayan almacenado suficientes muestras, fallando si algo no es consistente.

### Parámetros de configuración de la simulación

Ejemplo con parámetros personalizados:

```bash
python local_test_runner.py \
  --server http://localhost:8000 \
  --services 5 \
  --interval 2 \
  --iterations 120 \
  --scenario stress-cpu
```

Parámetros principales:
- `--server`: URL del backend (por defecto `http://localhost:8000`).
- `--services`: cantidad de servicios simulados.
- `--interval`: intervalo de envío en segundos.
- `--iterations`: número de muestras por servicio.
- `--scenario`: patrón de carga:
  - `normal`
  - `stress-cpu`
  - `memory-leak`
  - `io-spikes`

TLS:
- `--verify`: ruta a CA/cert o `false` para desactivar la verificación TLS.

### Formato y estructura de las métricas

El simulador envía exactamente la misma estructura que el agente real, por ejemplo:

```json
{
  "server_id": "local-test-service-1",
  "memory": {
    "total": 8192.0,
    "used": 4096.0,
    "free": 4096.0,
    "cache": 819.2
  },
  "cpu": {
    "total": 35.0,
    "per_core": [32.0, 36.0, 34.0, 38.0]
  },
  "disk": {
    "total": 256.0,
    "used": 128.0,
    "free": 128.0,
    "percent": 50.0
  },
  "docker": {
    "running_containers": 1,
    "containers": [
      { "name": "service-1-main" }
    ]
  },
  "timestamp": "2026-01-14T09:30:00Z"
}
```

Reglas clave que se validan automáticamente antes de enviar:
- `0 <= cpu.total <= 100`
- Cada entrada de `cpu.per_core` está entre 0 y 100.
- `memory.total > 0` y `memory.used <= memory.total`.
- `0 <= disk.percent <= 100`.

Si alguna métrica generada viola estas reglas, el simulador falla inmediatamente, lo que permite detectar errores de generación antes de impactar al backend.

### Escenarios de prueba sugeridos

Algunos ejemplos de uso para pruebas locales:

1. **Escenario base estable**
   ```bash
   python local_test_runner.py --scenario normal --services 2 --interval 5 --iterations 60
   ```
   Ideal para validar el flujo completo de métricas y el panel en tiempo real.

2. **Prueba de alertas por CPU alta**
   ```bash
   python local_test_runner.py --scenario stress-cpu --services 3 --interval 3 --iterations 80
   ```
   Genera cargas altas de CPU para disparar alertas y revisar el histórico.

3. **Fuga de memoria progresiva**
   ```bash
   python local_test_runner.py --scenario memory-leak --services 1 --interval 5 --iterations 120
   ```
   Útil para ver tendencias ascendentes en memoria en el dashboard.

4. **Picos de I/O y disco**
   ```bash
   python local_test_runner.py --scenario io-spikes --services 2 --interval 2 --iterations 100
   ```
   Simula picos periódicos de disco y uso combinado de recursos.

Con estos comandos puedes probar de forma exhaustiva el flujo de métricas, el panel en tiempo real y el histórico, manteniendo siempre el principio de que el agente y el simulador solo envían métricas y no implementan login ni autenticación de usuario.

### 🖥️ Ejecutar en Segundo Plano (Modo Servicio)

Para que el agente se inicie automáticamente con el sistema y corra en segundo plano (sin dejar la terminal abierta):

#### Linux (Automático)

Hemos incluido un script que hace todo el trabajo por ti:

1. Asegúrate de estar en la carpeta `agent/python`:
   ```bash
   cd agent/python
   ```
2. Ejecuta el script de instalación del servicio:
   ```bash
   bash setup_service.sh
   ```
   Este script verificará la configuración (o te pedirá crearla) y configurará systemd automáticamente.

#### Linux (Manual - Systemd)
Si prefieres hacerlo manualmente:

1. Crea el archivo de servicio:
   ```bash
   sudo nano /etc/systemd/system/monitoreo-agent.service
   ```

2. Pega el siguiente contenido (ajusta las rutas según donde descargaste el agente):
   ```ini
   [Unit]
   Description=Agente de Monitoreo
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/ruta/a/tu/carpeta/agent/python
   ExecStart=/usr/bin/python3 /ruta/a/tu/carpeta/agent/python/agent.py
   Restart=always
   RestartSec=60

   [Install]
   WantedBy=multi-user.target
   ```

3. Activa e inicia el servicio:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable monitor-agent
   sudo systemctl start monitor-agent
   ```

#### Windows (Sin ventana)
Para ejecutarlo sin que aparezca la ventana negra de la terminal, usa `pythonw` en lugar de `python`.

1. **Opción Rápida**:
   ```powershell
   Start-Process -WindowStyle Hidden -FilePath "pythonw" -ArgumentList "agent.py"
   ```

2. **Opción Permanente (Inicio de Windows)**:
   - Crea un acceso directo al archivo `agent.py`.
   - Haz clic derecho en el acceso directo -> Propiedades.
   - En "Destino", cambia `python.exe` por `pythonw.exe`.
   - Mueve este acceso directo a la carpeta de Inicio (`Win + R` y escribe `shell:startup`).

#### Linux/MacOS (Alternativa con PM2)
Si prefieres usar un gestor de procesos moderno como PM2 (requiere Node.js):

1. **Instalar PM2**:
   ```bash
   npm install -g pm2
   ```

2. **Iniciar el Agente**:
   ```bash
   pm2 start agent.py --name monitor-agent --interpreter python3
   ```

3. **Comandos Útiles**:
   - Ver estado: `pm2 status`
   - Ver logs: `pm2 logs monitor-agent`
   - Reiniciar: `pm2 restart monitor-agent`
   - Detener: `pm2 stop monitor-agent`

4. **Persistencia (Inicio automático)**:
   ```bash
   pm2 save
   pm2 startup
   ```
   *(Copia y pega el comando que te muestre la terminal para finalizar).*

---

## 🛠️ Solución de Problemas

- **Error de conexión**: Verifica que la URL en `agent.config.json` sea correcta y que el servidor sea accesible desde esta máquina.
- **Falta de permisos**: Si no detecta Docker o Discos, intenta ejecutarlo como Administrador o con `sudo`.
- **Cambiar intervalo**: Edita el valor `"interval"` en `agent.config.json` y reinicia el agente.
