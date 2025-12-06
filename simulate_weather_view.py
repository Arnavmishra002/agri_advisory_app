
import os
import django
import sys
import json

# Setup Django environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
from datetime import datetime

def test_view_logic():
    print("Testing Weather View Logic...")
    api = UltraDynamicGovernmentAPI()
    location = "Delhi"
    language = "hi"
    
    try:
        print(f"\nFetching weather data for {location}...")
        weather_data = api.get_weather_data(location)
        print("Raw API Data:", json.dumps(weather_data, indent=2, default=str))
        
        # Simulate View Logic
        print("\nSimulating View Processing...")
        if weather_data and weather_data.get('status') == 'success':
            weather_info = weather_data.get('data', {})
        else:
            weather_info = weather_data if isinstance(weather_data, dict) else {}
            
        enhanced_weather = {
            'location': weather_info.get('location', location),
            'current_weather': {
                'temperature': weather_info.get('temperature', weather_info.get('temp', '28°C')),
                'humidity': weather_info.get('humidity', '65%'),
                'wind_speed': weather_info.get('wind_speed', weather_info.get('wind', '12 km/h')),
                'wind_direction': weather_info.get('wind_direction', 'उत्तर-पूर्व'),
                'condition': weather_info.get('condition', weather_info.get('weather', 'साफ आसमान')),
                'description': weather_info.get('description', weather_info.get('weather_description', 'साफ आसमान')),
                'feels_like': weather_info.get('feels_like', '30°C'),
                'pressure': weather_info.get('pressure', '1013'),
                'pressure_unit': weather_info.get('pressure_unit', 'hPa'),
                'visibility': weather_info.get('visibility', '10'),
                'visibility_unit': weather_info.get('visibility_unit', 'km'),
                'uv_index': weather_info.get('uv_index', '5')
            },
            'forecast_7_days': weather_data.get('forecast_7_days', weather_info.get('forecast', weather_info.get('forecast_7_days', weather_info.get('forecast_7day', [])))),
            'farmer_advice': {
                'general': 'मौसम अनुकूल है, नियमित सिंचाई करें',
                'crop_specific': 'वर्तमान मौसम में गेहूं की बुवाई के लिए उपयुक्त है',
                'precautions': 'कीटों के हमले की संभावना कम है'
            },
            'agricultural_advice': weather_info.get('agricultural_advice', []),
            'alerts': weather_info.get('alerts', []),
            'data_source': weather_info.get('data_source', 'IMD (Indian Meteorological Department) - Real-Time Government API'),
            'timestamp': datetime.now().isoformat()
        }
        
        print("\n✅ View Logic Successful!")
        print("Enhanced Weather:", json.dumps(enhanced_weather, indent=2, default=str))
        
    except Exception as e:
        print(f"\n❌ View Logic Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_view_logic()
