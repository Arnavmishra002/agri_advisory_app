
# district_data.py
# Maps specific districts to granular Agro-Climatic Profiles
# Format: 'district_name_lower': {'state': 'State', 'soil': 'Type', 'rainfall': 'Level', 'irrigation': 'Level'}

DISTRICT_PROFILES = {
    # --- MAHARASHTRA ---
    'pune': {'state': 'Maharashtra', 'soil': 'Black', 'rainfall': 'Medium', 'irrigation': 'High'},
    'nashik': {'state': 'Maharashtra', 'soil': 'Red', 'rainfall': 'Medium', 'irrigation': 'High'},
    'nagpur': {'state': 'Maharashtra', 'soil': 'Black', 'rainfall': 'High', 'irrigation': 'Medium'},
    'solapur': {'state': 'Maharashtra', 'soil': 'Black', 'rainfall': 'Low', 'irrigation': 'Low'},
    'aurangabad': {'state': 'Maharashtra', 'soil': 'Black', 'rainfall': 'Low', 'irrigation': 'Medium'},
    'amravati': {'state': 'Maharashtra', 'soil': 'Black', 'rainfall': 'Medium', 'irrigation': 'Medium'},
    'kolhapur': {'state': 'Maharashtra', 'soil': 'Red', 'rainfall': 'High', 'irrigation': 'High'},
    'satara': {'state': 'Maharashtra', 'soil': 'Black', 'rainfall': 'Medium', 'irrigation': 'High'},
    
    # --- GUJARAT ---
    'ahmedabad': {'state': 'Gujarat', 'soil': 'Alluvial', 'rainfall': 'Medium', 'irrigation': 'High'},
    'surat': {'state': 'Gujarat', 'soil': 'Black', 'rainfall': 'High', 'irrigation': 'High'},
    'rajkot': {'state': 'Gujarat', 'soil': 'Black', 'rainfall': 'Low', 'irrigation': 'Medium'},
    'kutch': {'state': 'Gujarat', 'soil': 'Sandy', 'rainfall': 'Very Low', 'irrigation': 'Low'},
    'vadodara': {'state': 'Gujarat', 'soil': 'Loamy', 'rainfall': 'Medium', 'irrigation': 'High'},
    'junagadh': {'state': 'Gujarat', 'soil': 'Calcareous', 'rainfall': 'Medium', 'irrigation': 'Medium'},
    
    # --- RAJASTHAN ---
    'jaipur': {'state': 'Rajasthan', 'soil': 'Loamy', 'rainfall': 'Low', 'irrigation': 'Medium'},
    'jodhpur': {'state': 'Rajasthan', 'soil': 'Sandy', 'rainfall': 'Very Low', 'irrigation': 'Low'},
    'udaipur': {'state': 'Rajasthan', 'soil': 'Red', 'rainfall': 'Medium', 'irrigation': 'Medium'},
    'kota': {'state': 'Rajasthan', 'soil': 'Black', 'rainfall': 'Medium', 'irrigation': 'High'},
    'bikaner': {'state': 'Rajasthan', 'soil': 'Sandy', 'rainfall': 'Very Low', 'irrigation': 'Low'},
    
    # --- PUNJAB/HARYANA ---
    'ludhiana': {'state': 'Punjab', 'soil': 'Alluvial', 'rainfall': 'Medium', 'irrigation': 'Very High'},
    'amritsar': {'state': 'Punjab', 'soil': 'Alluvial', 'rainfall': 'Medium', 'irrigation': 'Very High'},
    'patiala': {'state': 'Punjab', 'soil': 'Loamy', 'rainfall': 'Medium', 'irrigation': 'High'},
    'karnal': {'state': 'Haryana', 'soil': 'Alluvial', 'rainfall': 'Medium', 'irrigation': 'High'},
    'hisar': {'state': 'Haryana', 'soil': 'Sandy', 'rainfall': 'Low', 'irrigation': 'Medium'},
    
    # --- SOUTH INDIA ---
    'bangalore': {'state': 'Karnataka', 'soil': 'Red', 'rainfall': 'Medium', 'irrigation': 'Medium'},
    'mysore': {'state': 'Karnataka', 'soil': 'Red', 'rainfall': 'Medium', 'irrigation': 'High'},
    'belgaum': {'state': 'Karnataka', 'soil': 'Black', 'rainfall': 'High', 'irrigation': 'Medium'},
    'chennai': {'state': 'Tamil Nadu', 'soil': 'Coastal', 'rainfall': 'High', 'irrigation': 'Medium'},
    'coimbatore': {'state': 'Tamil Nadu', 'soil': 'Red', 'rainfall': 'Low', 'irrigation': 'High'},
    'madurai': {'state': 'Tamil Nadu', 'soil': 'Red', 'rainfall': 'Low', 'irrigation': 'High'},
    'hyderabad': {'state': 'Telangana', 'soil': 'Red', 'rainfall': 'Medium', 'irrigation': 'Medium'},
    'warangal': {'state': 'Telangana', 'soil': 'Black', 'rainfall': 'Medium', 'irrigation': 'High'},
    
    # --- EAST INDIA ---
    'kolkata': {'state': 'West Bengal', 'soil': 'Alluvial', 'rainfall': 'Very High', 'irrigation': 'High'},
    'siliguri': {'state': 'West Bengal', 'soil': 'Terai', 'rainfall': 'Very High', 'irrigation': 'High'},
    'patna': {'state': 'Bihar', 'soil': 'Alluvial', 'rainfall': 'Medium', 'irrigation': 'High'},
    'bhubaneswar': {'state': 'Odisha', 'soil': 'Red', 'rainfall': 'High', 'irrigation': 'Medium'},
    'guwahati': {'state': 'Assam', 'soil': 'Alluvial', 'rainfall': 'Very High', 'irrigation': 'Medium'},
    
    # --- CENTRAL INDIA ---
    'bhopal': {'state': 'Madhya Pradesh', 'soil': 'Black', 'rainfall': 'Medium', 'irrigation': 'Medium'},
    'indore': {'state': 'Madhya Pradesh', 'soil': 'Black', 'rainfall': 'Medium', 'irrigation': 'High'},
    'jabalpur': {'state': 'Madhya Pradesh', 'soil': 'Sandy', 'rainfall': 'High', 'irrigation': 'Medium'},
    'raipur': {'state': 'Chhattisgarh', 'soil': 'Red', 'rainfall': 'High', 'irrigation': 'Medium'},
    
    # --- NORTH INDIA ---
    'lucknow': {'state': 'Uttar Pradesh', 'soil': 'Alluvial', 'rainfall': 'Medium', 'irrigation': 'High'},
    'kanpur': {'state': 'Uttar Pradesh', 'soil': 'Alluvial', 'rainfall': 'Medium', 'irrigation': 'High'},
    'varanasi': {'state': 'Uttar Pradesh', 'soil': 'Alluvial', 'rainfall': 'Medium', 'irrigation': 'High'},
    'dehradun': {'state': 'Uttarakhand', 'soil': 'Forest', 'rainfall': 'High', 'irrigation': 'Medium'},
}
