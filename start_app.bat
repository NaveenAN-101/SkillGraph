@echo off
title SkillGraph Launcher
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "ENV_FILE=%ROOT%.env"

REM Load .env values (KEY=VALUE, lines starting with # are ignored)
if exist "%ENV_FILE%" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
    if not "%%~A"=="" set "%%~A=%%~B"
  )
)

REM Defaults if not present in .env
if not defined WSL_PROJECT_PATH set "WSL_PROJECT_PATH="
if not defined API_APP set "API_APP=main:app"
if not defined API_HOST set "API_HOST=0.0.0.0"
if not defined API_PORT set "API_PORT=8000"
if not defined FRONTEND_PORT set "FRONTEND_PORT=5500"
if not defined INDEX_FILE set "INDEX_FILE=index.html"
if not defined PYTHON_BIN set "PYTHON_BIN=python"
if not defined VENV_ACTIVATE set "VENV_ACTIVATE=venv/bin/activate"
if not defined ENABLE_RELOAD set "ENABLE_RELOAD=1"
if not defined ENABLE_NEO4J_START set "ENABLE_NEO4J_START=1"
if not defined OPEN_BROWSER set "OPEN_BROWSER=1"

set "RELOAD_FLAG="
if /I "!ENABLE_RELOAD!"=="1" set "RELOAD_FLAG=--reload"

if not defined WSL_PROJECT_PATH (
  for /f "delims=" %%I in ('wsl wslpath "%ROOT%" 2^>nul') do set "WSL_PROJECT_PATH=%%I"
)

echo ===================================
echo Starting SkillGraph...
echo ===================================

if not defined WSL_PROJECT_PATH (
  echo [ERROR] Could not resolve WSL project path.
  echo Ensure WSL is installed and accessible from Windows Terminal,
  echo or set WSL_PROJECT_PATH in .env
  pause
  exit /b 1
)

if /I "!ENABLE_NEO4J_START!"=="1" (
  echo.
  echo [1/3] Starting Neo4j in WSL...
  wsl sudo systemctl start neo4j
) else (
  echo.
  echo [1/3] Skipping Neo4j start (ENABLE_NEO4J_START=!ENABLE_NEO4J_START!)
)

echo.
echo [2/3] Starting FastAPI in WSL...
start "SkillGraph API" wsl bash -lc "cd '!WSL_PROJECT_PATH!' && if [ -f '!VENV_ACTIVATE!' ]; then source '!VENV_ACTIVATE!'; fi && !PYTHON_BIN! -m uvicorn !API_APP! !RELOAD_FLAG! --host !API_HOST! --port !API_PORT!"

echo.
echo [3/3] Starting Frontend server...
start "SkillGraph Frontend" cmd /k "cd /d %ROOT% && !PYTHON_BIN! -m http.server !FRONTEND_PORT!"

timeout /t 4 >nul

if /I "!OPEN_BROWSER!"=="1" (
  echo.
  echo Opening SkillGraph in browser...
  start http://localhost:!FRONTEND_PORT!/!INDEX_FILE!
)

echo.
echo SkillGraph is running 🚀
pause
