@echo off
setlocal enabledelayedexpansion
title UNIchat Master Launcher
color 0B

echo.
echo  ==========================================
echo     UNIchat - Master Setup ^& Launch
echo     Clara RAG + Qwen 0.5B + BitNet
echo  ==========================================
echo.

cd /d "%~dp0"

:: ── Cleanup Old Scripts & Ports ──
if exist "setup.bat" del /f /q "setup.bat" >nul 2>&1
if exist "launch.bat" del /f /q "launch.bat" >nul 2>&1
if exist "start.bat" del /f /q "start.bat" >nul 2>&1

echo  Cleaning up orphaned ports (8000, 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

:: ── Step 1: Check Python ──
echo  [1/6] Checking Python...
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed. Please install Python 3.10+.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
)

:: ── Step 2: Python venv ──
echo.
echo  [2/6] Checking Python virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo    Creating Python virtual environment...
    %PYTHON_CMD% -m venv venv
)
set "VENV_PYTHON=%~dp0venv\Scripts\python.exe"

:: ── Step 3: Python deps ──
echo.
echo  [3/6] Checking Python dependencies...
"%VENV_PYTHON%" -c "import fastapi, uvicorn, sklearn, numpy, llama_cpp" >nul 2>&1
if errorlevel 1 (
    echo    Installing Python dependencies...
    "%VENV_PYTHON%" -m pip install fastapi uvicorn scikit-learn numpy llama-cpp-python huggingface-hub[cli]
) else (
    echo    Python dependencies are already installed.
)

:: ── Step 4: Node.js deps ──
echo.
echo  [4/6] Checking Node.js frontend...
if exist "frontend" (
    if not exist "frontend\node_modules" (
        echo    Installing Node.js dependencies...
        cd frontend
        call npm install
        cd ..
    ) else (
        echo    Node.js dependencies already installed.
    )
) else (
    echo    [WARNING] frontend folder not found!
)

:: ── Step 5: Check / Download Model ──
echo.
echo  [5/6] Checking AI Model...
if not exist "models" mkdir models
if not exist "models\model.gguf" (
    if not exist "models\qwen2.5-0.5b-instruct-q4_k_m.gguf" (
        :: Escaping parentheses inside echo inside an if-block is critical!
        echo    Downloading Qwen2.5-0.5B-Instruct model ^(this may take a while^)...
        "%VENV_PYTHON%" -m huggingface_hub.cli download Qwen/Qwen2.5-0.5B-Instruct-GGUF qwen2.5-0.5b-instruct-q4_k_m.gguf --local-dir models
    )
    if exist "models\qwen2.5-0.5b-instruct-q4_k_m.gguf" (
        copy /y "models\qwen2.5-0.5b-instruct-q4_k_m.gguf" "models\model.gguf" >nul
        echo    Model ready!
    )
) else (
    echo    Model is ready!
)

:: Create data directory
if not exist "data" mkdir data

:: ── Step 6: Launching ──
echo.
echo  [6/6] Starting Services...

echo  Starting Python API backend (port 8000)...
start "UNIchat API" /D "%~dp0." cmd /c "call venv\Scripts\activate.bat && python -m uvicorn server:app --host 127.0.0.1 --port 8000 > backend_error.log 2>&1"

timeout /t 3 /nobreak >nul

if not exist "frontend" goto :skip_frontend
echo  Starting Node.js frontend (port 3000)...
start "UNIchat Frontend" /D "%~dp0frontend" cmd /c "node server.js > ../frontend_error.log 2>&1"
timeout /t 2 /nobreak >nul
:skip_frontend


echo.
echo  ======================================
echo     UNIchat is running!
echo.
echo     Frontend ^& API: http://localhost:8000
echo     Node.js ^(Opt^):  http://localhost:3000
echo  ======================================
echo.
echo  Opening browser...

:: Uses Python to reliably force-open the default browser
"%VENV_PYTHON%" -c "import webbrowser; webbrowser.open('http://localhost:8000/')"

echo.
echo  UNIchat launched successfully!
echo  ^(You can safely close this master launcher window. The API and Frontend windows will stay open.^)
timeout /t 5 >nul

