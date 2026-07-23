@echo off
REM Startet die Mock-API (Port 8001) fuer Browser-Arbeit ohne echtes Backend.
call "%~dp0_node-path.cmd" || exit /b 1
cd /d "%~dp0.."
node scripts\dev-mock-api.mjs
