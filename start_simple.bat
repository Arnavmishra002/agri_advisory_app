@echo off
echo 🌾 Starting Krishimitra - Simple Standalone Version
echo ==================================================

echo.
echo 📂 Navigating to project directory...
cd /d "C:\AI\agri_advisory_app"

echo.
echo 🐍 Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo 🚀 Starting Standalone Streamlit App...
echo 🌐 URL: http://127.0.0.1:8502
echo.
echo ✅ No Django server required! This version uses mock data.
echo.

streamlit run streamlit_simple.py --server.port 8502 --server.address 127.0.0.1
