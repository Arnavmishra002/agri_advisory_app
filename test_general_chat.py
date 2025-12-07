
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.api.views import ChatbotViewSet

def test_general_query():
    import advisory.api.views
    print(f"Views File: {advisory.api.views.__file__}")
    
    view = ChatbotViewSet()
    print(f"View Module: {view.__module__}")
    
    methods = [m for m in dir(view) if 'handle' in m]
    print(f"Handle methods: {methods}")
    
    print("\n--- Testing General Query (ChatGPT-like) ---")
    
    if '_handle_general_query_advanced' in dir(view):
        response = view._handle_general_query_advanced(
            query="Tell me a joke about farming",
            language="en",
            location="Delhi"
        )
        print(f"Response: {response}")
    else:
        print("❌ FAIL: advanced handler not found")

if __name__ == "__main__":
    test_general_query()
