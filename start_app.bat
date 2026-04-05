@echo off
title SkillGraph Launcher

echo ===================================
echo Starting SkillGraph...
echo ===================================

echo.
echo [1/3] Starting Neo4j in WSL...
wsl sudo systemctl start neo4j

echo.
echo [2/3] Starting FastAPI in WSL...
start "SkillGraph API" wsl bash -c "cd /mnt/e/naveen/vitc/project/SkillGraph && source venv/bin/activate && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo [3/3] Starting Frontend server...
start "SkillGraph Frontend" cmd /k "cd /d %~dp0 && python -m http.server 5500"

timeout /t 4 >nul

echo.
echo Opening SkillGraph in browser...
start http://localhost:5500/index.html

echo.
echo SkillGraph is running 🚀
pause
