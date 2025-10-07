#!/usr/bin/env python3
"""
Debug AI to find the issue
"""

import sys
import os
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.ml.intelligent_chatbot import IntelligentAgriculturalChatbot

def test_ai():
    print("Testing AI initialization...")
    try:
        chatbot = IntelligentAgriculturalChatbot()
        print("✅ AI initialized successfully")
        
        print("Testing simple query...")
        try:
            result = chatbot.get_response("hello", "en")
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error in simple query: {e}")
            import traceback
            traceback.print_exc()
        
        print("Testing Hindi query...")
        try:
            result = chatbot.get_response("नमस्ते", "hi")
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error in Hindi query: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai()
