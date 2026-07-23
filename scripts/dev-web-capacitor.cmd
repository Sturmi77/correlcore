@echo off
REM SvelteKit-Dev-Server, Capacitor-Variante (Port 5174).
REM VITE_CAPACITOR=1 schaltet isCapacitorBuild() ein: Bearer-Auth statt Cookies,
REM absolute API-Base statt /api/v1. Das simuliert den Android-Shell-Codepfad im
REM Browser - echte native Plugins (Push, Widget, Deep Links) bleiben No-Ops.
call "%~dp0_node-path.cmd" || exit /b 1
if not defined INTERNAL_API_URL set "INTERNAL_API_URL=http://127.0.0.1:8001"
set "VITE_CAPACITOR=1"
set "VITE_API_BASE_URL=http://localhost:5174/api/v1"
cd /d "%~dp0.."
call corepack pnpm --filter @correlcore/web dev -- --port 5174 --strictPort %*
