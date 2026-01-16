# Changelog

All notable changes to this project will be documented in this file.

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
