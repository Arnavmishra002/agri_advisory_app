@echo off
echo ========================================
echo Starting Enhanced Agricultural Chatbot
echo ========================================
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Start the Django server
echo Starting Django server...
echo.
echo ========================================
echo Enhanced Agricultural Chatbot Starting...
echo ========================================
echo.
echo Features:
echo - ChatGPT-like Multilingual Chatbot (25+ languages)
echo - Persistent Chat History
echo - Advanced AI Conversations
echo - Agricultural Expertise
echo.
echo Access Points:
echo - Frontend: Open chatbot_frontend.html in browser
echo - API: http://localhost:8000/api/
echo - API Docs: http://localhost:8000/api/schema/swagger-ui/
echo - Admin Panel: http://localhost:8000/admin/ (admin/admin123)
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python manage.py runserver 127.0.0.1:8000
