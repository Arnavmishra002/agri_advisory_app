# Agri-Advisory App Prototype

## Problem Description
A majority of small and marginal farmers in India rely on traditional knowledge, local shopkeepers, or guesswork for crop selection, pest control, and fertilizer use. They lack access to personalized, real-time advisory services that account for soil type, weather conditions, and crop history. This often leads to poor yield, excessive input costs, and environmental degradation due to overuse of chemicals. Language barriers, low digital literacy, and absence of localized tools further limit their access to modern agri-tech resources.

## Impact
Helping small farmers make informed decisions can significantly increase productivity, reduce costs, and improve livelihoods. It also contributes to sustainable farming practices, food security, and environmental conservation. A smart advisory solution can empower farmers with scientific insights in their native language and reduce dependency on unreliable third-party advice.

## Expected Outcomes
*   A multilingual, AI-based mobile app or chatbot that provides real-time, location-specific crop advisory.
*   Soil health recommendations and fertilizer guidance.
*   Weather-based alerts and predictive insights.
*   Pest/disease detection via image uploads.
*   Market price tracking.
*   Voice support for low-literate users.
*   Feedback and usage data collection for continuous improvement.

## Technologies
*   **Frontend:** Flutter (Mobile), React (Web)
*   **Backend:** Django / Node.js
*   **Database:** PostgreSQL / MongoDB
*   **AI/ML Models:** Yield prediction (scikit-learn/XGBoost), Pest detection (CNN, TensorFlow), NLP chatbot (BERT, multilingual)
*   **APIs/Data Sources:**
    *   Weather → IMD APIs
    *   Soil → Govt. Soil Health Card data
    *   Market → Agmarknet & e-NAM
    *   Pest dataset → ICAR & open datasets

## Research and References
*   NABARD Report 2022 → 86% of Indian farmers are small/marginal.
*   FAO & ICAR studies → ICT advisories improve yield by 20–30%.
*   IMD Weather Data Portal – https://mausam.imd.gov.in
*   Agmarknet (Mandi Prices) – https://agmarknet.gov.in
*   e-NAM (National Agri Market) – https://enam.gov.in
*   ICAR pest & crop dataset

## Prototype Structure

This prototype will focus on a basic backend structure using Django, a simple API endpoint for crop advisory, and a placeholder for AI/ML models. It will demonstrate the core idea of providing personalized agricultural advice. 

## Setup and Run Instructions (Django Backend)

1.  **Navigate to the project directory:**
    ```bash
    cd agri_advisory_app
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Make migrations:**
    ```bash
    python manage.py makemigrations advisory
    python manage.py migrate
    ```

4.  **Create a superuser (optional, for accessing Django Admin):**
    ```bash
    python manage.py createsuperuser
    ```

5.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```

    The API will be available at `http://127.0.0.1:8000/api/`.
    The interactive API documentation (Swagger UI) will be available at `http://127.0.0.1:8000/api/schema/swagger-ui/`.

## API Endpoints:

*   `GET /api/advisories/`: List all crop advisories.
*   `POST /api/advisories/`: Create a new crop advisory.
*   `GET /api/advisories/{id}/`: Retrieve a specific crop advisory.
*   `PUT /api/advisories/{id}/`: Update a specific crop advisory.
*   `DELETE /api/advisories/{id}/`: Delete a specific crop advisory.
*   `POST /api/advisories/predict_yield/`: Predict crop yield (takes `crop_type`, `soil_type`, `weather_data`).
*   `POST /api/advisories/detect_pest_disease/`: Detect pest/disease (takes `image`).
*   `POST /api/advisories/chatbot/`: Interact with the chatbot (takes `query`, `language`).
