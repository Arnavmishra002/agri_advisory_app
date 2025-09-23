def get_mock_market_prices(latitude, longitude, language, product_type=None):
    """
    Returns mock real-time market prices based on location and language.
    In a real application, this would fetch data from an external API.
    """

    # Simulate location-based data. For a demo, we'll use a simple approximation.
    # In a real scenario, you'd map lat/lon to a specific market location.
    mock_city = "Delhi"
    print(f"get_mock_market_prices: Received latitude={latitude}, longitude={longitude}, language={language}, product_type={product_type}")

    # Convert latitude and longitude to float
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (ValueError, TypeError):
        print("get_mock_market_prices: Invalid latitude or longitude, using default mock city.")
        latitude = None
        longitude = None

    if latitude and longitude:
        # Simple logic to simulate different locations for mock data
        if 18.0 <= latitude <= 20.0 and 72.0 <= longitude <= 74.0: # Roughly Mumbai region
            mock_city = "Mumbai"
        elif 28.0 <= latitude <= 30.0 and 76.0 <= longitude <= 78.0: # Roughly Delhi region
            mock_city = "Delhi"
        else:
            mock_city = "Other"
    print(f"get_mock_market_prices: Determined mock_city={mock_city}")

    mock_prices_en = {
        "Wheat": {
            "Delhi": {"price": 2200, "unit": "INR/quintal", "date": "2025-09-23"},
            "Mumbai": {"price": 2350, "unit": "INR/quintal", "date": "2025-09-23"},
        },
        "Rice": {
            "Delhi": {"price": 3500, "unit": "INR/quintal", "date": "2025-09-23"},
            "Mumbai": {"price": 3700, "unit": "INR/quintal", "date": "2025-09-23"},
        },
        "Corn": {
            "Delhi": {"price": 1900, "unit": "INR/quintal", "date": "2025-09-23"},
            "Mumbai": {"price": 2050, "unit": "INR/quintal", "date": "2025-09-23"},
        }
    }

    mock_prices_hi = {
        "गेहूं": {
            "दिल्ली": {"price": 2200, "unit": "INR/क्विंटल", "date": "2025-09-23"},
            "मुंबई": {"price": 2350, "unit": "INR/क्विंटल", "date": "2025-09-23"},
        },
        "चावल": {
            "दिल्ली": {"price": 3500, "unit": "INR/क्विंटल", "date": "2025-09-23"},
            "मुंबई": {"price": 3700, "unit": "INR/क्विंटल", "date": "2025-09-23"},
        },
        "मक्का": {
            "दिल्ली": {"price": 1900, "unit": "INR/क्विंटल", "date": "2025-09-23"},
            "मुंबई": {"price": 2050, "unit": "INR/क्विंटल", "date": "2025-09-23"},
        }
    }

    selected_mock_prices = mock_prices_hi if language == 'hi' else mock_prices_en

    if product_type and mock_city in selected_mock_prices.get(product_type, {}):
        return {product_type: selected_mock_prices[product_type][mock_city]}
    elif mock_city:
        result = {}
        for prod, loc_data in selected_mock_prices.items():
            if mock_city in loc_data:
                result[prod] = loc_data[mock_city]
        if result: # Only return if there's data for the mock_city
            return result
    
    return {}

def get_mock_trending_crops(latitude, longitude, language):
    # Mock trending crops data based on general location for demo
    # In a real app, this would involve more sophisticated geo-mapping
    # and actual agricultural trend analysis.

    trending_crops_en = [
        {
            "name": "Rice",
            "description": "A staple food crop, high-yielding varieties are trending.",
            "benefits": ["High demand", "Good market price", "Suitable for monsoon season"]
        },
        {
            "name": "Wheat",
            "description": "Winter crop with increasing demand due to food security concerns.",
            "benefits": ["Essential commodity", "Government support", "Drought-resistant varieties"]
        },
        {
            "name": "Cotton",
            "description": "Cash crop with growing demand in textile industry.",
            "benefits": ["Export potential", "High profitability", "Suitable for dry regions"]
        }
    ]

    trending_crops_hi = [
        {
            "name": "धान",
            "description": "एक मुख्य खाद्य फसल, अधिक उपज देने वाली किस्में चलन में हैं।",
            "benefits": ["उच्च मांग", "अच्छा बाजार मूल्य", "मानसून के मौसम के लिए उपयुक्त"]
        },
        {
            "name": "गेहूं",
            "description": "खाद्य सुरक्षा चिंताओं के कारण बढ़ती मांग वाली रबी की फसल।",
            "benefits": ["आवश्यक वस्तु", "सरकारी सहायता", "सूखा प्रतिरोधी किस्में"]
        },
        {
            "name": "कपास",
            "description": "वस्त्र उद्योग में बढ़ती मांग वाली नकदी फसल।",
            "benefits": ["निर्यात क्षमता", "उच्च लाभप्रदता", "शुष्क क्षेत्रों के लिए उपयुक्त"]
        }
    ]

    if language == 'hi':
        return trending_crops_hi
    return trending_crops_en