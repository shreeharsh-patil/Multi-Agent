@echo off
echo ============================================
echo  Starting Agentic AI Platform
echo ============================================
echo.

:: Kill any existing processes on our ports
echo [1/3] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul

:: Start Backend
echo [2/3] Starting Backend (port 8000)...
if not exist "D:\Multi agents\backend\.venv\Scripts\python.exe" (
    echo ERROR: Backend virtual environment is missing.
    echo Run: cd /d "D:\Multi agents\backend" ^&^& python -m venv .venv ^&^& .venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)
start "Backend" cmd /c "cd /d D:\Multi agents\backend && .venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 5 /nobreak >nul

:: Start OpenDocuments (Optional, runs on port 5001)
:: To use OpenDocuments RAG, enable it in Settings and run the following command to start OpenDocuments:
:: start "OpenDocuments" cmd /c "cd /d D:\Multi agents\OpenDocuments && npx turbo start -- --port 5001"

:: Start Frontend
echo [3/3] Starting Frontend (port 3000)...
start "Frontend" cmd /c "cd /d D:\Multi agents\frontend && npx next dev -p 3000"
timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:3000
echo  API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Press any key to open the app in your browser...
pause >nul
start http://localhost:3000
