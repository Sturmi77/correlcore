@echo off
REM Gemeinsamer Node-PATH-Setup fuer die dev-*.cmd Wrapper.
REM Node wird hier ueber fnm verwaltet und liegt nicht global auf dem PATH.
REM Reihenfolge: vorhandenes node.exe auf dem PATH > NODE_DIR (falls gesetzt)
REM > hoechste installierte fnm-Version.

where node >nul 2>&1 && exit /b 0

if defined NODE_DIR goto :check

for /f "delims=" %%D in ('dir /b /ad /o-n "%APPDATA%\fnm\node-versions\v*" 2^>nul') do (
  set "NODE_DIR=%APPDATA%\fnm\node-versions\%%D\installation"
  goto :check
)

:check
if not defined NODE_DIR (
  echo [dev] Keine fnm-Node-Installation unter "%APPDATA%\fnm\node-versions" gefunden.
  echo [dev] Node installieren ^(fnm install 22^) oder NODE_DIR selbst setzen.
  exit /b 1
)
if not exist "%NODE_DIR%\node.exe" (
  echo [dev] node.exe nicht gefunden unter "%NODE_DIR%" - NODE_DIR pruefen.
  exit /b 1
)
set "PATH=%NODE_DIR%;%PATH%"
