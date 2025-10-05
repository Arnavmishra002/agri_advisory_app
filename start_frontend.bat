@echo off
echo ========================================
echo Starting Enhanced Agricultural AI Platform - Frontend
echo ========================================
echo.

cd /d C:\AI\agri_advisory_app

echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Installing Streamlit dependencies...
pip install streamlit plotly requests

echo.
echo Starting Streamlit frontend...
echo Frontend will be available at: http://127.0.0.1:8501
echo.

streamlit run streamlit_app.py --server.port 8501 --server.address 127.0.0.1

echo.
echo Frontend stopped.
pause
