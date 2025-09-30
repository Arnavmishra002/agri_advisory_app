@echo off
echo Starting Celery Worker...
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Start Celery worker
echo Starting Celery worker...
echo.
echo ========================================
echo Celery Worker is starting...
echo ========================================
echo.
echo This handles background tasks for the app
echo Keep this window open while using the app
echo.
echo Press Ctrl+C to stop the worker
echo ========================================
echo.

celery -A core worker --loglevel=info
