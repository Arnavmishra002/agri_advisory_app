@echo off
echo ========================================
echo Starting Krishimitra Streamlit Frontend
echo ========================================
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install Streamlit requirements
echo Installing Streamlit requirements...
pip install -r requirements_streamlit.txt

REM Start Streamlit app
echo Starting Streamlit application...
echo.
echo ========================================
echo Krishimitra Streamlit Frontend Starting...
echo ========================================
echo.
echo Features:
echo - ChatGPT-like AI Chatbot (25+ languages)
echo - Real-time Weather & Location
echo - Trending Crops Analysis
echo - Mandi Prices & Market Data
echo - Agricultural Advisory & Schemes
echo.
echo Access Points:
echo - Streamlit App: http://localhost:8501
echo - Django API: http://localhost:8000/api/
echo - Admin Panel: http://localhost:8000/admin/ (admin/admin123)
echo.
echo Make sure Django server is running on port 8000!
echo Press Ctrl+C to stop the Streamlit server
echo ========================================
echo.

streamlit run streamlit_app.py --server.port 8501 --server.address localhost
