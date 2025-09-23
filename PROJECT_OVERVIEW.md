# Agri-Advisory App: Project Overview

This document provides a comprehensive overview of the Agri-Advisory application, detailing its purpose, features, technical architecture, and implementation specifics.

## 1. Project Description

The Agri-Advisory App is designed to assist farmers by providing essential agricultural information. It integrates weather data, market prices, trending crop information, a chatbot for queries, and an image upload feature for pest and disease detection. The application aims to offer localized and language-specific advice to empower farmers with timely and relevant data for better decision-making.

## 2. Key Features

*   **Auto-Location Detection:** Automatically detects the user's geographical location to provide localized data.
*   **Weather Display:** Shows current weather conditions based on the user's detected location.
*   **Market Prices Display:** Provides mock real-time market prices for various agricultural products relevant to the user's location.
*   **Trending Crops Display:** Suggests trending and beneficial crops for the user's region, considering local conditions (currently mock data).
*   **Chatbot:** An interactive chatbot to answer farmer queries (backend AI model integration pending, currently uses a mock response).
*   **Image Upload for Pest/Disease Detection:** Allows farmers to upload images for potential pest or disease identification (backend AI model integration pending).
*   **Language Selection:** Supports switching between English and Hindi for all user-facing content.

## 3. Technologies Used

### Frontend
*   **React:** A JavaScript library for building user interfaces.
*   **TypeScript:** A typed superset of JavaScript that compiles to plain JavaScript, enhancing code quality and maintainability.
*   **Axios:** A promise-based HTTP client for making API requests from the browser.
*   **CSS:** For styling the application.

### Backend
*   **Django:** A high-level Python Web framework that encourages rapid development and clean, pragmatic design.
*   **Django REST Framework (DRF):** A powerful and flexible toolkit for building Web APIs.
*   **Python:** The primary programming language for the backend logic.

### Database
*   **SQLite:** Django's default lightweight database, used for development and local testing (`db.sqlite3`).

## 4. Architectural Overview

The application follows a client-server architecture with a clear separation between the frontend and the backend:

*   **Frontend (React/TypeScript):** Runs in the user's web browser, responsible for the user interface, user interaction, and making API calls to the backend.
*   **Backend (Django/Python):** A RESTful API server responsible for handling business logic, data processing, mock data generation, and eventually integrating with external (e.g., Indian government) APIs.

Communication between the frontend and backend occurs via HTTP requests to `/api/` endpoints exposed by the Django REST Framework.

## 5. Technical Implementation Details

### Auto-Location Detection (Frontend)
The user's location (latitude and longitude) is obtained using the browser's native `navigator.geolocation.getCurrentPosition()` API. This is handled in `frontend/src/App.tsx` within a `useEffect` hook that runs once on component mount. The obtained `latitude`, `longitude`, and the selected `language` are then passed as props to relevant child components (`WeatherDisplay`, `MarketPricesDisplay`, `TrendingCropsDisplay`).

### Mock Backend APIs
To enable a functional demo while awaiting integration with real Indian government APIs, mock data has been implemented for weather, market prices, and trending crops.

*   **`advisory/weather_api.py`**:
    *   Contains `MockWeatherAPI` with `get_current_weather` and `get_forecast_weather` methods.
    *   These methods return hardcoded weather data that varies slightly based on the provided `latitude`, `longitude`, and `language` (English or Hindi).
    *   The original `ExternalWeatherAPI` is kept for future real API integration.

*   **`advisory/market_api.py`**:
    *   Includes `get_mock_market_prices` which now accepts `latitude`, `longitude`, `language`, and `product_type`.
    *   It simulates location-based market prices by mapping `latitude` and `longitude` to a `mock_city` (e.g., Delhi, Mumbai).
    *   The prices and units are localized based on the `language` parameter.
    *   Also contains `get_mock_trending_crops` which returns hardcoded trending crop information, localized based on the `language` parameter.

*   **`advisory/views.py`**:
    *   **`WeatherViewSet`**: Its `current` and `forecast` methods now instantiate `MockWeatherAPI` and call its respective methods, passing `latitude`, `longitude`, and `language` (and `days` for forecast).
    *   **`MarketPricesViewSet`**: Its `prices` method calls `get_mock_market_prices`, forwarding `latitude`, `longitude`, `language`, and `product_type`.
    *   **`TrendingCropsViewSet`**: A new `ViewSet` with a `list` method that calls `get_mock_trending_crops`, passing `latitude`, `longitude`, and `language`.
    *   **`TextToSpeechViewSet`**: This ViewSet has been commented out, along with its import, as the Text-to-Speech functionality was removed per user request.

### Localization
The application supports English and Hindi. The `language` state is managed in `frontend/src/App.tsx` and passed down to child components. All user-facing strings in `WeatherDisplay.tsx`, `MarketPricesDisplay.tsx`, and `TrendingCropsDisplay.tsx` are dynamically rendered based on the `language` prop. The backend also uses the `lang` parameter in API calls to return localized mock data.

### Chatbot & Image Upload
These features are implemented on the frontend (`Chatbot.tsx`, `ImageUpload.tsx`) with placeholders for backend integration. The frontend makes calls to `http://localhost:8000/api/advisories/chatbot/` and `http://localhost:8000/api/advisories/detect_pest_disease/` respectively. The backend (`advisory/views.py`, `advisory/ai_models.py`) contains basic structures to handle these requests and can be extended with actual AI models.

## 6. Setup and Running the Project

To run this project, you need to have Python (with pip) and Node.js (with npm) installed.

### Backend Setup (Django)

1.  **Navigate to the backend directory:**
    ```bash
    cd C:\AI\agri_advisory_app
    ```
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Apply database migrations:**
    ```bash
    python manage.py migrate
    ```
4.  **Start the Django development server:**
    ```bash
    python manage.py runserver
    ```
    The backend API will be available at `http://127.0.0.1:8000/`.

### Frontend Setup (React)

1.  **Open a new terminal and navigate to the frontend directory:**
    ```bash
    cd C:\AI\agri_advisory_app\frontend
    ```
2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```
3.  **Start the React development server:**
    ```bash
    npm start
    ```
    The frontend application will typically open in your browser at `http://localhost:3000`.

## 7. Future Enhancements

The current mock data implementation serves as a placeholder. Future enhancements will involve:

*   **Integration with Real Indian Government APIs:** Replacing mock data in `advisory/weather_api.py` and `advisory/market_api.py` with actual data fetched from official Indian government weather and agricultural data APIs.
*   **Advanced Location Mapping:** Implementing more precise mapping of `latitude`/`longitude` to specific agricultural regions or market locations in India.
*   **AI Model Integration:** Fully integrating AI models for the chatbot and pest/disease detection.

This `PROJECT_OVERVIEW.md` file aims to provide all the necessary information for understanding and developing the Agri-Advisory App.
