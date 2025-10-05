@echo off
echo ========================================
echo Starting Enhanced Agricultural AI Platform - ALL SERVICES
echo ========================================
echo.

echo This will start both backend and frontend services...
echo.

echo Starting Backend Server...
start "Backend Server - Django" cmd /k "cd /d C:\AI\agri_advisory_app && venv\Scripts\activate && echo Starting Django Backend Server... && python manage.py runserver 127.0.0.1:8000"

echo Waiting 5 seconds for backend to start...
timeout /t 5

echo Starting Frontend Server...
start "Frontend Server - Streamlit" cmd /k "cd /d C:\AI\agri_advisory_app && venv\Scripts\activate && echo Installing Streamlit dependencies... && pip install streamlit plotly requests && echo Starting Streamlit Frontend... && streamlit run streamlit_app.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo ========================================
echo ALL SERVICES STARTED SUCCESSFULLY!
echo ========================================
echo.
echo Your Enhanced Agricultural AI Platform is now running:
echo.
echo Backend API:     http://127.0.0.1:8000
echo Swagger UI:      http://127.0.0.1:8000/api/schema/swagger-ui/
echo Admin Panel:     http://127.0.0.1:8000/admin/
echo.
echo Frontend App:    http://127.0.0.1:8501
echo.
echo Features Available:
echo - ChatGPT-like AI Chatbot (25+ languages)
echo - Real-time Weather Dashboard
echo - Market Prices & Trends
echo - Crop Advisory System
echo - Government-style Professional UI
echo.
echo Check the opened command windows for any errors.
echo.
pause
