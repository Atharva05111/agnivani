@echo off
REM One-click start on Windows. First run creates the virtual environment.
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  call .venv\Scripts\activate
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)
if not exist .env (
  copy .env.example .env
  echo.
  echo Created .env - open it, paste your GNANI_API_KEY, then run this again.
  notepad .env
  exit /b
)
start "" /b cmd /c "timeout /t 4 >nul & start http://localhost:8000"
uvicorn app.main:app --port 8000
