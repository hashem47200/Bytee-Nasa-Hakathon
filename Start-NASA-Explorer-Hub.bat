@echo off
cd /d "%~dp0"
title NASA Explorer Hub (Django Server)
echo ============================================================
echo   NASA EXPLORER HUB - DJANGO DATABASE BACKEND
echo   Serving folder : %cd%
echo   Open in browser: http://127.0.0.1:8123
echo   Keep this window open while using the website!
echo   Press Ctrl+C to stop the server.
echo ============================================================
echo.

set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Install Python 3.10+ from https://www.python.org/downloads/
  echo         and tick "Add Python to PATH" during installation.
  pause
  exit /b 1
)

echo [1/4] Checking Django installation...
%PY% -c "import django" >nul 2>nul
if errorlevel 1 (
  echo       Django not found - installing from requirements.txt ...
  %PY% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Could not install Django. Check your internet connection.
    pause
    exit /b 1
  )
)

echo [2/4] Applying database migrations...
%PY% manage.py migrate --noinput
if errorlevel 1 goto :fail

echo [3/4] Verifying space mission educational data...
%PY% manage.py import_missions
if errorlevel 1 goto :fail

echo [4/4] Launching NASA Explorer Hub on port 8123...
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8123"
%PY% manage.py runserver 127.0.0.1:8123
goto :end

:fail
echo.
echo [ERROR] A setup step failed. See the messages above.

:end
echo.
echo ============================================================
echo   Server stopped. Press any key to close this window.
echo ============================================================
pause
