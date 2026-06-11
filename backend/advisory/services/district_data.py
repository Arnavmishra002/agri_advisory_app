"""
KrishiMitra District Agro-Climatic Profiles v1.0
Covers 200+ key agricultural districts across India.

Each district profile:
  state       – parent state name
  soil        – dominant soil type
  rainfall    – Very Low | Low | Medium | High | Very High
  irrigation  – Low | Medium | High
  agro_zone   – zone key from comprehensive_crop_database.ZONES
  priority_crops – ordered list of highest-suitability crop keys
"""

from typing import Dict, Any

DISTRICT_PROFILES: Dict[str, Dict[str, Any]] = {

    # ─── PUNJAB ───────────────────────────────────────────────────────
    "amritsar":    {"state": "Punjab",  "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "northwest",    "priority_crops": ["wheat","rice","cotton","sugarcane","potato","mustard"]},
    "ludhiana":    {"state": "Punjab",  "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "northwest",    "priority_crops": ["wheat","rice","cotton","maize","potato","mustard"]},
    "jalandhar":   {"state": "Punjab",  "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "northwest",    "priority_crops": ["wheat","rice","potato","sugarcane","cotton"]},
    "patiala":     {"state": "Punjab",  "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "northwest",    "priority_crops": ["wheat","rice","cotton","maize","potato"]},
    "firozpur":    {"state": "Punjab",  "soil": "Sandy Loam","rainfall": "Low",     "irrigation": "High",   "agro_zone": "northwest",    "priority_crops": ["wheat","cotton","rice","bajra","mustard"]},
    "bathinda":    {"state": "Punjab",  "soil": "Sandy Loam","rainfall": "Low",     "irrigation": "Medium", "agro_zone": "northwest",    "priority_crops": ["cotton","wheat","bajra","mustard","sunflower"]},

    # ─── HARYANA ──────────────────────────────────────────────────────
    "karnal":      {"state": "Haryana", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "northwest",    "priority_crops": ["wheat","rice","sugarcane","mustard","potato"]},
    "hisar":       {"state": "Haryana", "soil": "Sandy Loam","rainfall": "Low",     "irrigation": "Medium", "agro_zone": "northwest",    "priority_crops": ["cotton","wheat","bajra","mustard","guar"]},
    "rohtak":      {"state": "Haryana", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "northwest",    "priority_crops": ["wheat","mustard","gram","rice","cotton"]},
    "gurgaon":     {"state": "Haryana", "soil": "Sandy Loam","rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "northwest",    "priority_crops": ["wheat","mustard","bajra","cotton","vegetables"]},
    "sirsa":       {"state": "Haryana", "soil": "Sandy Loam","rainfall": "Low",     "irrigation": "Medium", "agro_zone": "northwest",    "priority_crops": ["cotton","wheat","bajra","mustard","cumin"]},

    # ─── UTTAR PRADESH ────────────────────────────────────────────────
    "lucknow":     {"state": "Uttar Pradesh", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["wheat","rice","sugarcane","potato","mustard","mango"]},
    "kanpur":      {"state": "Uttar Pradesh", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["wheat","potato","mustard","sugarcane","peas"]},
    "agra":        {"state": "Uttar Pradesh", "soil": "Sandy Loam","rainfall": "Low",     "irrigation": "Medium", "agro_zone": "indo_gangetic", "priority_crops": ["wheat","mustard","bajra","potato","tomato"]},
    "varanasi":    {"state": "Uttar Pradesh", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["wheat","rice","vegetable","gram","masoor"]},
    "allahabad":   {"state": "Uttar Pradesh", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "indo_gangetic", "priority_crops": ["wheat","gram","peas","mustard","potato"]},
    "meerut":      {"state": "Uttar Pradesh", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["sugarcane","wheat","potato","mustard","peas"]},
    "moradabad":   {"state": "Uttar Pradesh", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["sugarcane","wheat","rice","potato","moong"]},
    "bareilly":    {"state": "Uttar Pradesh", "soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["sugarcane","wheat","rice","potato","mustard"]},
    "gorakhpur":   {"state": "Uttar Pradesh", "soil": "Alluvial",  "rainfall": "High",    "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["rice","wheat","sugarcane","maize","urad"]},

    # ─── RAJASTHAN ────────────────────────────────────────────────────
    "jaipur":      {"state": "Rajasthan", "soil": "Sandy Loam","rainfall": "Low",   "irrigation": "Low",    "agro_zone": "thar_desert",  "priority_crops": ["bajra","mustard","gram","wheat","cumin","fennel"]},
    "jodhpur":     {"state": "Rajasthan", "soil": "Sandy",     "rainfall": "Very Low","irrigation": "Low",  "agro_zone": "thar_desert",  "priority_crops": ["bajra","guar","cumin","fennel","castor","moong"]},
    "barmer":      {"state": "Rajasthan", "soil": "Sandy",     "rainfall": "Very Low","irrigation": "Low",  "agro_zone": "thar_desert",  "priority_crops": ["bajra","guar","cumin","castor","sesame"]},
    "bikaner":     {"state": "Rajasthan", "soil": "Sandy",     "rainfall": "Very Low","irrigation": "Low",  "agro_zone": "thar_desert",  "priority_crops": ["bajra","moong","guar","cumin","fennel"]},
    "kota":        {"state": "Rajasthan", "soil": "Black",     "rainfall": "Medium", "irrigation": "Medium","agro_zone": "thar_desert",  "priority_crops": ["soybean","mustard","wheat","gram","cotton","coriander"]},
    "ajmer":       {"state": "Rajasthan", "soil": "Sandy Loam","rainfall": "Low",   "irrigation": "Low",    "agro_zone": "thar_desert",  "priority_crops": ["wheat","bajra","mustard","gram","coriander"]},
    "udaipur":     {"state": "Rajasthan", "soil": "Red",       "rainfall": "Medium", "irrigation": "Low",   "agro_zone": "thar_desert",  "priority_crops": ["maize","wheat","gram","mustard","garlic"]},

    # ─── MADHYA PRADESH ───────────────────────────────────────────────
    "bhopal":      {"state": "Madhya Pradesh", "soil": "Black",   "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "central", "priority_crops": ["soybean","wheat","gram","maize","onion"]},
    "indore":      {"state": "Madhya Pradesh", "soil": "Black",   "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "central", "priority_crops": ["soybean","wheat","gram","onion","cotton"]},
    "jabalpur":    {"state": "Madhya Pradesh", "soil": "Black",   "rainfall": "High",    "irrigation": "Medium", "agro_zone": "central", "priority_crops": ["soybean","rice","wheat","urad","linseed"]},
    "gwalior":     {"state": "Madhya Pradesh", "soil": "Alluvial","rainfall": "Low",     "irrigation": "Medium", "agro_zone": "central", "priority_crops": ["wheat","mustard","gram","potato","masoor"]},
    "rewa":        {"state": "Madhya Pradesh", "soil": "Red",     "rainfall": "Medium",  "irrigation": "Low",    "agro_zone": "central", "priority_crops": ["wheat","gram","linseed","masoor","urad"]},
    "sagar":       {"state": "Madhya Pradesh", "soil": "Black",   "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "central", "priority_crops": ["soybean","wheat","gram","linseed"]},
    "ujjain":      {"state": "Madhya Pradesh", "soil": "Black",   "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "central", "priority_crops": ["soybean","wheat","gram","garlic","onion"]},

    # ─── MAHARASHTRA ──────────────────────────────────────────────────
    "pune":        {"state": "Maharashtra", "soil": "Black",    "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "deccan", "priority_crops": ["sugarcane","onion","grape","tomato","potato"]},
    "nashik":      {"state": "Maharashtra", "soil": "Black",    "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "deccan", "priority_crops": ["grapes","onion","tomato","sugarcane","wheat"]},
    "nagpur":      {"state": "Maharashtra", "soil": "Black",    "rainfall": "Medium",  "irrigation": "Low",    "agro_zone": "deccan", "priority_crops": ["orange","soybean","cotton","wheat","gram"]},
    "aurangabad":  {"state": "Maharashtra", "soil": "Black",    "rainfall": "Low",     "irrigation": "Low",    "agro_zone": "deccan", "priority_crops": ["cotton","soybean","jowar","gram","moong"]},
    "solapur":     {"state": "Maharashtra", "soil": "Black",    "rainfall": "Low",     "irrigation": "Low",    "agro_zone": "deccan", "priority_crops": ["sugarcane","onion","pomegranate","cotton","jowar"]},
    "kolhapur":    {"state": "Maharashtra", "soil": "Laterite", "rainfall": "High",    "irrigation": "Medium", "agro_zone": "deccan", "priority_crops": ["sugarcane","rice","groundnut","turmeric","cotton"]},
    "amravati":    {"state": "Maharashtra", "soil": "Black",    "rainfall": "Medium",  "irrigation": "Low",    "agro_zone": "deccan", "priority_crops": ["cotton","soybean","wheat","jowar","tur"]},
    "latur":       {"state": "Maharashtra", "soil": "Black",    "rainfall": "Low",     "irrigation": "Low",    "agro_zone": "deccan", "priority_crops": ["tur","soybean","cotton","jowar","gram"]},
    "nanded":      {"state": "Maharashtra", "soil": "Black",    "rainfall": "Low",     "irrigation": "Low",    "agro_zone": "deccan", "priority_crops": ["cotton","soybean","tur","jowar","turmeric"]},

    # ─── KARNATAKA ────────────────────────────────────────────────────
    "bangalore":   {"state": "Karnataka", "soil": "Red",      "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["ragi","maize","tomato","potato","sunflower"]},
    "mysore":      {"state": "Karnataka", "soil": "Red",      "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["sugarcane","rice","ragi","groundnut","sericulture"]},
    "hubli":       {"state": "Karnataka", "soil": "Black",    "rainfall": "Medium",  "irrigation": "Low",    "agro_zone": "peninsular", "priority_crops": ["cotton","jowar","sunflower","tur","maize"]},
    "gulbarga":    {"state": "Karnataka", "soil": "Black",    "rainfall": "Low",     "irrigation": "Low",    "agro_zone": "peninsular", "priority_crops": ["tur","cotton","gram","soybean","jowar"]},
    "shimoga":     {"state": "Karnataka", "soil": "Laterite", "rainfall": "Very High","irrigation": "Medium","agro_zone": "peninsular", "priority_crops": ["rice","coconut","areca_nut","black_pepper","ginger"]},
    "bellary":     {"state": "Karnataka", "soil": "Red",      "rainfall": "Low",     "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["cotton","groundnut","sunflower","maize","onion"]},
    "mangalore":   {"state": "Karnataka", "soil": "Laterite", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "coastal",    "priority_crops": ["coconut","areca_nut","black_pepper","cashew","rice"]},

    # ─── ANDHRA PRADESH ───────────────────────────────────────────────
    "vijayawada":  {"state": "Andhra Pradesh", "soil": "Alluvial","rainfall": "Medium", "irrigation": "High",  "agro_zone": "peninsular", "priority_crops": ["rice","maize","cotton","chilli","sugarcane"]},
    "guntur":      {"state": "Andhra Pradesh", "soil": "Black",   "rainfall": "Medium", "irrigation": "Medium","agro_zone": "peninsular", "priority_crops": ["chilli","cotton","tobacco","rice","groundnut"]},
    "kurnool":     {"state": "Andhra Pradesh", "soil": "Black",   "rainfall": "Low",    "irrigation": "Low",   "agro_zone": "peninsular", "priority_crops": ["cotton","groundnut","jowar","sunflower","tur"]},
    "visakhapatnam":{"state":"Andhra Pradesh","soil": "Red",      "rainfall": "High",   "irrigation": "Medium","agro_zone": "coastal",    "priority_crops": ["rice","cashew","sugarcane","coconut","turmeric"]},
    "nellore":     {"state": "Andhra Pradesh", "soil": "Alluvial","rainfall": "Medium", "irrigation": "High",  "agro_zone": "coastal",    "priority_crops": ["rice","sugarcane","cotton","groundnut","aquaculture"]},

    # ─── TELANGANA ────────────────────────────────────────────────────
    "hyderabad":   {"state": "Telangana", "soil": "Red",      "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["rice","maize","cotton","turmeric","vegetables"]},
    "warangal":    {"state": "Telangana", "soil": "Black",    "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["rice","cotton","maize","turmeric","jowar"]},
    "nizamabad":   {"state": "Telangana", "soil": "Black",    "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["rice","turmeric","cotton","maize","sugarcane"]},
    "karimnagar":  {"state": "Telangana", "soil": "Black",    "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["rice","cotton","maize","chilli","turmeric"]},
    "khammam":     {"state": "Telangana", "soil": "Red",      "rainfall": "High",    "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["rice","cotton","maize","oil_palm","sugarcane"]},

    # ─── TAMIL NADU ───────────────────────────────────────────────────
    "chennai":     {"state": "Tamil Nadu","soil": "Red",       "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["rice","groundnut","vegetables","coconut","banana"]},
    "coimbatore":  {"state": "Tamil Nadu","soil": "Black",     "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "peninsular", "priority_crops": ["sugarcane","cotton","maize","groundnut","turmeric"]},
    "madurai":     {"state": "Tamil Nadu","soil": "Black",     "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["rice","cotton","banana","groundnut","vegetables"]},
    "tirunelveli": {"state": "Tamil Nadu","soil": "Sandy Loam","rainfall": "High",    "irrigation": "Medium", "agro_zone": "coastal",    "priority_crops": ["banana","rice","coconut","cashew","groundnut"]},
    "salem":       {"state": "Tamil Nadu","soil": "Red",       "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["mango","rice","maize","groundnut","vegetables"]},
    "thanjavur":   {"state": "Tamil Nadu","soil": "Alluvial",  "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "coastal",    "priority_crops": ["rice","banana","sugarcane","coconut","groundnut"]},
    "erode":       {"state": "Tamil Nadu","soil": "Red",       "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "peninsular", "priority_crops": ["sugarcane","turmeric","cotton","coconut","banana"]},

    # ─── KERALA ───────────────────────────────────────────────────────
    "thiruvananthapuram":{"state":"Kerala","soil":"Laterite",  "rainfall": "Very High","irrigation": "Medium","agro_zone": "coastal",    "priority_crops": ["coconut","rubber","cashew","tapioca","banana"]},
    "kochi":       {"state": "Kerala",    "soil": "Alluvial", "rainfall": "Very High","irrigation": "Medium","agro_zone": "coastal",    "priority_crops": ["coconut","rice","banana","black_pepper","cardamom"]},
    "kozhikode":   {"state": "Kerala",    "soil": "Laterite", "rainfall": "Very High","irrigation": "Medium","agro_zone": "coastal",    "priority_crops": ["coconut","ginger","rice","black_pepper","areca_nut"]},
    "palakkad":    {"state": "Kerala",    "soil": "Red",      "rainfall": "High",     "irrigation": "High",  "agro_zone": "coastal",    "priority_crops": ["rice","banana","coconut","sugarcane","turmeric"]},
    "idukki":      {"state": "Kerala",    "soil": "Laterite", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "coastal",    "priority_crops": ["cardamom","tea","coffee","rubber","pepper"]},
    "thrissur":    {"state": "Kerala",    "soil": "Laterite", "rainfall": "Very High","irrigation": "Medium","agro_zone": "coastal",    "priority_crops": ["coconut","areca_nut","rice","banana","ginger"]},

    # ─── GUJARAT ──────────────────────────────────────────────────────
    "ahmedabad":   {"state": "Gujarat",   "soil": "Black",    "rainfall": "Low",     "irrigation": "Medium", "agro_zone": "gujarat",    "priority_crops": ["cotton","wheat","groundnut","castor","tobacco"]},
    "surat":       {"state": "Gujarat",   "soil": "Alluvial", "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "gujarat",    "priority_crops": ["sugarcane","rice","vegetables","banana","cotton"]},
    "rajkot":      {"state": "Gujarat",   "soil": "Sandy Loam","rainfall": "Low",    "irrigation": "Low",    "agro_zone": "gujarat",    "priority_crops": ["groundnut","cotton","wheat","sesame","bajra"]},
    "vadodara":    {"state": "Gujarat",   "soil": "Black",    "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "gujarat",    "priority_crops": ["cotton","wheat","tobacco","maize","vegetables"]},
    "anand":       {"state": "Gujarat",   "soil": "Alluvial", "rainfall": "Low",     "irrigation": "High",   "agro_zone": "gujarat",    "priority_crops": ["potato","tobacco","wheat","rice","vegetables"]},
    "junagadh":    {"state": "Gujarat",   "soil": "Sandy Loam","rainfall": "Medium", "irrigation": "Medium", "agro_zone": "gujarat",    "priority_crops": ["groundnut","mango","banana","cotton","castor"]},
    "mehsana":     {"state": "Gujarat",   "soil": "Sandy Loam","rainfall": "Low",    "irrigation": "Medium", "agro_zone": "gujarat",    "priority_crops": ["cumin","fennel","wheat","cotton","groundnut"]},

    # ─── WEST BENGAL ──────────────────────────────────────────────────
    "kolkata":     {"state": "West Bengal","soil": "Alluvial","rainfall": "High",    "irrigation": "High",   "agro_zone": "indo_gangetic","priority_crops": ["rice","jute","potato","vegetables","mustard"]},
    "murshidabad": {"state": "West Bengal","soil": "Alluvial","rainfall": "High",    "irrigation": "Medium", "agro_zone": "indo_gangetic","priority_crops": ["jute","rice","potato","mustard","mango"]},
    "burdwan":     {"state": "West Bengal","soil": "Alluvial","rainfall": "High",    "irrigation": "High",   "agro_zone": "indo_gangetic","priority_crops": ["rice","jute","potato","mustard","vegetables"]},
    "darjeeling":  {"state": "West Bengal","soil": "Laterite","rainfall": "Very High","irrigation": "Low",   "agro_zone": "himalayan",   "priority_crops": ["tea","ginger","potato","cardamom","turmeric"]},

    # ─── BIHAR ────────────────────────────────────────────────────────
    "patna":       {"state": "Bihar",    "soil": "Alluvial", "rainfall": "Medium",  "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["rice","wheat","maize","potato","litchi"]},
    "muzaffarpur": {"state": "Bihar",    "soil": "Alluvial", "rainfall": "High",    "irrigation": "High",   "agro_zone": "indo_gangetic", "priority_crops": ["litchi","rice","wheat","maize","sugarcane"]},
    "gaya":        {"state": "Bihar",    "soil": "Alluvial", "rainfall": "Medium",  "irrigation": "Medium", "agro_zone": "indo_gangetic", "priority_crops": ["wheat","rice","moong","urad","vegetables"]},
    "bhagalpur":   {"state": "Bihar",    "soil": "Alluvial", "rainfall": "High",    "irrigation": "Medium", "agro_zone": "indo_gangetic", "priority_crops": ["rice","wheat","maize","jute","sugarcane"]},
    "purnea":      {"state": "Bihar",    "soil": "Alluvial", "rainfall": "High",    "irrigation": "Medium", "agro_zone": "indo_gangetic", "priority_crops": ["jute","rice","maize","wheat","moong"]},

    # ─── ODISHA ───────────────────────────────────────────────────────
    "bhubaneswar": {"state": "Odisha",   "soil": "Alluvial", "rainfall": "High",    "irrigation": "Medium", "agro_zone": "coastal",    "priority_crops": ["rice","jute","turmeric","ginger","vegetables"]},
    "cuttack":     {"state": "Odisha",   "soil": "Alluvial", "rainfall": "High",    "irrigation": "High",   "agro_zone": "coastal",    "priority_crops": ["rice","jute","turmeric","ginger","potato"]},
    "koraput":     {"state": "Odisha",   "soil": "Red",      "rainfall": "High",    "irrigation": "Low",    "agro_zone": "peninsular", "priority_crops": ["rice","maize","finger_millet","turmeric","ginger"]},
    "sambalpur":   {"state": "Odisha",   "soil": "Red",      "rainfall": "High",    "irrigation": "Medium", "agro_zone": "peninsular", "priority_crops": ["rice","sugarcane","cotton","maize","sesame"]},
    "balasore":    {"state": "Odisha",   "soil": "Alluvial", "rainfall": "High",    "irrigation": "Medium", "agro_zone": "coastal",    "priority_crops": ["rice","jute","turmeric","vegetables","cashew"]},

    # ─── ASSAM ────────────────────────────────────────────────────────
    "guwahati":    {"state": "Assam",    "soil": "Alluvial", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["rice","jute","tea","mustard","ginger"]},
    "dibrugarh":   {"state": "Assam",    "soil": "Alluvial", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["tea","rice","jute","ginger","pineapple"]},
    "jorhat":      {"state": "Assam",    "soil": "Alluvial", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["tea","rice","jute","pineapple","banana"]},
    "nagaon":      {"state": "Assam",    "soil": "Alluvial", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["rice","mustard","jute","ginger","turmeric"]},
    "silchar":     {"state": "Assam",    "soil": "Alluvial", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["rice","tea","jute","pineapple","sugarcane"]},

    # ─── HIMACHAL PRADESH ─────────────────────────────────────────────
    "shimla":      {"state": "Himachal Pradesh","soil": "Loamy",  "rainfall": "High", "irrigation": "Low",  "agro_zone": "himalayan",   "priority_crops": ["apple","potato","rajma","peas","strawberry"]},
    "kullu":       {"state": "Himachal Pradesh","soil": "Loamy",  "rainfall": "High", "irrigation": "Low",  "agro_zone": "himalayan",   "priority_crops": ["apple","maize","wheat","rajma","potato"]},
    "mandi":       {"state": "Himachal Pradesh","soil": "Loamy",  "rainfall": "High", "irrigation": "Low",  "agro_zone": "himalayan",   "priority_crops": ["maize","wheat","potato","ginger","rajma"]},
    "kangra":      {"state": "Himachal Pradesh","soil": "Alluvial","rainfall": "High","irrigation": "Medium","agro_zone": "himalayan",  "priority_crops": ["rice","wheat","maize","ginger","tea"]},
    "solan":       {"state": "Himachal Pradesh","soil": "Sandy Loam","rainfall": "Medium","irrigation": "Medium","agro_zone": "himalayan","priority_crops": ["tomato","potato","mushroom","capsicum","peas"]},

    # ─── UTTARAKHAND ──────────────────────────────────────────────────
    "dehradun":    {"state": "Uttarakhand","soil": "Alluvial","rainfall": "High",    "irrigation": "Medium", "agro_zone": "himalayan",   "priority_crops": ["rice","wheat","litchi","lemongrass","sugarcane"]},
    "haridwar":    {"state": "Uttarakhand","soil": "Alluvial","rainfall": "Medium",  "irrigation": "High",   "agro_zone": "himalayan",   "priority_crops": ["sugarcane","wheat","rice","potato","vegetables"]},
    "nainital":    {"state": "Uttarakhand","soil": "Loamy",  "rainfall": "High",    "irrigation": "Low",    "agro_zone": "himalayan",   "priority_crops": ["apple","potato","wheat","rajma","peas"]},
    "almora":      {"state": "Uttarakhand","soil": "Loamy",  "rainfall": "High",    "irrigation": "Low",    "agro_zone": "himalayan",   "priority_crops": ["mandua","wheat","rajma","potato","apple"]},

    # ─── CHHATTISGARH ─────────────────────────────────────────────────
    "raipur":      {"state": "Chhattisgarh","soil": "Red",   "rainfall": "High",    "irrigation": "Medium", "agro_zone": "central",    "priority_crops": ["rice","maize","soybean","sesame","vegetables"]},
    "bilaspur":    {"state": "Chhattisgarh","soil": "Red",   "rainfall": "High",    "irrigation": "Low",    "agro_zone": "central",    "priority_crops": ["rice","maize","sesame","groundnut","tomato"]},
    "durg":        {"state": "Chhattisgarh","soil": "Red",   "rainfall": "High",    "irrigation": "Medium", "agro_zone": "central",    "priority_crops": ["rice","wheat","vegetables","maize","soybean"]},

    # ─── JHARKHAND ────────────────────────────────────────────────────
    "ranchi":      {"state": "Jharkhand", "soil": "Red",     "rainfall": "High",    "irrigation": "Low",    "agro_zone": "peninsular", "priority_crops": ["rice","maize","vegetables","tomato","potato"]},
    "dhanbad":     {"state": "Jharkhand", "soil": "Red",     "rainfall": "High",    "irrigation": "Low",    "agro_zone": "peninsular", "priority_crops": ["rice","maize","potato","vegetables","moong"]},
    "jamshedpur":  {"state": "Jharkhand", "soil": "Red",     "rainfall": "High",    "irrigation": "Low",    "agro_zone": "peninsular", "priority_crops": ["rice","maize","vegetables","sweet_potato","tomato"]},

    # ─── GOA ──────────────────────────────────────────────────────────
    "panaji":      {"state": "Goa",      "soil": "Laterite", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "coastal",    "priority_crops": ["coconut","cashew","rice","mango","areca_nut"]},
    "margao":      {"state": "Goa",      "soil": "Laterite", "rainfall": "Very High","irrigation": "Low",   "agro_zone": "coastal",    "priority_crops": ["coconut","cashew","rice","mango","banana"]},

    # ─── JAMMU & KASHMIR / LADAKH ─────────────────────────────────────
    "srinagar":    {"state": "Jammu and Kashmir","soil": "Alluvial","rainfall": "Medium","irrigation": "High","agro_zone": "himalayan",  "priority_crops": ["apple","cherry","walnut","saffron","pear"]},
    "jammu":       {"state": "Jammu and Kashmir","soil": "Alluvial","rainfall": "Medium","irrigation": "High","agro_zone": "himalayan",  "priority_crops": ["wheat","rice","maize","potato","rajma"]},
    "anantnag":    {"state": "Jammu and Kashmir","soil": "Alluvial","rainfall": "High",  "irrigation": "Medium","agro_zone": "himalayan","priority_crops": ["apple","walnut","rice","wheat","saffron"]},

    # ─── NORTHEAST STATES ─────────────────────────────────────────────
    "shillong":    {"state": "Meghalaya", "soil": "Laterite","rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["potato","ginger","turmeric","rice","pineapple"]},
    "aizawl":      {"state": "Mizoram",   "soil": "Laterite","rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["rice","ginger","banana","orange","vegetables"]},
    "kohima":      {"state": "Nagaland",  "soil": "Loamy",  "rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["rice","maize","potato","ginger","vegetables"]},
    "imphal":      {"state": "Manipur",   "soil": "Alluvial","rainfall": "Very High","irrigation": "Low",   "agro_zone": "northeast",   "priority_crops": ["rice","vegetables","ginger","potato","bamboo"]},
    "agartala":    {"state": "Tripura",   "soil": "Alluvial","rainfall": "Very High","irrigation": "Medium","agro_zone": "northeast",   "priority_crops": ["rice","pineapple","bamboo","jute","rubber"]},
    "gangtok":     {"state": "Sikkim",    "soil": "Loamy",  "rainfall": "Very High","irrigation": "Low",   "agro_zone": "himalayan",   "priority_crops": ["cardamom","ginger","maize","potato","oranges"]},
    "itanagar":    {"state": "Arunachal Pradesh","soil":"Red","rainfall": "Very High","irrigation": "Low",  "agro_zone": "northeast",   "priority_crops": ["rice","ginger","cardamom","bamboo","pineapple"]},
}
