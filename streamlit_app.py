"""
🌾 Krishimitra - Enhanced Agricultural AI Assistant
Streamlit Frontend for Agricultural Chatbot Platform

Based on: https://github.com/shivamr021/KrishiMitra-AI
Enhanced with ChatGPT-like capabilities and 25+ language support
"""

import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import base64
from PIL import Image
import io

# Page configuration
st.set_page_config(
    page_title="🌾 Krishimitra - AI Agricultural Assistant",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        background: #f8f9fa;
    }
    
    .user-message {
        background: #e3f2fd;
        border-left-color: #2196F3;
        margin-left: 2rem;
    }
    
    .bot-message {
        background: #e8f5e8;
        border-left-color: #4CAF50;
        margin-right: 2rem;
    }
    
    .gov-badge {
        background: linear-gradient(135deg, #FFD700, #FFA000);
        color: #333;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 1rem;
    }
    
    .status-online {
        color: #4CAF50;
        font-weight: bold;
    }
    
    .status-offline {
        color: #f44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE = "http://localhost:8000/api"

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'session_id' not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time())}"
if 'user_id' not in st.session_state:
    st.session_state.user_id = f"user_{int(time.time())}"
if 'current_location' not in st.session_state:
    st.session_state.current_location = "Delhi"

def check_server_status():
    """Check if the backend server is running"""
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_weather_data():
    """Get weather data from API or return mock data"""
    try:
        response = requests.get(f"{API_BASE}/weather/current/?lat=28.6139&lon=77.2090&lang=en", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # Return mock data if API fails
    return {
        "temperature": "28°C",
        "humidity": "65%",
        "rainfall": "2.5mm",
        "wind_speed": "12 km/h",
        "advisory": "Moderate rainfall expected in the next 3 days. Suitable for kharif crops."
    }

def get_trending_crops():
    """Get trending crops data from API or return mock data"""
    try:
        response = requests.get(f"{API_BASE}/trending-crops/?lat=28.6139&lon=77.2090&lang=en", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # Return mock data
    return [
        {"name": "Wheat", "price": "₹2,450/quintal", "trend": "up", "change": "+2.1%"},
        {"name": "Rice", "price": "₹3,200/quintal", "trend": "up", "change": "+2.4%"},
        {"name": "Maize", "price": "₹1,800/quintal", "trend": "down", "change": "-1.4%"},
        {"name": "Cotton", "price": "₹6,500/quintal", "trend": "up", "change": "+3.2%"},
        {"name": "Sugarcane", "price": "₹315/quintal", "trend": "stable", "change": "0.0%"}
    ]

def get_market_prices():
    """Get market prices data from API or return mock data"""
    try:
        response = requests.get(f"{API_BASE}/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # Return mock data
    return [
        {"commodity": "Wheat", "mandi": "Delhi", "price": "₹2,450", "change": "+50", "change_percent": "+2.1%"},
        {"commodity": "Rice", "mandi": "Kolkata", "price": "₹3,200", "change": "+75", "change_percent": "+2.4%"},
        {"commodity": "Maize", "mandi": "Mumbai", "price": "₹1,800", "change": "-25", "change_percent": "-1.4%"},
        {"commodity": "Cotton", "mandi": "Ahmedabad", "price": "₹6,500", "change": "+200", "change_percent": "+3.2%"}
    ]

def send_chat_message(message, language="auto"):
    """Send message to chatbot API"""
    try:
        response = requests.post(
            f"{API_BASE}/advisories/chatbot/",
            json={
                "query": message,
                "language": language,
                "user_id": st.session_state.user_id,
                "session_id": st.session_state.session_id
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"response": f"API Error: {response.status_code}", "error": True}
    except Exception as e:
        return {"response": f"Connection Error: {str(e)}", "error": True}

# Main Header
st.markdown("""
<div class="main-header">
    <h1>🌾 Krishimitra - Enhanced Agricultural AI Assistant</h1>
    <div class="gov-badge">GOVERNMENT OF INDIA INITIATIVE</div>
    <p>ChatGPT-like AI with 25+ Language Support | Real-time Agricultural Intelligence</p>
</div>
""", unsafe_allow_html=True)

# Server Status
server_online = check_server_status()
status_color = "status-online" if server_online else "status-offline"
status_text = "🟢 Online" if server_online else "🔴 Offline"

st.markdown(f"""
<div style="text-align: center; margin-bottom: 2rem;">
    <h3>Server Status: <span class="{status_color}">{status_text}</span></h3>
    <p>Make sure the Django server is running: <code>python manage.py runserver 127.0.0.1:8000</code></p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🎛️ Controls")
    
    # Language Selection
    language = st.selectbox(
        "🌍 Select Language",
        ["auto", "en", "hi", "bn", "te", "ta", "gu", "mr", "kn", "ml"],
        format_func=lambda x: {
            "auto": "Auto-detect",
            "en": "English",
            "hi": "Hindi (हिन्दी)",
            "bn": "Bengali (বাংলা)",
            "te": "Telugu (తెలుగు)",
            "ta": "Tamil (தமிழ்)",
            "gu": "Gujarati (ગુજરાતી)",
            "mr": "Marathi (मराठी)",
            "kn": "Kannada (ಕನ್ನಡ)",
            "ml": "Malayalam (മലയാളം)"
        }[x]
    )
    
    # Location Input
    st.session_state.current_location = st.text_input(
        "📍 Location",
        value=st.session_state.current_location,
        placeholder="Enter your city, district, or pincode"
    )
    
    # Clear Chat
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
    
    # Session Info
    st.markdown("---")
    st.markdown("**Session Info:**")
    st.text(f"User ID: {st.session_state.user_id}")
    st.text(f"Session ID: {st.session_state.session_id}")
    st.text(f"Messages: {len(st.session_state.chat_history)}")

# Main Content Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🤖 AI Chatbot", 
    "🌦️ Weather & Location", 
    "🌱 Trending Crops", 
    "💰 Market Prices", 
    "📋 Agricultural Advisory"
])

# Tab 1: AI Chatbot
with tab1:
    st.header("🤖 Enhanced Agricultural AI Assistant")
    st.markdown("**ChatGPT-like conversations with 25+ language support**")
    
    # Chat Interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for i, message in enumerate(st.session_state.chat_history):
            if message["type"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>🤖 Krishimitra:</strong> {message["content"]}
                    <br><small>Language: {message.get('language', 'Unknown')} | 
                    Confidence: {message.get('confidence', 'Unknown')}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # Chat Input
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.text_input(
            "💬 Ask me anything about agriculture...",
            placeholder="What crops should I plant in Delhi?",
            key="chat_input"
        )
    
    with col2:
        send_button = st.button("Send ➤", type="primary", width='stretch')
    
    # Process message
    if (send_button or user_input) and user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            "type": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Show typing indicator
        with st.spinner("🤖 Krishimitra is thinking..."):
            # Send to chatbot
            response = send_chat_message(user_input, language)
            
            # Add bot response to history
            st.session_state.chat_history.append({
                "type": "bot",
                "content": response.get("response", "Sorry, I couldn't process your request."),
                "language": response.get("language", "Unknown"),
                "confidence": response.get("confidence", "Unknown"),
                "timestamp": datetime.now().isoformat()
            })
        
        # Clear input and rerun
        st.rerun()

# Tab 2: Weather & Location
with tab2:
    st.header("🌦️ Weather & Location Information")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📍 Current Location: {st.session_state.current_location}")
        
        # Get weather data
        weather_data = get_weather_data()
        
        # Weather metrics
        col_temp, col_humidity, col_rainfall, col_wind = st.columns(4)
        
        with col_temp:
            st.metric("🌡️ Temperature", weather_data.get("temperature", "28°C"))
        
        with col_humidity:
            st.metric("💧 Humidity", weather_data.get("humidity", "65%"))
        
        with col_rainfall:
            st.metric("🌧️ Rainfall", weather_data.get("rainfall", "2.5mm"))
        
        with col_wind:
            st.metric("💨 Wind Speed", weather_data.get("wind_speed", "12 km/h"))
        
        # Weather advisory
        st.info(f"🌤️ **Weather Advisory:** {weather_data.get('advisory', 'No advisory available')}")
    
    with col2:
        # Location map placeholder
        st.subheader("🗺️ Location Map")
        st.info("Interactive map would be displayed here with current location marked.")
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        if st.button("🔄 Refresh Weather"):
            st.rerun()
        
        if st.button("📍 Get Current Location"):
            st.info("Location detection would be implemented here.")

# Tab 3: Trending Crops
with tab3:
    st.header("🌱 Trending Crops in Your Area")
    
    # Get trending crops data
    crops_data = get_trending_crops()
    
    # Create DataFrame for better display
    crops_df = pd.DataFrame(crops_data)
    
    # Display crops in columns
    cols = st.columns(len(crops_data))
    
    for i, crop in enumerate(crops_data):
        with cols[i]:
            # Handle missing trend field gracefully
            trend = crop.get("trend", "stable")
            trend_icon = "📈" if trend == "up" else "📉" if trend == "down" else "➡️"
            trend_color = "#4CAF50" if trend == "up" else "#f44336" if trend == "down" else "#666"
            
            # Handle missing fields gracefully
            crop_name = crop.get("name", "Unknown Crop")
            crop_price = crop.get("price", "N/A")
            crop_change = crop.get("change", "No change")
            
            st.markdown(f"""
            <div class="feature-card">
                <h4>{trend_icon} {crop_name}</h4>
                <p><strong>{crop_price}</strong></p>
                <p style="color: {trend_color};">{crop_change}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Crop price chart
    st.subheader("📊 Crop Price Trends")
    
    # Create a sample price trend chart
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
    chart_data = []
    
    # If no crops data, create sample data
    if not crops_data:
        crops_data = [
            {"name": "Rice", "price": "₹2500/quintal", "trend": "up"},
            {"name": "Wheat", "price": "₹2200/quintal", "trend": "stable"},
            {"name": "Maize", "price": "₹1800/quintal", "trend": "down"}
        ]
    
    for crop in crops_data:
        # Handle missing fields gracefully
        crop_price = crop.get('price', '₹2000/quintal')
        crop_trend = crop.get('trend', 'stable')
        crop_name = crop.get('name', 'Unknown Crop')
        
        # Extract price value safely
        try:
            price_str = str(crop_price).replace('₹', '').replace(',', '').replace('/quintal', '')
            base_price = float(price_str)
        except (ValueError, AttributeError):
            base_price = 2000.0  # Default price
        
        # Generate some sample trend data
        trend_multiplier = 1 if crop_trend == 'up' else -1 if crop_trend == 'down' else 0
        trend_data = [base_price + (i * trend_multiplier) for i in range(len(dates))]
        chart_data.append(go.Scatter(x=dates, y=trend_data, mode='lines', name=crop_name))
    
    fig = go.Figure(data=chart_data)
    fig.update_layout(
        title="30-Day Price Trends",
        xaxis_title="Date",
        yaxis_title="Price (₹/quintal)",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, width='stretch')

# Tab 4: Market Prices
with tab4:
    st.header("💰 Mandi Prices & Market Information")
    
    # Get market prices data
    prices_data = get_market_prices()
    
    # Create DataFrame
    prices_df = pd.DataFrame(prices_data)
    
    # Display prices table
    st.subheader("📋 Current Mandi Prices")
    
    # Style the DataFrame
    def style_price_change(val):
        if isinstance(val, str) and val.startswith('+'):
            return 'color: #4CAF50; font-weight: bold;'
        elif isinstance(val, str) and val.startswith('-'):
            return 'color: #f44336; font-weight: bold;'
        else:
            return ''
    
    styled_df = prices_df.style.applymap(style_price_change, subset=['change', 'change_percent'])
    st.dataframe(styled_df, width='stretch')
    
    # Market analysis
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Market Analysis")
        
        # Calculate market sentiment
        up_count = len([p for p in prices_data if p['change'].startswith('+')])
        down_count = len([p for p in prices_data if p['change'].startswith('-')])
        total_count = len(prices_data)
        
        sentiment = "📈 Bullish" if up_count > down_count else "📉 Bearish" if down_count > up_count else "➡️ Neutral"
        
        st.metric("Market Sentiment", sentiment)
        st.metric("Rising Prices", f"{up_count}/{total_count}")
        st.metric("Falling Prices", f"{down_count}/{total_count}")
    
    with col2:
        st.subheader("🏪 Top Mandis")
        
        mandi_counts = {}
        for price in prices_data:
            mandi = price['mandi']
            mandi_counts[mandi] = mandi_counts.get(mandi, 0) + 1
        
        for mandi, count in mandi_counts.items():
            st.metric(mandi, f"{count} commodities")

# Tab 5: Agricultural Advisory
with tab5:
    st.header("📋 Agricultural Advisory & Government Schemes")
    
    # Advisory sections
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌱 Crop Advisory")
        
        advisories = [
            {
                "title": "🌧️ Weather Alert",
                "content": "Moderate rainfall expected in the next 3 days. Perfect for planting rice and maize.",
                "priority": "High"
            },
            {
                "title": "🌾 Pest Alert",
                "content": "Monitor for pest attacks in cotton fields. Apply preventive measures immediately.",
                "priority": "Medium"
            },
            {
                "title": "💧 Irrigation Schedule",
                "content": "Reduce irrigation frequency for wheat crops. Current soil moisture is adequate.",
                "priority": "Low"
            }
        ]
        
        for advisory in advisories:
            priority_color = "#f44336" if advisory["priority"] == "High" else "#ff9800" if advisory["priority"] == "Medium" else "#4CAF50"
            
            st.markdown(f"""
            <div class="feature-card">
                <h4 style="color: {priority_color};">{advisory['title']}</h4>
                <p>{advisory['content']}</p>
                <small><strong>Priority:</strong> {advisory['priority']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("🏛️ Government Schemes")
        
        schemes = [
            {
                "name": "PM Kisan",
                "description": "₹6000 annual income support for farmers",
                "eligibility": "All farmers",
                "status": "Active"
            },
            {
                "name": "Crop Insurance",
                "description": "Pradhan Mantri Fasal Bima Yojana",
                "eligibility": "Farmers with land",
                "status": "Active"
            },
            {
                "name": "KCC Scheme",
                "description": "Kisan Credit Card with low interest rates",
                "eligibility": "Farmers and agricultural workers",
                "status": "Active"
            },
            {
                "name": "Solar Pump Subsidy",
                "description": "Subsidy for solar water pumps",
                "eligibility": "Small and marginal farmers",
                "status": "Active"
            }
        ]
        
        for scheme in schemes:
            st.markdown(f"""
            <div class="feature-card">
                <h4>🏛️ {scheme['name']}</h4>
                <p>{scheme['description']}</p>
                <small><strong>Eligibility:</strong> {scheme['eligibility']}</small><br>
                <small><strong>Status:</strong> <span style="color: #4CAF50;">{scheme['status']}</span></small>
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <h4>🌾 Krishimitra - Enhanced Agricultural AI Assistant</h4>
    <p>Powered by Advanced AI | 25+ Language Support | Real-time Agricultural Intelligence</p>
    <p><strong>Government of India Initiative</strong> | Built with ❤️ for Indian Farmers</p>
</div>
""", unsafe_allow_html=True)
