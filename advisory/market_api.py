def get_mock_market_prices(product_type=None, location=None):
    """
    Returns mock real-time market prices. In a real application, this would
    fetch data from an external API.
    """
    mock_prices = {
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

    if product_type and location:
        return mock_prices.get(product_type, {}).get(location)
    elif product_type:
        return mock_prices.get(product_type)
    elif location:
        # Filter all products by location
        result = {}
        for prod, loc_data in mock_prices.items():
            if location in loc_data:
                result[prod] = loc_data[location]
        return result
    
    return mock_prices
