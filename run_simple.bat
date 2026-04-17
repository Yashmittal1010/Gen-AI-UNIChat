@echo off
title UNIchat Simple Launcher
color 0B
echo UNIchat Launcher (Simplified)
echo =============================

cd /d "%~dp0"

echo Cleaning previous sessions...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

echo Starting API Backend...
start "UNIchat API" /D "%~dp0." cmd /c "venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting Web Interface...
start "UNIchat UI" /D "%~dp0frontend" cmd /c "node server.js"

timeout /t 2 /nobreak >nul

echo Opening Browser...
venv\Scripts\python.exe -c "import webbrowser; webbrowser.open('http://localhost:3000')"

exit
