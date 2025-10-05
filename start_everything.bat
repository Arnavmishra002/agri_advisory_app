@echo off
echo 🌾 Starting Krishimitra Agricultural AI Assistant
echo ================================================

echo.
echo 📂 Navigating to project directory...
cd /d "C:\AI\agri_advisory_app"

echo.
echo 🐍 Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo 🔧 Starting Django server...
start "Django Server" cmd /k "python manage.py runserver 127.0.0.1:8000"

echo.
echo ⏳ Waiting 5 seconds for Django server to start...
timeout /t 5 /nobreak > nul

echo.
echo 🚀 Starting Streamlit app...
start "Streamlit App" cmd /k "streamlit run streamlit_app.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo ✅ Both servers are starting!
echo.
echo 🌐 Django API: http://127.0.0.1:8000
echo 🌐 Streamlit UI: http://127.0.0.1:8501
echo.
echo Press any key to exit this window...
pause > nul
