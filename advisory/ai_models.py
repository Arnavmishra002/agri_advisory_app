
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

TRANSLATIONS = {
    "en": {
        "crop_recommendation_prompt": "To give you the best crop recommendation{location_info}, I need to know your soil type and recent weather patterns. You can use the 'predict_yield' feature with specific parameters for more personalized advice.",
        "weather_raebareli": "The weather today{location_query} is sunny with a high of 32°C and a low of 22°C. There's a low chance of rain. (Simulated data, real data would come from IMD APIs)",
        "weather_location_prompt": "To provide weather, please specify a city or location. (Simulated data, real data would come from IMD APIs)",
        "weather_today": "The weather today is sunny with a high of 30°C and a low of 20°C. There's a 10% chance of light rain in the evening. (Simulated data, real data would come from IMD APIs)",
        "weather_next_week": "The forecast for next week includes intermittent showers and moderate temperatures, ideal for crop growth. (Simulated data, real data would come from IMD APIs)",
        "weather_general_prompt": "Please specify for which period or location you'd like the weather information. (Simulated data, real data would come from IMD APIs)",
        "fertilizer_recommendation": "Based on typical soil health recommendations for loamy soil, a balanced NPK (12-12-12) fertilizer is generally recommended for optimal growth. For precise guidance, a soil test is advisable. (Referring to Govt. Soil Health Card data principles)",
        "market_price_wheat": "The current market price for wheat in your nearest mandi is approximately ₹2,200 per quintal. (Data from Agmarknet & e-NAM APIs)",
        "market_price_rice": "Rice (Basmati) is currently trading at around ₹3,500 per quintal in major markets. (Data from Agmarknet & e-NAM APIs)",
        "market_price_prompt": "Please specify the crop for which you'd like the market price.",
        "pest_disease_recommendation": "If you suspect a pest or disease, please use the 'detect_pest_disease' feature by uploading an image for an accurate diagnosis and recommendation.",
        "fallback_response": "I'm sorry, I don't have specific information on that. Could you please rephrase your question or ask about weather, soil, market prices, pests, or crop recommendations?",
        "greeting": "Hello! I'm Krishimitra. How can I help you today?"
    },
    "hi": {
        "crop_recommendation_prompt": "आपको सर्वोत्तम फसल की सिफारिश{location_info} देने के लिए, मुझे आपकी मिट्टी का प्रकार और हालिया मौसम पैटर्न जानने की आवश्यकता है। अधिक व्यक्तिगत सलाह के लिए आप विशिष्ट मापदंडों के साथ 'predict_yield' सुविधा का उपयोग कर सकते हैं।",
        "weather_raebareli": "आज{location_query} का मौसम धूप वाला है, अधिकतम 32°C और न्यूनतम 22°C तापमान के साथ। बारिश की संभावना कम है। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "weather_location_prompt": "मौसम की जानकारी प्रदान करने के लिए, कृपया एक शहर या स्थान निर्दिष्ट करें। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "weather_today": "आज का मौसम धूप वाला है, अधिकतम 30°C और न्यूनतम 20°C तापमान के साथ। शाम को हल्की बारिश की 10% संभावना है। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "weather_next_week": "अगले सप्ताह के पूर्वानुमान में रुक-रुक कर बारिश और मध्यम तापमान शामिल है, जो फसल वृद्धि के लिए आदर्श है। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "weather_general_prompt": "कृपया उस अवधि या स्थान को निर्दिष्ट करें जिसके लिए आप मौसम की जानकारी चाहते हैं। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "fertilizer_recommendation": "दोमट मिट्टी के लिए विशिष्ट मिट्टी स्वास्थ्य सिफारिशों के आधार पर, इष्टतम वृद्धि के लिए आमतौर पर एक संतुलित एनपीके (12-12-12) उर्वरक की सिफारिश की जाती है। सटीक मार्गदर्शन के लिए, मिट्टी परीक्षण उचित है। (सरकारी मृदा स्वास्थ्य कार्ड डेटा सिद्धांतों का जिक्र करते हुए)",
        "market_price_wheat": "आपके निकटतम मंडी में गेहूं का वर्तमान बाजार मूल्य लगभग ₹2,200 प्रति क्विंटल है। (एगमार्कनेट और ई-नाम एपीआई से डेटा)",
        "market_price_rice": "प्रमुख बाजारों में चावल (बासमती) वर्तमान में लगभग ₹3,500 प्रति क्विंटल पर कारोबार कर रहा है। (एगमार्कनेट और ई-नाम एपीआई से डेटा)",
        "market_price_prompt": "कृपया उस फसल का नाम बताएं जिसके लिए आप बाजार मूल्य चाहते हैं।",
        "pest_disease_recommendation": "यदि आपको किसी कीट या बीमारी का संदेह है, तो सटीक निदान और सिफारिश के लिए कृपया एक छवि अपलोड करके 'detect_pest_disease' सुविधा का उपयोग करें।",
        "fallback_response": "मुझे क्षमा करें, मेरे पास उस पर विशिष्ट जानकारी नहीं है। क्या आप अपने प्रश्न को फिर से दोहरा सकते हैं या मौसम, मिट्टी, बाजार कीमतों, कीटों या फसल की सिफारिशों के बारे में पूछ सकते हैं?",
        "greeting": "नमस्ते! मैं कृषि मित्र हूँ। आज मैं आपकी कैसे सहायता कर सकता हूँ?"
    }
}

def get_chatbot_response(user_query, language="en"):
    lang_data = TRANSLATIONS.get(language, TRANSLATIONS["en"])
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
        
        return lang_data["crop_recommendation_prompt"].format(location_info=location_info)
    
    elif "weather" in user_query_lower:
        location_query = ""
        if "raebareli" in user_query_lower:
            location_query = " in Raebareli"
            return lang_data["weather_raebareli"].format(location_query=location_query)
        elif "location" in user_query_lower or "city" in user_query_lower or "pincode" in user_query_lower:
            return lang_data["weather_location_prompt"]
        elif "today" in user_query_lower:
            return lang_data["weather_today"]
        elif "next week" in user_query_lower:
            return lang_data["weather_next_week"]
        return lang_data["weather_general_prompt"]
    
    elif "fertilizer" in user_query_lower or "soil health" in user_query_lower:
        return lang_data["fertilizer_recommendation"]

    elif "market price" in user_query_lower or "mandi" in user_query_lower:
        if "wheat" in user_query_lower:
            return lang_data["market_price_wheat"]
        elif "rice" in user_query_lower:
            return lang_data["market_price_rice"]
        return lang_data["market_price_prompt"]

    elif "pest" in user_query_lower or "disease" in user_query_lower:
        return lang_data["pest_disease_recommendation"]

    return lang_data["fallback_response"]
