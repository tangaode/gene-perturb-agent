@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Checking Python...
where py >nul 2>nul
if %errorlevel%==0 goto :have_python
where python >nul 2>nul
if %errorlevel%==0 goto :have_python

echo Python not found. Please install Python 3.11+ first.
echo Download: https://www.python.org/downloads/
pause
exit /b 1

:have_python
echo [2/3] Installing/updating dependencies (first run may take several minutes)...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\setup_easy.ps1"
if not %errorlevel%==0 (
  echo Setup failed.
  pause
  exit /b 1
)

echo [3/3] Starting Gene Perturb Agent...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_easy.ps1"
if not %errorlevel%==0 (
  echo Start failed.
  pause
  exit /b 1
)

exit /b 0
