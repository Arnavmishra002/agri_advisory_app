@echo off
echo ========================================
echo Starting Enhanced Agricultural AI Platform - Backend
echo ========================================
echo.

cd /d C:\AI\agri_advisory_app

echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Starting Django backend server...
echo Server will be available at: http://127.0.0.1:8000
echo Swagger UI: http://127.0.0.1:8000/api/schema/swagger-ui/
echo Admin Panel: http://127.0.0.1:8000/admin/
echo.

python manage.py runserver 127.0.0.1:8000

echo.
echo Backend server stopped.
pause
