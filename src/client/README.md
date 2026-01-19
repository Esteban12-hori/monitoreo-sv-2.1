# UpKeep – Frontend (Panel Web)

Este directorio contiene la aplicación web (dashboard) del sistema de monitoreo de servidores **UpKeep**.

## 🌐 ¿Qué ofrece el panel web?

- Vista general de todos los servidores monitoreados.
- Gráficas en tiempo real de:
  - CPU
  - Memoria RAM
  - Disco
  - Contenedores Docker (cuando están disponibles)
- Filtros por grupo/proyecto y rango de tiempo.
- Exportación de métricas a CSV/JSON.
- Gestión de usuarios y roles (administrador / usuario normal).
- Configuración de SMTP y destinatarios de alertas.

## 🧩 Stack

- Vue 3 (Composition API)
- Vue Router
- Pinia (store)
- TailwindCSS
- Chart.js + vue-chartjs
- Axios

## 🎨 Assets y UI

El proyecto incluye assets personalizados para mejorar la identificación visual:
- **Logos de SO**: Detección automática de Linux y Windows en el dashboard.
- **Iconos**: Integración de logos SVG y PNG para una experiencia visual rica.

## 🛠 Desarrollo local

Desde `src/client`:

```bash
npm install
npm run dev
```

La aplicación se ejecutará por defecto en `http://localhost:5173` (o el puerto que indique Vite).

> El backend FastAPI debe estar levantado (por ejemplo en `http://localhost:8000`) y accesible mediante `/api`.

## 🏗 Build para producción

```bash
npm run build
```

Los archivos estáticos se generan en la carpeta `dist/`, que luego se sirven detrás de Nginx u otro servidor web según se describe en el README de la raíz del proyecto.
