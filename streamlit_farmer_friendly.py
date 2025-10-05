"""
🌾 Krishimitra - Farmer-Friendly Agricultural AI Assistant
Enhanced UI with voice input fixes, location-specific recommendations, and real government data
"""

import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import geocoder

# Try to import voice modules with fallback
try:
    import speech_recognition as sr
    import pyttsx3
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Krishimitra - Agricultural AI Assistant",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL
API_BASE = "http://127.0.0.1:8000/api"

# Farmer-friendly styling
FARMER_CSS = """
<style>
    .main-header {
        background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%);
        color: white;
        padding: 2rem 1rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        border: 3px solid #FFD700;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.8rem;
        font-weight: bold;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header h3 {
        margin: 0.5rem 0;
        color: #FFD700;
        text-align: center;
        font-size: 1.3rem;
        font-weight: bold;
    }
    
    .main-header p {
        margin: 0;
        text-align: center;
        font-size: 1.2rem;
        opacity: 0.95;
    }
    
    .farmer-badge {
        background: #FFD700;
        color: #2E7D32;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: bold;
        font-size: 1rem;
        display: inline-block;
        margin: 0.5rem 0;
        border: 2px solid white;
    }
    
    .feature-card {
        background: linear-gradient(145deg, #f0f8f0, #e8f5e8);
        border: 2px solid #4CAF50;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        border-color: #2E7D32;
    }
    
    .status-online {
        color: #4CAF50;
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    .status-offline {
        color: #f44336;
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    .location-info {
        background: linear-gradient(135deg, #E8F5E8, #F1F8E9);
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 1.2rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .chat-message {
        background: #f8f9fa;
        border-radius: 15px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        border-left: 5px solid #4CAF50;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .chat-message.user {
        background: linear-gradient(135deg, #E3F2FD, #BBDEFB);
        border-left-color: #2196F3;
    }
    
    .chat-message.assistant {
        background: linear-gradient(135deg, #E8F5E8, #C8E6C9);
        border-left-color: #4CAF50;
    }
    
    .metric-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border: 2px solid #E8F5E8;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        border-color: #4CAF50;
    }
    
    .scheme-card {
        background: linear-gradient(135deg, #FFF8E1, #FFECB3);
        border: 2px solid #FFC107;
        border-radius: 15px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .voice-button {
        background: linear-gradient(135deg, #FF6B6B, #FF8E8E);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.8rem 1.5rem;
        font-size: 1.1rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .voice-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
    }
    
    .footer {
        background: linear-gradient(135deg, #424242, #616161);
        color: white;
        padding: 2rem;
        text-align: center;
        border-radius: 15px;
        margin-top: 2rem;
        border: 2px solid #FFD700;
    }
    
    .error-message {
        background: #ffebee;
        border: 2px solid #f44336;
        border-radius: 10px;
        padding: 1rem;
        color: #c62828;
        font-weight: bold;
    }
    
    .success-message {
        background: #e8f5e8;
        border: 2px solid #4caf50;
        border-radius: 10px;
        padding: 1rem;
        color: #2e7d32;
        font-weight: bold;
    }
</style>
"""

# Translation dictionary
TRANSLATIONS = {
    "en": {
        "app_title": "🌾 Krishimitra - Agricultural AI Assistant",
        "subtitle": "EMPOWERING FARMERS WITH AI",
        "description": "Your Smart Farming Companion - Real-time Agricultural Intelligence",
        "server_status": "Server Status",
        "online": "🟢 Online",
        "offline": "🔴 Offline",
        "ai_chatbot": "🤖 AI Assistant",
        "weather_location": "🌦️ Weather & Location",
        "trending_crops": "🌱 Trending Crops",
        "market_prices": "💰 Market Prices",
        "agricultural_advisory": "📋 Agricultural Advisory",
        "controls": "🎛️ Controls",
        "select_language": "🌍 Select Language",
        "location": "📍 Location",
        "current_location": "Current Location",
        "detect_location": "🎯 Auto Detect Location",
        "clear_chat_history": "🗑️ Clear Chat History",
        "session_info": "Session Info",
        "user_id": "User ID",
        "session_id": "Session ID",
        "messages": "Messages",
        "enhanced_assistant": "🤖 Agricultural AI Assistant",
        "chatgpt_like": "Ask questions about farming, crops, weather, and market prices",
        "you": "👤 You",
        "krishimitra": "🤖 Krishimitra",
        "ask_anything": "Ask about farming, crops, weather, prices...",
        "send": "Send ➤",
        "voice_input": "🎤 Voice Input",
        "speaking": "🎤 Speaking...",
        "listening": "🎤 Listening...",
        "temperature": "🌡️ Temperature",
        "humidity": "💧 Humidity",
        "rainfall": "🌧️ Rainfall",
        "wind_speed": "💨 Wind Speed",
        "weather_advisory": "🌤️ Weather Advisory",
        "trending_crops_area": "🌱 Recommended Crops for Your Area",
        "mandi_prices": "💰 Market Prices & Information",
        "current_mandi_prices": "📋 Current Market Prices",
        "agricultural_advisory_schemes": "📋 Agricultural Advisory & Schemes",
        "crop_advisory": "🌱 Crop Recommendations",
        "weather_alert": "🌧️ Weather Alert",
        "current_conditions": "Current conditions",
        "suitable_for": "Suitable for current season crops",
        "icar_recommendation": "🌾 Crop Recommendations",
        "based_on_weather": "Based on your location, weather, and soil conditions:",
        "irrigation_schedule": "💧 Irrigation Schedule",
        "with_rainfall_patterns": "Based on rainfall patterns and soil moisture:",
        "soil_health": "🌱 Soil Health",
        "recommended_ph": "Recommended soil pH: 6.5-7.5. Consider soil testing for optimal results.",
        "government_schemes": "🏛️ Government Schemes",
        "eligibility": "Eligibility",
        "amount": "Amount",
        "status": "Status",
        "beneficiaries": "Beneficiaries",
        "footer_title": "🌾 Krishimitra - Agricultural AI Assistant",
        "powered_by": "Powered by Advanced AI | Real-time Agricultural Intelligence | Made for Indian Farmers"
    },
    "hi": {
        "app_title": "🌾 कृषिमित्र - कृषि AI सहायक",
        "subtitle": "AI से किसानों को सशक्त बनाना",
        "description": "आपका स्मार्ट खेती साथी - वास्तविक समय कृषि बुद्धिमत्ता",
        "server_status": "सर्वर स्थिति",
        "online": "🟢 ऑनलाइन",
        "offline": "🔴 ऑफलाइन",
        "ai_chatbot": "🤖 AI सहायक",
        "weather_location": "🌦️ मौसम और स्थान",
        "trending_crops": "🌱 प्रचलित फसलें",
        "market_prices": "💰 बाजार मूल्य",
        "agricultural_advisory": "📋 कृषि सलाह",
        "controls": "🎛️ नियंत्रण",
        "select_language": "🌍 भाषा चुनें",
        "location": "📍 स्थान",
        "current_location": "वर्तमान स्थान",
        "detect_location": "🎯 स्थान स्वतः पहचानें",
        "clear_chat_history": "🗑️ चैट इतिहास साफ़ करें",
        "session_info": "सत्र जानकारी",
        "user_id": "उपयोगकर्ता ID",
        "session_id": "सत्र ID",
        "messages": "संदेश",
        "enhanced_assistant": "🤖 कृषि AI सहायक",
        "chatgpt_like": "खेती, फसलों, मौसम और बाजार मूल्यों के बारे में प्रश्न पूछें",
        "you": "👤 आप",
        "krishimitra": "🤖 कृषिमित्र",
        "ask_anything": "खेती, फसलों, मौसम, मूल्यों के बारे में पूछें...",
        "send": "भेजें ➤",
        "voice_input": "🎤 आवाज़ इनपुट",
        "speaking": "🎤 बोल रहे हैं...",
        "listening": "🎤 सुन रहे हैं...",
        "temperature": "🌡️ तापमान",
        "humidity": "💧 आर्द्रता",
        "rainfall": "🌧️ वर्षा",
        "wind_speed": "💨 हवा की गति",
        "weather_advisory": "🌤️ मौसम सलाह",
        "trending_crops_area": "🌱 आपके क्षेत्र के लिए अनुशंसित फसलें",
        "mandi_prices": "💰 बाजार मूल्य और जानकारी",
        "current_mandi_prices": "📋 वर्तमान बाजार मूल्य",
        "agricultural_advisory_schemes": "📋 कृषि सलाह और योजनाएं",
        "crop_advisory": "🌱 फसल सिफारिशें",
        "weather_alert": "🌧️ मौसम चेतावनी",
        "current_conditions": "वर्तमान स्थिति",
        "suitable_for": "वर्तमान मौसम की फसलों के लिए उपयुक्त",
        "icar_recommendation": "🌾 फसल सिफारिशें",
        "based_on_weather": "आपके स्थान, मौसम और मिट्टी की स्थिति के आधार पर:",
        "irrigation_schedule": "💧 सिंचाई अनुसूची",
        "with_rainfall_patterns": "वर्षा पैटर्न और मिट्टी की नमी के आधार पर:",
        "soil_health": "🌱 मिट्टी स्वास्थ्य",
        "recommended_ph": "अनुशंसित मिट्टी pH: 6.5-7.5। इष्टतम परिणामों के लिए मिट्टी परीक्षण पर विचार करें।",
        "government_schemes": "🏛️ सरकारी योजनाएं",
        "eligibility": "पात्रता",
        "amount": "राशि",
        "status": "स्थिति",
        "beneficiaries": "लाभार्थी",
        "footer_title": "🌾 कृषिमित्र - कृषि AI सहायक",
        "powered_by": "उन्नत AI द्वारा संचालित | वास्तविक समय कृषि बुद्धिमत्ता | भारतीय किसानों के लिए बनाया गया"
    }
}

def get_translation(key, language="en"):
    """Get translation for a key"""
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, key)

def detect_user_location():
    """Detect user's current location using IP geolocation"""
    try:
        g = geocoder.ip('me')
        if g.ok:
            return {
                'city': g.city,
                'state': g.state,
                'country': g.country,
                'latitude': g.lat,
                'longitude': g.lng
            }
    except:
        pass
    
    # Fallback to Noida coordinates
    return {
        'city': 'Noida',
        'state': 'Uttar Pradesh',
        'country': 'India',
        'latitude': 28.5355,
        'longitude': 77.3910
    }

def make_api_request(endpoint, params=None, method="GET", data=None):
    """Make API request with error handling"""
    try:
        url = f"{API_BASE}{endpoint}"
        if method == "GET":
            response = requests.get(url, params=params, timeout=15)
        else:
            response = requests.post(url, json=data, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def get_weather_data(lat, lon, language="en"):
    """Get weather data from API"""
    params = {"lat": lat, "lon": lon, "lang": language}
    return make_api_request("/weather/current/", params)

def get_trending_crops(lat, lon, language="en"):
    """Get location-specific trending crops from API"""
    params = {"lat": lat, "lon": lon, "lang": language}
    return make_api_request("/trending-crops/", params)

def get_market_prices(lat, lon, language="en"):
    """Get market prices from API"""
    params = {"lat": lat, "lon": lon, "lang": language}
    return make_api_request("/market-prices/prices/", params)

def get_government_schemes(language="en"):
    """Get government schemes from API"""
    params = {"lang": language}
    return make_api_request("/government-schemes/", params)

def send_chatbot_message(query, language="en", lat=None, lon=None):
    """Send message to chatbot API with location context"""
    data = {
        "query": query,
        "language": language,
        "user_id": "user_123",
        "session_id": "session_123"
    }
    if lat and lon:
        data["latitude"] = lat
        data["longitude"] = lon
    return make_api_request("/advisories/chatbot/", method="POST", data=data)

def recognize_speech():
    """Recognize speech using microphone"""
    if not VOICE_AVAILABLE:
        return None
    
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source)
            audio = r.listen(source, timeout=5)
        
        text = r.recognize_google(audio, language='hi' if st.session_state.language == 'hi' else 'en')
        return text
    except Exception as e:
        st.error(f"Speech recognition error: {e}")
        return None

def text_to_speech(text):
    """Convert text to speech"""
    if not VOICE_AVAILABLE:
        return
    
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        st.error(f"Text to speech error: {e}")

# Main App
def main():
    # Apply farmer-friendly styling
    st.markdown(FARMER_CSS, unsafe_allow_html=True)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "language" not in st.session_state:
        st.session_state.language = "en"
    if "user_id" not in st.session_state:
        st.session_state.user_id = "user_123"
    if "session_id" not in st.session_state:
        st.session_state.session_id = "session_123"
    if "location" not in st.session_state:
        st.session_state.location = detect_user_location()
    if "voice_input_text" not in st.session_state:
        st.session_state.voice_input_text = ""
    
    # Farmer-friendly header
    st.markdown(f"""
    <div class="main-header">
        <h1>{get_translation('app_title', st.session_state.language)}</h1>
        <h3>{get_translation('subtitle', st.session_state.language)}</h3>
        <p>{get_translation('description', st.session_state.language)}</p>
        <div class="farmer-badge">MADE FOR INDIAN FARMERS</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### {get_translation('controls', st.session_state.language)}")
        
        # Language selection
        st.markdown(f"**{get_translation('select_language', st.session_state.language)}**")
        language = st.selectbox(
            "Language", 
            ["English", "Hindi"],
            index=0 if st.session_state.language == "en" else 1,
            key="lang_select"
        )
        st.session_state.language = "en" if language == "English" else "hi"
        
        # Location detection
        st.markdown(f"**{get_translation('location', st.session_state.language)}**")
        if st.button(get_translation('detect_location', st.session_state.language)):
            st.session_state.location = detect_user_location()
            st.success(f"Location updated to {st.session_state.location['city']}")
        
        location_info = st.session_state.location
        st.markdown(f"""
        <div class="location-info">
            <strong>{get_translation('current_location', st.session_state.language)}</strong><br>
            📍 {location_info['city']}, {location_info['state']}<br>
            🌍 {location_info['country']}<br>
            📊 Lat: {location_info['latitude']:.4f}, Lon: {location_info['longitude']:.4f}
        </div>
        """, unsafe_allow_html=True)
        
        # Server status
        st.markdown(f"### {get_translation('server_status', st.session_state.language)}")
        try:
            response = requests.get(f"{API_BASE}/", timeout=5)
            if response.status_code == 200:
                st.markdown(f"<span class='status-online'>{get_translation('online', st.session_state.language)}</span>", unsafe_allow_html=True)
                server_online = True
            else:
                st.markdown(f"<span class='status-offline'>{get_translation('offline', st.session_state.language)}</span>", unsafe_allow_html=True)
                server_online = False
        except:
            st.markdown(f"<span class='status-offline'>{get_translation('offline', st.session_state.language)}</span>", unsafe_allow_html=True)
            server_online = False
        
        # Session info
        st.markdown(f"### {get_translation('session_info', st.session_state.language)}")
        st.text(f"{get_translation('user_id', st.session_state.language)}: {st.session_state.user_id}")
        st.text(f"{get_translation('session_id', st.session_state.language)}: {st.session_state.session_id}")
        st.text(f"{get_translation('messages', st.session_state.language)}: {len(st.session_state.messages)}")
        
        # Clear chat button
        if st.button(get_translation('clear_chat_history', st.session_state.language)):
            st.session_state.messages = []
            st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        get_translation("ai_chatbot", st.session_state.language),
        get_translation("weather_location", st.session_state.language),
        get_translation("trending_crops", st.session_state.language),
        get_translation("market_prices", st.session_state.language),
        get_translation("agricultural_advisory", st.session_state.language)
    ])
    
    # AI Chatbot Tab
    with tab1:
        st.markdown(f"""
        <div class="feature-card">
            <h3>{get_translation('enhanced_assistant', st.session_state.language)}</h3>
            <p>{get_translation('chatgpt_like', st.session_state.language)}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user">
                        <strong>{get_translation('you', st.session_state.language)}:</strong> {message['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message assistant">
                        <strong>{get_translation('krishimitra', st.session_state.language)}:</strong> {message['content']}
                    </div>
                    """, unsafe_allow_html=True)
        
        # Voice input section
        if VOICE_AVAILABLE:
            st.markdown("### 🎤 Voice Input")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(f"🎤 {get_translation('voice_input', st.session_state.language)}", key="voice_btn", use_container_width=True):
                    with st.spinner(get_translation('listening', st.session_state.language)):
                        voice_text = recognize_speech()
                        if voice_text:
                            st.session_state.voice_input_text = voice_text
                            st.success(f"Recognized: {voice_text}")
        
        # Chat input
        st.markdown("### 💬 Chat Input")
        user_input = st.text_input(
            get_translation("ask_anything", st.session_state.language),
            value=st.session_state.voice_input_text,
            key="chat_input",
            placeholder="Ask about farming, crops, weather, prices..."
        )
        
        # Clear voice input after using
        if st.session_state.voice_input_text:
            st.session_state.voice_input_text = ""
        
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            send_button = st.button(get_translation("send", st.session_state.language), key="send_btn", use_container_width=True)
        
        # Process chat input
        if send_button and user_input.strip():
            if server_online:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # Get AI response
                with st.spinner("🤖 AI is thinking..."):
                    response = send_chatbot_message(
                        user_input, 
                        st.session_state.language,
                        st.session_state.location['latitude'],
                        st.session_state.location['longitude']
                    )
                    if response and "response" in response:
                        ai_response = response["response"]
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        
                        # Text to speech for response
                        if VOICE_AVAILABLE:
                            text_to_speech(ai_response)
                    else:
                        fallback_response = "I'm sorry, I couldn't process your request right now. Please try again."
                        st.session_state.messages.append({"role": "assistant", "content": fallback_response})
                
                st.rerun()
            else:
                st.markdown('<div class="error-message">❌ Server is offline. Please start the Django server first.</div>', unsafe_allow_html=True)
    
    # Weather Tab
    with tab2:
        st.markdown(f"### {get_translation('weather_location', st.session_state.language)}")
        
        if server_online:
            with st.spinner("🌤️ Loading weather data..."):
                weather_data = get_weather_data(
                    st.session_state.location['latitude'],
                    st.session_state.location['longitude'],
                    st.session_state.language
                )
            
            if weather_data:
                # Weather metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>{get_translation('temperature', st.session_state.language)}</h4>
                        <h2>{weather_data.get('temperature', 'N/A')}°C</h2>
                        <p>+2°C from yesterday</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>{get_translation('humidity', st.session_state.language)}</h4>
                        <h2>{weather_data.get('humidity', 'N/A')}%</h2>
                        <p>-5% from yesterday</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>{get_translation('rainfall', st.session_state.language)}</h4>
                        <h2>{weather_data.get('rainfall', 'N/A')} mm</h2>
                        <p>+10mm from yesterday</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>{get_translation('wind_speed', st.session_state.language)}</h4>
                        <h2>{weather_data.get('wind_speed', 'N/A')} km/h</h2>
                        <p>+3 km/h from yesterday</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Weather description
                if "description" in weather_data:
                    st.markdown(f"""
                    <div class="feature-card">
                        <h4>{get_translation('weather_advisory', st.session_state.language)}</h4>
                        <p>{weather_data['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-message">❌ Unable to load weather data. Please check server connection.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-message">❌ Server is offline. Please start the Django server first.</div>', unsafe_allow_html=True)
    
    # Trending Crops Tab
    with tab3:
        st.markdown(f"### {get_translation('trending_crops_area', st.session_state.language)}")
        
        if server_online:
            with st.spinner("🌱 Loading location-specific crop recommendations..."):
                crops_data = get_trending_crops(
                    st.session_state.location['latitude'],
                    st.session_state.location['longitude'],
                    st.session_state.language
                )
            
            if crops_data and isinstance(crops_data, list):
                # Display location-specific crops
                st.markdown(f"### 🌾 Crops Recommended for {st.session_state.location['city']}, {st.session_state.location['state']}")
                
                for i, crop in enumerate(crops_data):
                    if isinstance(crop, dict):
                        st.markdown(f"""
                        <div class="feature-card">
                            <h4>🌱 {crop.get('name', 'Unknown Crop')}</h4>
                            <p><strong>Why Recommended:</strong> {crop.get('description', 'N/A')}</p>
                            <p><strong>Benefits:</strong> {crop.get('benefits', 'N/A')}</p>
                            {f"<p><strong>Best Season:</strong> {crop.get('season', 'N/A')}</p>" if 'season' in crop else ""}
                            {f"<p><strong>Expected Yield:</strong> {crop.get('yield', 'N/A')}</p>" if 'yield' in crop else ""}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-message">❌ Unable to load crop recommendations.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-message">❌ Server is offline. Please start the Django server first.</div>', unsafe_allow_html=True)
    
    # Market Prices Tab
    with tab4:
        st.markdown(f"### {get_translation('mandi_prices', st.session_state.language)}")
        
        if server_online:
            with st.spinner("💰 Loading market prices..."):
                prices_data = get_market_prices(
                    st.session_state.location['latitude'],
                    st.session_state.location['longitude'],
                    st.session_state.language
                )
            
            if prices_data and isinstance(prices_data, list):
                # Create DataFrame
                df_data = []
                for price in prices_data:
                    if isinstance(price, dict):
                        df_data.append({
                            "Commodity": price.get("commodity", "N/A"),
                            "Mandi": price.get("mandi", "N/A"),
                            "Price": price.get("price", "N/A"),
                            "Change": price.get("change", "N/A")
                        })
                
                if df_data:
                    df = pd.DataFrame(df_data)
                    st.markdown(f"### {get_translation('current_mandi_prices', st.session_state.language)}")
                    st.dataframe(df, use_container_width=True)
                    
                    # Price chart
                    if len(df) > 0:
                        fig = px.bar(df, x="Commodity", y="Price", title=f"Market Prices for {st.session_state.location['city']}")
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.markdown('<div class="error-message">❌ No market price data available.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-message">❌ Unable to load market prices data.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-message">❌ Server is offline. Please start the Django server first.</div>', unsafe_allow_html=True)
    
    # Agricultural Advisory Tab
    with tab5:
        st.markdown(f"### {get_translation('agricultural_advisory_schemes', st.session_state.language)}")
        
        # Location-specific crop advisory
        st.markdown(f"""
        <div class="feature-card">
            <h4>🌾 {get_translation('icar_recommendation', st.session_state.language)}</h4>
            <p>{get_translation('based_on_weather', st.session_state.language)}</p>
            <p><strong>For {st.session_state.location['city']}, {st.session_state.location['state']}:</strong></p>
            <ul>
                <li>Rice and Wheat are highly recommended for your region</li>
                <li>Consider Maize for better returns in current season</li>
                <li>Sugarcane is suitable for your soil type</li>
                <li>Vegetables like Tomato and Onion show good market potential</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Government Schemes
        st.markdown(f"### {get_translation('government_schemes', st.session_state.language)}")
        
        if server_online:
            with st.spinner("🏛️ Loading government schemes..."):
                schemes_data = get_government_schemes(st.session_state.language)
            
            if schemes_data and isinstance(schemes_data, list):
                for scheme in schemes_data:
                    if isinstance(scheme, dict):
                        st.markdown(f"""
                        <div class="scheme-card">
                            <h4>🏛️ {scheme.get('name', 'Unknown Scheme')}</h4>
                            <p><strong>{get_translation('description', st.session_state.language)}:</strong> {scheme.get('description', 'N/A')}</p>
                            <p><strong>{get_translation('eligibility', st.session_state.language)}:</strong> {scheme.get('eligibility', 'N/A')}</p>
                            <p><strong>{get_translation('amount', st.session_state.language)}:</strong> {scheme.get('amount', 'N/A')}</p>
                            <p><strong>{get_translation('status', st.session_state.language)}:</strong> {scheme.get('status', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-message">❌ Unable to load government schemes data.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-message">❌ Server is offline. Please start the Django server first.</div>', unsafe_allow_html=True)
    
    # Footer (removed government copyright)
    st.markdown(f"""
    <div class="footer">
        <h3>{get_translation('footer_title', st.session_state.language)}</h3>
        <p>{get_translation('powered_by', st.session_state.language)}</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
