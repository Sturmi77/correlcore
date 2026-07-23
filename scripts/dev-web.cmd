@echo off
REM SvelteKit-Dev-Server, Browser-Variante (Port 5173).
REM INTERNAL_API_URL zeigt per Default auf die Mock-API (scripts\dev-mock-api.cmd).
REM Fuer das echte Backend vorher setzen: set INTERNAL_API_URL=http://127.0.0.1:8000
call "%~dp0_node-path.cmd" || exit /b 1
if not defined INTERNAL_API_URL set "INTERNAL_API_URL=http://127.0.0.1:8001"
cd /d "%~dp0.."
call corepack pnpm --filter @correlcore/web dev %*
