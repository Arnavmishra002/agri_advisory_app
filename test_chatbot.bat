@echo off
echo ========================================
echo Testing Enhanced Agricultural Chatbot
echo ========================================
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Testing Enhanced Chatbot Features...
echo.

REM Test basic functionality
echo 1. Testing Basic Chatbot...
python simple_test_chatbot.py
echo.

REM Test Django tests
echo 2. Running Django Tests...
python manage.py test advisory.tests --verbosity=2
echo.

REM Test API endpoints
echo 3. Testing API Endpoints...
echo.

echo Testing English Chat:
curl -X POST http://localhost:8000/api/advisories/chatbot/ ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"Hello! How are you?\", \"language\": \"en\", \"user_id\": \"test_user\"}"
echo.

echo Testing Hindi Chat:
curl -X POST http://localhost:8000/api/advisories/chatbot/ ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"नमस्ते! आप कैसे हैं?\", \"language\": \"hi\", \"user_id\": \"test_user\"}"
echo.

echo Testing Bengali Chat:
curl -X POST http://localhost:8000/api/advisories/chatbot/ ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"নমস্কার! আপনি কেমন আছেন?\", \"language\": \"bn\", \"user_id\": \"test_user\"}"
echo.

echo Testing Weather API:
curl "http://localhost:8000/api/weather/current/?lat=28.6139&lon=77.2090&lang=en"
echo.

echo Testing Market Prices API:
curl "http://localhost:8000/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en"
echo.

echo ========================================
echo Chatbot Testing Complete!
echo ========================================
echo.
echo Check the results above to verify:
echo - Multilingual support (25+ languages)
echo - ChatGPT-like conversations
echo - Persistent chat history
echo - Agricultural expertise
echo - API functionality
echo.
pause
