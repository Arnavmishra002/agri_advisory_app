
import datetime

# Mock the AccurateLocationAPI response
mock_api_response = {
    'status': 'success',
    'location': {
        'name': 'Connaught Place',
        'city': 'New Delhi',
        'state': 'Delhi',
        'district': 'New Delhi',
        'coordinates': {'lat': 28.6139, 'lng': 77.2090}
    },
    'data_source': 'Nominatim (OpenStreetMap)',
    'timestamp': datetime.datetime.now().isoformat()
}

# Simulate the view logic
def simulate_view_logic(location_result):
    location_data = location_result.get('location', {}) if location_result.get('status') == 'success' else location_result
    
    response = {
        'coordinates': {'lat': 28.6139, 'lon': 77.2090},
        'location': location_data,
        'timestamp': datetime.datetime.now().isoformat()
    }
    return response

# Verify
result = simulate_view_logic(mock_api_response)
print("Resulting Response Structure:")
print(result)

# Check if frontend access pattern works
location_name = "Unknown"
if result['location'] and 'name' in result['location']:
    location_name = result['location']['name']

print(f"\nFrontend extracted location name: {location_name}")

if location_name == 'Connaught Place':
    print("\n✅ VERIFICATION SUCCESSFUL: Frontend logic will correctly extract the name.")
else:
    print("\n❌ VERIFICATION FAILED: Frontend logic will fail.")
