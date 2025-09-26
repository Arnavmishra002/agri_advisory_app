
from .government_apis import ICARDataIntegration, NABARDInsights
from .fertilizer_recommendations import FertilizerRecommendationEngine

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

def get_crop_substitutions(soil_type, market_prices=None):
    """Provides crop substitution recommendations based on soil type and market prices.
    
    This function suggests alternative crops that are:
    1. Suitable for the given soil type
    2. Currently profitable based on market prices
    3. Provide good yield potential
    """
    # Crop substitution database based on soil type and profitability
    crop_substitutions = {
        "loamy": {
            "high_profit": ["Tomato", "Onion", "Potato", "Maize"],
            "medium_profit": ["Wheat", "Sugarcane", "Cotton", "Soybean"],
            "low_profit": ["Rice", "Barley", "Mustard"]
        },
        "clayey": {
            "high_profit": ["Rice", "Sugarcane", "Potato", "Onion"],
            "medium_profit": ["Wheat", "Maize", "Soybean", "Cotton"],
            "low_profit": ["Barley", "Mustard", "Tomato"]
        },
        "sandy": {
            "high_profit": ["Groundnut", "Sunflower", "Maize", "Cotton"],
            "medium_profit": ["Wheat", "Barley", "Soybean", "Potato"],
            "low_profit": ["Rice", "Sugarcane", "Onion"]
        },
        "silty": {
            "high_profit": ["Wheat", "Maize", "Soybean", "Potato"],
            "medium_profit": ["Rice", "Cotton", "Onion", "Tomato"],
            "low_profit": ["Sugarcane", "Barley", "Mustard"]
        }
    }
    
    # Default to loamy if soil type not found
    soil_crops = crop_substitutions.get(soil_type.lower(), crop_substitutions["loamy"])
    
    # Combine recommendations
    recommendations = []
    recommendations.extend([f"{crop} (High Profit)" for crop in soil_crops["high_profit"][:2]])
    recommendations.extend([f"{crop} (Good Profit)" for crop in soil_crops["medium_profit"][:2]])
    
    return recommendations


TRANSLATIONS = {
    "en": {
        "crop_recommendation_prompt": "To give you the best crop recommendation{location_info}, I need to know your soil type and recent weather patterns. You can use the 'predict_yield' feature with specific parameters for more personalized advice.",
        "crop_substitution_prompt": "Based on your soil type and current market prices, here are some profitable crop alternatives: {substitutions}",
        "weather_raebareli": "The weather today{location_query} is sunny with a high of 32°C and a low of 22°C. There's a low chance of rain. (Simulated data, real data would come from IMD APIs)",
        "weather_location_prompt": "To provide weather, please specify a city or location. (Simulated data, real data would come from IMD APIs)",
        "weather_today": "The weather today is sunny with a high of 30°C and a low of 20°C. There's a 10% chance of light rain in the evening. (Simulated data, real data would come from IMD APIs)",
        "weather_next_week": "The forecast for next week includes intermittent showers and moderate temperatures, ideal for crop growth. (Simulated data, real data would come from IMD APIs)",
        "weather_general_prompt": "Please specify for which period or location you'd like the weather information. (Simulated data, real data would come from IMD APIs)",
        "fertilizer_recommendation": "I can provide detailed fertilizer recommendations based on your crop type, soil type, and season. Please specify your crop and soil type for personalized fertilizer guidance.",
        "market_price_wheat": "The current market price for wheat in your nearest mandi is approximately ₹2,200 per quintal. (Data from Agmarknet & e-NAM APIs)",
        "market_price_rice": "Rice (Basmati) is currently trading at around ₹3,500 per quintal in major markets. (Data from Agmarknet & e-NAM APIs)",
        "market_price_prompt": "Please specify the crop for which you'd like the market price.",
        "fallback_response": "I'm sorry, I don't have specific information on that. Could you please rephrase your question or ask about weather, soil, market prices, or crop recommendations?",
        "greeting": "Hello! I'm Krishimitra. I can help you with crop recommendations, soil analysis, and weather-based farming advice."
    },
    "hi": {
        "crop_recommendation_prompt": "आपको सर्वोत्तम फसल की सिफारिश{location_info} देने के लिए, मुझे आपकी मिट्टी का प्रकार और हालिया मौसम पैटर्न जानने की आवश्यकता है। अधिक व्यक्तिगत सलाह के लिए आप विशिष्ट मापदंडों के साथ 'predict_yield' सुविधा का उपयोग कर सकते हैं।",
        "crop_substitution_prompt": "आपकी मिट्टी के प्रकार और वर्तमान बाजार कीमतों के आधार पर, यहाँ कुछ लाभदायक फसल विकल्प हैं: {substitutions}",
        "weather_raebareli": "आज{location_query} का मौसम धूप वाला है, अधिकतम 32°C और न्यूनतम 22°C तापमान के साथ। बारिश की संभावना कम है। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "weather_location_prompt": "मौसम की जानकारी प्रदान करने के लिए, कृपया एक शहर या स्थान निर्दिष्ट करें। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "weather_today": "आज का मौसम धूप वाला है, अधिकतम 30°C और न्यूनतम 20°C तापमान के साथ। शाम को हल्की बारिश की 10% संभावना है। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "weather_next_week": "अगले सप्ताह के पूर्वानुमान में रुक-रुक कर बारिश और मध्यम तापमान शामिल है, जो फसल वृद्धि के लिए आदर्श है। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "weather_general_prompt": "कृपया उस अवधि या स्थान को निर्दिष्ट करें जिसके लिए आप मौसम की जानकारी चाहते हैं। (सिम्युलेटेड डेटा, वास्तविक डेटा IMD API से आएगा)",
        "fertilizer_recommendation": "मैं आपकी फसल के प्रकार, मिट्टी के प्रकार और मौसम के आधार पर विस्तृत उर्वरक सिफारिशें प्रदान कर सकता हूँ। व्यक्तिगत उर्वरक मार्गदर्शन के लिए कृपया अपनी फसल और मिट्टी का प्रकार बताएं।",
        "market_price_wheat": "आपके निकटतम मंडी में गेहूं का वर्तमान बाजार मूल्य लगभग ₹2,200 प्रति क्विंटल है। (एगमार्कनेट और ई-नाम एपीआई से डेटा)",
        "market_price_rice": "प्रमुख बाजारों में चावल (बासमती) वर्तमान में लगभग ₹3,500 प्रति क्विंटल पर कारोबार कर रहा है। (एगमार्कनेट और ई-नाम एपीआई से डेटा)",
        "market_price_prompt": "कृपया उस फसल का नाम बताएं जिसके लिए आप बाजार मूल्य चाहते हैं।",
        "fallback_response": "मुझे क्षमा करें, मेरे पास उस पर विशिष्ट जानकारी नहीं है। क्या आप अपने प्रश्न को फिर से दोहरा सकते हैं या मौसम, मिट्टी, बाजार कीमतों या फसल की सिफारिशों के बारे में पूछ सकते हैं?",
        "greeting": "नमस्ते! मैं कृषि मित्र हूँ। मैं आपको फसल की सिफारिश, मिट्टी और मौसम के आधार पर सलाह दे सकता हूँ।"
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
    
    # Handle crop substitution queries
    if ("crop" in user_query_lower and ("substitute" in user_query_lower or "alternative" in user_query_lower or "replace" in user_query_lower)):
        # Extract soil type from query
        soil_type = "loamy"  # default
        if "clayey" in user_query_lower or "clay" in user_query_lower:
            soil_type = "clayey"
        elif "sandy" in user_query_lower:
            soil_type = "sandy"
        elif "silty" in user_query_lower or "silt" in user_query_lower:
            soil_type = "silty"
        
        substitutions = get_crop_substitutions(soil_type)
        substitutions_text = ", ".join(substitutions)
        return lang_data["crop_substitution_prompt"].format(substitutions=substitutions_text)
    
    # Prioritize specific crop recommendation queries
    elif ("crop" in user_query_lower and "plant" in user_query_lower) or "what to plant" in user_query_lower or "crop recommendation" in user_query_lower:
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
    
    elif "fertilizer" in user_query_lower or "soil health" in user_query_lower or "fertilizer recommendation" in user_query_lower:
        # Extract crop and soil information from query
        crop_type = None
        soil_type = "loamy"  # default
        season = "kharif"  # default
        
        # Extract crop type
        crops = ["wheat", "rice", "maize", "sugarcane", "cotton", "tomato", "potato", "onion"]
        for crop in crops:
            if crop in user_query_lower:
                crop_type = crop
                break
        
        # Extract soil type
        if "clayey" in user_query_lower or "clay" in user_query_lower:
            soil_type = "clayey"
        elif "sandy" in user_query_lower:
            soil_type = "sandy"
        elif "silty" in user_query_lower or "silt" in user_query_lower:
            soil_type = "silty"
        
        # Extract season
        if "rabi" in user_query_lower:
            season = "rabi"
        elif "zaid" in user_query_lower:
            season = "zaid"
        
        if crop_type:
            # Get detailed fertilizer recommendation
            fertilizer_engine = FertilizerRecommendationEngine()
            recommendation = fertilizer_engine.get_fertilizer_recommendation(
                crop_type, soil_type, season, 1.0, language
            )
            
            if "error" not in recommendation:
                # Format the recommendation for chatbot response
                response = f"Here's your personalized fertilizer recommendation for {crop_type} in {soil_type} soil during {season} season:\n\n"
                response += f"Primary Nutrients:\n"
                for nutrient, data in recommendation["nutrient_requirements"].items():
                    response += f"• {nutrient.title()}: {data['adjusted_amount']} {data['unit']}\n"
                
                response += f"\nRecommended Fertilizers: {', '.join(recommendation['recommended_fertilizers'])}\n"
                response += f"\nEstimated Cost: ₹{recommendation['cost_estimation']['total_cost']}\n"
                response += f"\nSource: {recommendation['source']}"
                
                if language == 'hi':
                    response = f"यहाँ आपके लिए {crop_type} के लिए {soil_type} मिट्टी में {season} मौसम के दौरान व्यक्तिगत उर्वरक सिफारिश है:\n\n"
                    response += f"प्राथमिक पोषक तत्व:\n"
                    for nutrient, data in recommendation["nutrient_requirements"].items():
                        response += f"• {nutrient.title()}: {data['adjusted_amount']} {data['unit']}\n"
                    
                    response += f"\nसुझाए गए उर्वरक: {', '.join(recommendation['recommended_fertilizers'])}\n"
                    response += f"\nअनुमानित लागत: ₹{recommendation['cost_estimation']['total_cost']}\n"
                    response += f"\nस्रोत: {recommendation['source']}"
                
                return response
        
        return lang_data["fertilizer_recommendation"]

    elif "market price" in user_query_lower or "mandi" in user_query_lower:
        if "wheat" in user_query_lower:
            return lang_data["market_price_wheat"]
        elif "rice" in user_query_lower:
            return lang_data["market_price_rice"]
        return lang_data["market_price_prompt"]


    return lang_data["fallback_response"]
