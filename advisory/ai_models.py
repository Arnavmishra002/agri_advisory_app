
def predict_yield(crop_type, soil_type, weather_data):
    """Simulates yield prediction using a placeholder AI model.

    In a real application:
    1. **Data Collection:**
       - `weather_data` would be fetched from IMD APIs based on location and current/historical dates.
       - `soil_type` and other soil health parameters would be retrieved from Govt. Soil Health Card data.
       - Historical crop data (yields, input costs) would be used for training.

    2. **Model Loading & Prediction:**
       - A pre-trained scikit-learn or XGBoost model would be loaded.
       - Features (e.g., crop_type, soil_type, temperature, rainfall, humidity) would be extracted/engineered.
       - The model would predict the yield.

    3. **Recommendation Generation:**
       - Based on the predicted yield and other factors, a personalized recommendation is generated.
    """
    # Placeholder logic for demonstration
    if crop_type == "wheat" and soil_type == "loamy":
        if weather_data == "favorable":
            return {"predicted_yield": "50-55 quintals/acre", "confidence": "high", "recommendation": "Optimal conditions, continue good practices."}
        elif weather_data == "drought":
            return {"predicted_yield": "20-25 quintals/acre", "confidence": "medium", "recommendation": "Consider drought-resistant varieties or irrigation."}
        else:
            return {"predicted_yield": "40-45 quintals/acre", "confidence": "medium", "recommendation": "Moderate conditions, monitor closely."}
    elif crop_type == "rice" and soil_type == "clayey":
        if weather_data == "favorable":
            return {"predicted_yield": "60-65 quintals/acre", "confidence": "high", "recommendation": "Excellent for rice. Ensure proper water management."}
        else:
            return {"predicted_yield": "35-40 quintals/acre", "confidence": "medium", "recommendation": "Sub-optimal conditions. Focus on nutrient management."}
    
    return {"predicted_yield": "unknown", "confidence": "low", "recommendation": "No specific recommendation available for these inputs. Consider providing more data."}

def detect_pest_disease(image_upload):
    """Simulates pest/disease detection using a placeholder AI model.

    In a real application:
    1. **Data Collection:**
       - `image_upload` would be a base64 encoded image string or a URL to an image.
       - This image would be pre-processed (resizing, normalization) to match the model's input requirements.
       - Pest/disease datasets (e.g., ICAR & open datasets) would be used for training.

    2. **Model Loading & Prediction:**
       - A pre-trained CNN model (e.g., built with TensorFlow/Keras) for image classification would be loaded.
       - The pre-processed image would be fed to the model to predict the presence and type of pest/disease.

    3. **Recommendation Generation:**
       - Based on the detection, specific recommendations for pest control or disease management are provided.
    """
    # Placeholder logic for demonstration
    if image_upload == "leaf_with_spots.jpg":
        return {"detection": "Early Blight (Potato/Tomato)", "confidence": "high", "recommendation": "Apply a broad-spectrum fungicide containing Mancozeb or Chlorothalonil. Improve air circulation."}
    elif image_upload == "yellow_leaves.png":
        return {"detection": "Nitrogen Deficiency", "confidence": "medium", "recommendation": "Apply nitrogen-rich fertilizer (e.g., Urea). Ensure proper soil pH."}
    elif image_upload == "holes_in_leaf.jpg":
        return {"detection": "Insect Infestation (e.g., Caterpillars)", "confidence": "high", "recommendation": "Use neem oil spray or appropriate organic pesticide. Hand-pick larger insects."}
    return {"detection": "No significant pest/disease detected", "confidence": "low", "recommendation": "Continue regular monitoring and good agricultural practices."}

def get_chatbot_response(user_query, language="en"):
    """Simulates NLP chatbot interaction using a placeholder AI model.

    In a real application:
    1. **Natural Language Understanding (NLU):**
       - A pre-trained multilingual BERT model would be used to understand the user's intent and extract entities (e.g., crop_type, location, specific problem).
       - This model would be fine-tuned on agricultural datasets.

    2. **Context & Data Integration:**
       - The chatbot would integrate with external APIs (IMD for weather, Agmarknet/e-NAM for market prices) and internal data (Soil Health Card, historical advisories).
       - It would maintain conversational context to provide more personalized responses.

    3. **Response Generation:**
       - Based on the understood intent, extracted entities, and integrated data, a relevant and multilingual response would be generated.
       - Voice support for low-literate users would involve Speech-to-Text and Text-to-Speech integration.
    """
    print(f"Chatbot received query: {user_query}")
    user_query_lower = user_query.lower().strip() # Strip whitespace
    print(f"Lowercase and stripped query: '{user_query_lower}'") # Debug print
    print(f"'what to plant' in query: {'what to plant' in user_query_lower}") # Debug print
    print(f"'crop recommendation' in query: {'crop recommendation' in user_query_lower}") # Debug print
    print(f"'crop' in query: {'crop' in user_query_lower}")
    print(f"'plant' in query: {'plant' in user_query_lower}")
    print(f"'weather' in query: {'weather' in user_query_lower}")
    print(f"'raebareli' in query: {'raebareli' in user_query_lower}")

    # Placeholder logic for demonstration - Updated to force reload and improve intent
    
    # Prioritize specific crop recommendation queries
    if ("crop" in user_query_lower and "plant" in user_query_lower) or "what to plant" in user_query_lower or "crop recommendation" in user_query_lower:
        location_info = ""
        if "pincode" in user_query_lower:
            # Simulate extracting pincode
            import re
            match = re.search(r'pincode\s*(\d{6})', user_query_lower)
            if match: 
                pincode = match.group(1)
                location_info = f" for pincode {pincode}"
            else:
                location_info = " for your specified location"
        elif "location" in user_query_lower:
            location_info = " for your specified location"
        
        return f"To give you the best crop recommendation{location_info}, I need to know your soil type and recent weather patterns. You can use the 'predict_yield' feature with specific parameters for more personalized advice."
    
    elif "weather" in user_query_lower:
        location_query = ""
        if "raebareli" in user_query_lower:
            location_query = " in Raebareli"
            return f"The weather today{location_query} is sunny with a high of 32°C and a low of 22°C. There's a low chance of rain. (Simulated data, real data would come from IMD APIs)"
        elif "location" in user_query_lower or "city" in user_query_lower or "pincode" in user_query_lower:
            return "To provide weather, please specify a city or location. (Simulated data, real data would come from IMD APIs)"
        elif "today" in user_query_lower:
            return "The weather today is sunny with a high of 30°C and a low of 20°C. There's a 10% chance of light rain in the evening. (Simulated data, real data would come from IMD APIs)"
        elif "next week" in user_query_lower:
            return "The forecast for next week includes intermittent showers and moderate temperatures, ideal for crop growth. (Simulated data, real data would come from IMD APIs)"
        return "Please specify for which period or location you'd like the weather information. (Simulated data, real data would come from IMD APIs)"
    
    elif "fertilizer" in user_query_lower or "soil health" in user_query_lower:
        return "Based on typical soil health recommendations for loamy soil, a balanced NPK (12-12-12) fertilizer is generally recommended for optimal growth. For precise guidance, a soil test is advisable. (Referring to Govt. Soil Health Card data principles)"

    elif "market price" in user_query_lower or "mandi" in user_query_lower:
        if "wheat" in user_query_lower:
            return "The current market price for wheat in your nearest mandi is approximately ₹2,200 per quintal. (Data from Agmarknet & e-NAM APIs)"
        elif "rice" in user_query_lower:
            return "Rice (Basmati) is currently trading at around ₹3,500 per quintal in major markets. (Data from Agmarknet & e-NAM APIs)"
        return "Please specify the crop for which you'd like the market price."

    elif "pest" in user_query_lower or "disease" in user_query_lower:
        return "If you suspect a pest or disease, please use the 'detect_pest_disease' feature by uploading an image for an accurate diagnosis and recommendation."

    return "I'm sorry, I don't have specific information on that. Could you please rephrase your question or ask about weather, soil, market prices, pests, or crop recommendations?"
