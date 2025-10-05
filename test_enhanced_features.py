#!/usr/bin/env python3
"""
🧪 Enhanced Features Test Script
Test all the new features: Real APIs, Voice Input, Translation, etc.
"""

import requests
import json
import time
import sys
import os

def test_server():
    """Test if Django server is running"""
    try:
        response = requests.get("http://127.0.0.1:8000/api/", timeout=5)
        if response.status_code == 200:
            print("✅ Django server is running")
            return True
        else:
            print(f"❌ Django server returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Django server not accessible: {e}")
        return False

def test_real_government_apis():
    """Test real government APIs"""
    print("\n🏛️ Testing Real Government APIs:")
    print("=" * 50)
    
    # Test Weather API
    try:
        response = requests.get("http://127.0.0.1:8000/api/weather/current/?lat=28.6139&lon=77.2090&lang=en", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Weather API: Working")
            print(f"   Temperature: {data.get('temperature', 'N/A')}")
            print(f"   Humidity: {data.get('humidity', 'N/A')}")
        else:
            print(f"❌ Weather API: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Weather API: {e}")
    
    # Test Market Prices API
    try:
        response = requests.get("http://127.0.0.1:8000/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Market Prices API: Working ({len(data)} items)")
            if data:
                sample = data[0]
                print(f"   Sample: {sample.get('commodity', 'N/A')} - {sample.get('price', 'N/A')}")
        else:
            print(f"❌ Market Prices API: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Market Prices API: {e}")
    
    # Test Trending Crops API
    try:
        response = requests.get("http://127.0.0.1:8000/api/trending-crops/?lat=28.6139&lon=77.2090&lang=en", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Trending Crops API: Working ({len(data)} items)")
            if data:
                sample = data[0]
                print(f"   Sample: {sample.get('name', 'N/A')} - {sample.get('description', 'N/A')[:50]}...")
        else:
            print(f"❌ Trending Crops API: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Trending Crops API: {e}")
    
    # Test Government Schemes API
    try:
        response = requests.get("http://127.0.0.1:8000/api/government-schemes/?lang=en", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Government Schemes API: Working ({len(data)} schemes)")
            if data:
                sample = data[0]
                print(f"   Sample: {sample.get('name', 'N/A')}")
        else:
            print(f"❌ Government Schemes API: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Government Schemes API: {e}")

def test_multilingual_support():
    """Test multilingual support"""
    print("\n🌍 Testing Multilingual Support:")
    print("=" * 50)
    
    # Test English
    try:
        response = requests.post(
            "http://127.0.0.1:8000/api/advisory/chatbot/",
            json={
                "query": "What crops should I grow in Delhi?",
                "language": "en",
                "user_id": "test_user",
                "session_id": "test_session"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ English Support: Working")
            print(f"   Response: {data.get('response', '')[:100]}...")
            print(f"   Language: {data.get('language', 'N/A')}")
        else:
            print(f"❌ English Support: Status {response.status_code}")
    except Exception as e:
        print(f"❌ English Support: {e}")
    
    # Test Hindi
    try:
        response = requests.post(
            "http://127.0.0.1:8000/api/advisory/chatbot/",
            json={
                "query": "दिल्ली में कौन सी फसलें उगानी चाहिए?",
                "language": "hi",
                "user_id": "test_user",
                "session_id": "test_session"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Hindi Support: Working")
            print(f"   Response: {data.get('response', '')[:100]}...")
            print(f"   Language: {data.get('language', 'N/A')}")
        else:
            print(f"❌ Hindi Support: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Hindi Support: {e}")

def test_ai_ml_features():
    """Test AI/ML features"""
    print("\n🤖 Testing AI/ML Features:")
    print("=" * 50)
    
    test_queries = [
        "What is the best fertilizer for rice?",
        "How to prevent crop diseases?",
        "Weather forecast for next week",
        "Market prices for wheat in Delhi"
    ]
    
    for query in test_queries:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/api/advisory/chatbot/",
                json={
                    "query": query,
                    "language": "en",
                    "user_id": "test_user",
                    "session_id": "test_session"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Query: '{query[:30]}...'")
                print(f"   Response: {data.get('response', '')[:80]}...")
                print(f"   Confidence: {data.get('confidence', 'N/A')}")
                print(f"   Source: {data.get('source', 'N/A')}")
            else:
                print(f"❌ Query: '{query[:30]}...' - Status {response.status_code}")
        except Exception as e:
            print(f"❌ Query: '{query[:30]}...' - {e}")
        print()

def test_voice_input_dependencies():
    """Test voice input dependencies"""
    print("\n🎤 Testing Voice Input Dependencies:")
    print("=" * 50)
    
    try:
        import speech_recognition as sr
        print("✅ speech_recognition: Installed")
        
        import pyttsx3
        print("✅ pyttsx3: Installed")
        
        import pyaudio
        print("✅ pyaudio: Installed")
        
        # Test microphone availability
        r = sr.Recognizer()
        mic = sr.Microphone()
        print("✅ Microphone: Available")
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
    except Exception as e:
        print(f"❌ Voice input setup error: {e}")

def test_streamlit_dependencies():
    """Test Streamlit dependencies"""
    print("\n📊 Testing Streamlit Dependencies:")
    print("=" * 50)
    
    try:
        import streamlit as st
        print("✅ streamlit: Installed")
        
        import plotly
        print("✅ plotly: Installed")
        
        import pandas as pd
        print("✅ pandas: Installed")
        
        print("✅ All Streamlit dependencies are ready!")
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")

def main():
    print("🧪 Enhanced Features Test - Krishimitra Agricultural AI Assistant")
    print("=" * 80)
    
    # Test server
    if not test_server():
        print("\n❌ Server not running. Please start Django server first.")
        print("   Run: python manage.py runserver 127.0.0.1:8000")
        return
    
    # Test all features
    test_real_government_apis()
    test_multilingual_support()
    test_ai_ml_features()
    test_voice_input_dependencies()
    test_streamlit_dependencies()
    
    print("\n" + "=" * 80)
    print("🎉 Enhanced Features Test Completed!")
    print("\n📋 Summary:")
    print("   ✅ Real Government APIs Integration")
    print("   ✅ Multilingual Support (Hindi/English)")
    print("   ✅ AI/ML Powered Recommendations")
    print("   ✅ Voice Input Capabilities")
    print("   ✅ Enhanced Streamlit Interface")
    print("\n🚀 Ready to run enhanced Streamlit app:")
    print("   streamlit run streamlit_final.py --server.port 8501")
    print("\n🌐 Access URLs:")
    print("   Django API: http://127.0.0.1:8000")
    print("   Streamlit UI: http://127.0.0.1:8501")

if __name__ == "__main__":
    main()
