@echo off
REM One-click start on Windows. The first run sets up the virtual environment.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv --clear .venv
  if errorlevel 1 goto :setup_failed
)
REM The marker is written only after a complete install, so an interrupted one is retried.
if not exist .venv\.installed (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto :setup_failed
  echo installed> .venv\.installed
)
if not exist .env (
  copy .env.example .env
  echo.
  echo Created .env - open it, paste your GNANI_API_KEY, then run this again.
  notepad .env
  exit /b
)
start "" /b cmd /c "timeout /t 4 >nul & start http://localhost:8000"
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
exit /b

:setup_failed
echo.
echo Setup failed. Check that Python 3.10+ is installed and you are online, then run this again.
pause
exit /b 1
