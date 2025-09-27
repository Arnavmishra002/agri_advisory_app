# Krishimitra: Agri-Advisory App Prototype

## Problem Description
A majority of small and marginal farmers in India rely on traditional knowledge, local shopkeepers, or guesswork for crop selection, pest control, and fertilizer use. They lack access to personalized, real-time advisory services that account for soil type, weather conditions, and crop history. This often leads to poor yield, excessive input costs, and environmental degradation due to overuse of chemicals. Language barriers, low digital literacy, and absence of localized tools further limit their access to modern agri-tech resources.

## Impact
Helping small farmers make informed decisions can significantly increase productivity, reduce costs, and improve livelihoods. It also contributes to sustainable farming practices, food security, and environmental conservation. A smart advisory solution can empower farmers with scientific insights in their native language and reduce dependency on unreliable third-party advice.

## Expected Outcomes
*   A multilingual, AI-based mobile app or chatbot that provides real-time, location-specific crop advisory.
*   Comprehensive fertilizer recommendations based on crop type, soil type, and season using government data.
*   Weather-based alerts and predictive insights from IMD (India Meteorological Department).
*   Crop recommendation and substitution based on soil type, weather conditions, and market prices.
*   Real-time market price tracking from Agmarknet and e-NAM APIs.
*   ICAR-based crop recommendations and agricultural insights.
*   NABARD statistics integration for small and marginal farmer support.
*   **Advanced AI/ML Features:**
    *   Continuous learning from user feedback
    *   Personalized recommendations based on user history
    *   Real-time model retraining and improvement
    *   ML-enhanced predictions with confidence scores
    *   User feedback collection and analysis system
*   Voice support for low-literate users.
*   Feedback and usage data collection for continuous improvement.

## Technologies
*   **Frontend:** Flutter (Mobile), React (Web)
*   **Backend:** Django / Node.js
*   **Database:** PostgreSQL / MongoDB
*   **AI/ML Models:** 
    *   Advanced ML models with continuous learning from user feedback
    *   Random Forest for crop recommendations and yield prediction
    *   Neural Networks for fertilizer recommendations
    *   Personalized recommendations based on user history
    *   Real-time model retraining and performance monitoring
    *   NLP chatbot with ML enhancement (BERT, multilingual)
*   **APIs/Data Sources:**
    *   Weather → IMD APIs
*   Soil → Govt. Soil Health Card data
*   Market → Agmarknet & e-NAM
*   Crop data → ICAR & agricultural research datasets

## Research and References
*   NABARD Report 2022 → 86% of Indian farmers are small/marginal.
*   FAO & ICAR studies → ICT advisories improve yield by 20–30%.
*   IMD Weather Data Portal – https://mausam.imd.gov.in
*   Agmarknet (Mandi Prices) – https://agmarknet.gov.in
*   e-NAM (National Agri Market) – https://enam.gov.in
*   ICAR pest & crop dataset

## Prototype Structure

This prototype will focus on a basic backend structure using Django, a simple API endpoint for crop advisory, and a placeholder for AI/ML models. It will demonstrate the core idea of providing personalized agricultural advice. The frontend UI has been enhanced to provide a more intuitive and visually appealing experience, aligning with a farming software aesthetic. 

## Setup and Run Instructions

### Option 1: Docker Setup (Recommended)

1. **Prerequisites:**
   - Docker and Docker Compose installed
   - See [DOCKER.md](DOCKER.md) for detailed Docker setup instructions

2. **Quick Start with Docker:**
   ```bash
   cd agri_advisory_app
   docker-compose up --build
   ```

3. **Run database migrations:**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. **Access the application:**
   - Backend API: http://localhost:8000/api/
   - API Documentation: http://localhost:8000/api/schema/swagger-ui/

### Option 2: Local Development Setup

1. **Prerequisites:**
   - Python 3.10+
   - PostgreSQL
   - Redis

2. **Navigate to the project directory:**
    ```bash
    cd agri_advisory_app
    ```

3. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\Activate.ps1
   # On Linux/Mac:
   source venv/bin/activate
   ```

4. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

6. **Make migrations:**
    ```bash
    python manage.py makemigrations advisory
    python manage.py migrate
    ```

7. **Create a superuser (optional, for accessing Django Admin):**
    ```bash
    python manage.py createsuperuser
    ```

8. **Run the development server:**
    ```bash
    python manage.py runserver
   ```

9. **Start Celery worker (in a separate terminal):**
   ```bash
   celery -A core worker --loglevel=info
   ```

10. **Start Celery beat scheduler (in a separate terminal):**
    ```bash
    celery -A core beat --loglevel=info
    ```

    The API will be available at `http://127.0.0.1:8000/api/`.
    The interactive API documentation (Swagger UI) will be available at `http://127.0.0.1:8000/api/schema/swagger-ui/`.

## API Documentation

### Core Advisory Endpoints

#### Crop Advisory Management
*   `GET /api/advisories/`: List all crop advisories
*   `POST /api/advisories/`: Create a new crop advisory
*   `GET /api/advisories/{id}/`: Retrieve a specific crop advisory
*   `PUT /api/advisories/{id}/`: Update a specific crop advisory
*   `DELETE /api/advisories/{id}/`: Delete a specific crop advisory

#### AI/ML Prediction Endpoints
*   `POST /api/advisories/predict_yield/`: Predict crop yield
  - **Parameters:** `crop_type`, `soil_type`, `weather_data`
*   `POST /api/advisories/chatbot/`: Interact with the NLP chatbot
  - **Parameters:** `query`, `language`
*   `POST /api/advisories/fertilizer_recommendation/`: Get fertilizer recommendations
  - **Parameters:** `crop_type`, `soil_type`, `season`, `area_hectares`, `language`
*   `POST /api/advisories/ml_crop_recommendation/`: Get ML-enhanced crop recommendations
  - **Parameters:** `soil_type`, `season`, `temperature`, `rainfall`, `humidity`, `ph`, `organic_matter`, `user_id`
*   `POST /api/advisories/ml_fertilizer_recommendation/`: Get ML-enhanced fertilizer recommendations
  - **Parameters:** `crop_type`, `soil_type`, `season`, `temperature`, `rainfall`, `humidity`, `ph`, `organic_matter`

#### Feedback and Analytics
*   `POST /api/advisories/collect_feedback/`: Collect user feedback for ML model improvement
  - **Parameters:** `user_id`, `session_id`, `prediction_type`, `input_data`, `system_prediction`, `actual_result`, `feedback_rating`, `feedback_text`
*   `GET /api/advisories/feedback_analytics/`: Get feedback analytics
  - **Parameters:** `days`
*   `GET /api/advisories/model_performance/`: Get ML model performance metrics
*   `GET /api/advisories/user_feedback_history/`: Get user feedback history
  - **Parameters:** `user_id`, `limit`

### External Data Integration

#### Weather Data
*   `GET /api/weather/current/`: Get current weather data from IMD
  - **Parameters:** `lat`, `lon`, `lang`
*   `GET /api/weather/forecast/`: Get weather forecast from IMD
  - **Parameters:** `lat`, `lon`, `lang`, `days`

#### Market Data
*   `GET /api/market-prices/prices/`: Get market prices from Agmarknet
  - **Parameters:** `lat`, `lon`, `lang`, `product`
*   `GET /api/trending-crops/`: Get trending crops data from e-NAM
  - **Parameters:** `lat`, `lon`, `lang`

### Advanced Features

#### SMS/IVR Integration
*   `POST /api/sms-ivr/receive-sms/`: Receive SMS messages
  - **Parameters:** `phone_number`, `message`
*   `POST /api/sms-ivr/ivr-input/`: Handle IVR input
  - **Parameters:** `phone_number`, `user_input`

#### Pest Detection
*   `POST /api/pest-detection/detect/`: Detect pests from uploaded images
  - **Parameters:** `image` (file upload)

#### Text-to-Speech
*   `POST /api/tts/speak/`: Convert text to speech
  - **Parameters:** `text`, `language`

#### Community Forum
*   `GET /api/forum/`: List forum posts
*   `POST /api/forum/`: Create a new forum post
*   `GET /api/forum/{id}/`: Retrieve a specific forum post
*   `PUT /api/forum/{id}/`: Update a specific forum post
*   `DELETE /api/forum/{id}/`: Delete a specific forum post

#### User Management
*   `GET /api/users/`: List users (Admin only)
*   `POST /api/users/`: Create a new user (Admin only)
*   `GET /api/users/{id}/`: Retrieve a specific user
*   `PUT /api/users/{id}/`: Update a specific user
*   `DELETE /api/users/{id}/`: Delete a specific user

### Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Rate Limiting

- **General endpoints:** 100 requests per minute per user
- **ML prediction endpoints:** 10 requests per minute per user
- **File upload endpoints:** 5 requests per minute per user

### Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Too Many Requests
- `500`: Internal Server Error

### Interactive API Documentation

Visit `http://localhost:8000/api/schema/swagger-ui/` for interactive API documentation with request/response examples.

## Project Structure

```
agri_advisory_app/
├── core/                           # Django project settings
│   ├── settings.py                 # Main configuration
│   ├── urls.py                     # URL routing
│   ├── celery.py                   # Celery configuration
│   └── wsgi.py                     # WSGI configuration
├── advisory/                       # Main application
│   ├── models.py                   # Database models
│   ├── views.py                    # API views
│   ├── serializers.py              # Data serialization
│   ├── urls.py                     # URL patterns
│   ├── permissions.py              # Custom permissions
│   ├── utils.py                    # Utility functions
│   ├── api/                        # API layer
│   │   ├── views.py                # API viewsets
│   │   ├── serializers.py          # API serializers
│   │   └── urls.py                 # API URL routing
│   ├── ml/                         # Machine Learning
│   │   ├── ai_models.py            # AI model implementations
│   │   ├── ml_models.py            # ML model definitions
│   │   ├── fertilizer_recommendations.py
│   │   └── nlp_chatbot.py          # NLP chatbot
│   ├── services/                   # External services
│   │   ├── weather_api.py          # Weather data integration
│   │   ├── market_api.py           # Market data integration
│   │   ├── notifications.py        # Push notifications
│   │   ├── sms_ivr.py              # SMS/IVR integration
│   │   └── pest_detection.py       # Pest detection service
│   └── tasks.py                    # Celery background tasks
├── frontend/                       # React frontend
│   ├── public/
│   │   ├── manifest.json           # PWA manifest
│   │   └── index.html
│   ├── src/
│   │   ├── components/              # React components
│   │   ├── services/                # API services
│   │   ├── utils/                  # Utility functions
│   │   ├── App.tsx                 # Main app component
│   │   └── serviceWorker.ts        # PWA service worker
│   └── package.json
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Development Docker setup
├── docker-compose.prod.yml         # Production Docker setup
├── nginx.conf                      # Nginx configuration
├── env.example                     # Environment variables template
├── .dockerignore                   # Docker ignore file
├── DOCKER.md                       # Docker documentation
└── README.md                       # This file
```

## Key Features

### 🤖 AI/ML Capabilities
- **Crop Recommendation Engine**: ML-powered crop suggestions based on soil, weather, and market conditions
- **Yield Prediction**: Advanced models for crop yield forecasting
- **Fertilizer Optimization**: Smart fertilizer recommendations with dosage calculations
- **NLP Chatbot**: Multilingual conversational AI for farmer queries
- **Pest Detection**: Computer vision for pest identification from images
- **Continuous Learning**: Models improve through user feedback

### 🌐 External Data Integration
- **Weather Data**: Real-time and forecast data from IMD
- **Market Prices**: Live commodity prices from Agmarknet and e-NAM
- **Soil Health**: Integration with government soil health card data
- **Crop Data**: ICAR and agricultural research datasets

### 📱 Multi-Channel Access
- **Web Application**: React-based responsive web interface
- **Progressive Web App (PWA)**: Offline-capable mobile experience
- **SMS Integration**: Text-based advisory for basic phones
- **IVR Support**: Voice-based interaction for low-literacy users
- **Push Notifications**: Real-time alerts for weather and market updates

### 🔧 Technical Features
- **RESTful API**: Comprehensive API with JWT authentication
- **Background Tasks**: Celery for scheduled weather/market updates
- **Caching**: Redis for improved performance
- **Error Monitoring**: Sentry integration for production monitoring
- **Docker Support**: Containerized deployment for consistency
- **Database**: PostgreSQL for robust data storage

### 🌍 Localization
- **Multi-language Support**: Hindi, English, and regional languages
- **Text-to-Speech**: Audio responses for accessibility
- **Regional Adaptation**: Location-specific recommendations

### 👥 Community Features
- **Forum**: Community discussion platform
- **User Management**: Role-based access control
- **Feedback System**: Continuous improvement through user input

## Development Status

✅ **Completed Features:**
- Django backend with REST API
- Celery and Redis integration
- PWA frontend with service worker
- SMS/IVR integration hooks
- NLP chatbot with HuggingFace
- Pest detection pipeline
- API input sanitization
- Sentry error monitoring
- Text-to-speech support
- Push notifications
- Community forum
- Docker containerization
- Comprehensive documentation

🔄 **In Progress:**
- Unit testing implementation
- Performance optimization

📋 **Planned Features:**
- Mobile app development (Flutter)
- Advanced ML model training
- Real-time data streaming
- Advanced analytics dashboard

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Contact the development team
- Check the documentation in the `/docs` folder
