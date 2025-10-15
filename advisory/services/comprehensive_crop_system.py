#!/usr/bin/env python3
"""
Comprehensive Crop Recommendation System
Uses real-time government data with exact user-specified weights
"""

import logging
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)

class ComprehensiveCropRecommendationSystem:
    """Comprehensive crop recommendation system with real-time government data"""
    
    def __init__(self):
        from .real_time_gov_data_service import real_time_gov_service
        self.gov_service = real_time_gov_service
        
        # User-specified weights (exact percentages)
        self.weights = {
            'climate_suitability': 0.30,    # 30% - Climate Suitability Scoring
            'market_analysis': 0.25,        # 25% - Market Analysis
            'soil_compatibility': 0.20,     # 20% - Soil Compatibility
            'seasonal_timing': 0.15,        # 15% - Seasonal Timing
            'risk_assessment': 0.05,        # 5% - Risk Assessment
            'profitability_analysis': 0.05  # 5% - Profitability Analysis
        }
        
        # Comprehensive Indian crop database
        self.crop_database = {
            'rice': {
                'climate': {'min_temp': 20, 'max_temp': 35, 'rainfall': 1000, 'humidity': 70},
                'soil': ['Alluvial', 'Clay', 'Loam'],
                'season': ['kharif', 'rabi'],
                'duration': 120,
                'base_price': 3000,
                'input_cost': 25000,
                'yield_per_hectare': 40
            },
            'wheat': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 500, 'humidity': 60},
                'soil': ['Alluvial', 'Loam', 'Sandy Loam'],
                'season': ['rabi'],
                'duration': 150,
                'base_price': 2500,
                'input_cost': 20000,
                'yield_per_hectare': 35
            },
            'maize': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 600, 'humidity': 65},
                'soil': ['Alluvial', 'Loam', 'Clay'],
                'season': ['kharif', 'rabi'],
                'duration': 100,
                'base_price': 2000,
                'input_cost': 18000,
                'yield_per_hectare': 45
            },
            'potato': {
                'climate': {'min_temp': 15, 'max_temp': 25, 'rainfall': 400, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam', 'Clay'],
                'season': ['rabi', 'kharif'],
                'duration': 90,
                'base_price': 1500,
                'input_cost': 30000,
                'yield_per_hectare': 200
            },
            'onion': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 300, 'humidity': 60},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['rabi', 'kharif'],
                'duration': 120,
                'base_price': 2000,
                'input_cost': 25000,
                'yield_per_hectare': 150
            },
            'tomato': {
                'climate': {'min_temp': 18, 'max_temp': 28, 'rainfall': 400, 'humidity': 65},
                'soil': ['Loam', 'Clay', 'Sandy Loam'],
                'season': ['rabi', 'kharif'],
                'duration': 100,
                'base_price': 3000,
                'input_cost': 35000,
                'yield_per_hectare': 300
            },
            'cotton': {
                'climate': {'min_temp': 20, 'max_temp': 35, 'rainfall': 800, 'humidity': 60},
                'soil': ['Black Cotton', 'Alluvial', 'Clay'],
                'season': ['kharif'],
                'duration': 180,
                'base_price': 6000,
                'input_cost': 40000,
                'yield_per_hectare': 15
            },
            'sugarcane': {
                'climate': {'min_temp': 20, 'max_temp': 35, 'rainfall': 1200, 'humidity': 70},
                'soil': ['Alluvial', 'Clay', 'Black Cotton'],
                'season': ['kharif'],
                'duration': 365,
                'base_price': 400,
                'input_cost': 60000,
                'yield_per_hectare': 800
            },
            'soybean': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 600, 'humidity': 65},
                'soil': ['Black Cotton', 'Alluvial', 'Loam'],
                'season': ['kharif'],
                'duration': 120,
                'base_price': 4000,
                'input_cost': 22000,
                'yield_per_hectare': 25
            },
            'mustard': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 400, 'humidity': 60},
                'soil': ['Alluvial', 'Loam', 'Sandy Loam'],
                'season': ['rabi'],
                'duration': 120,
                'base_price': 5500,
                'input_cost': 18000,
                'yield_per_hectare': 20
            },
            # PULSES & LEGUMES
            'chickpea': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 400, 'humidity': 60},
                'soil': ['Sandy Loam', 'Loam', 'Alluvial'],
                'season': ['rabi'],
                'duration': 120,
                'base_price': 4500,
                'input_cost': 20000,
                'yield_per_hectare': 15
            },
            'lentil': {
                'climate': {'min_temp': 8, 'max_temp': 22, 'rainfall': 350, 'humidity': 55},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['rabi'],
                'duration': 100,
                'base_price': 5000,
                'input_cost': 18000,
                'yield_per_hectare': 12
            },
            'black_gram': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 600, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['kharif'],
                'duration': 80,
                'base_price': 5500,
                'input_cost': 15000,
                'yield_per_hectare': 10
            },
            'green_gram': {
                'climate': {'min_temp': 18, 'max_temp': 28, 'rainfall': 500, 'humidity': 65},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 75,
                'base_price': 6000,
                'input_cost': 12000,
                'yield_per_hectare': 8
            },
            'pigeon_pea': {
                'climate': {'min_temp': 20, 'max_temp': 32, 'rainfall': 600, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['kharif'],
                'duration': 150,
                'base_price': 4800,
                'input_cost': 18000,
                'yield_per_hectare': 12
            },
            # OILSEEDS
            'sunflower': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 500, 'humidity': 65},
                'soil': ['Sandy Loam', 'Loam', 'Red Soil'],
                'season': ['kharif', 'rabi'],
                'duration': 100,
                'base_price': 4500,
                'input_cost': 20000,
                'yield_per_hectare': 18
            },
            'groundnut': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['kharif'],
                'duration': 120,
                'base_price': 6000,
                'input_cost': 30000,
                'yield_per_hectare': 25
            },
            'sesame': {
                'climate': {'min_temp': 20, 'max_temp': 32, 'rainfall': 400, 'humidity': 65},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 90,
                'base_price': 8000,
                'input_cost': 15000,
                'yield_per_hectare': 8
            },
            # MORE VEGETABLES
            'brinjal': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam', 'Red Soil'],
                'season': ['rabi', 'kharif'],
                'duration': 120,
                'base_price': 2500,
                'input_cost': 70000,
                'yield_per_hectare': 200
            },
            'okra': {
                'climate': {'min_temp': 20, 'max_temp': 32, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 60,
                'base_price': 4000,
                'input_cost': 50000,
                'yield_per_hectare': 150
            },
            'cabbage': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam', 'Alluvial'],
                'season': ['rabi'],
                'duration': 90,
                'base_price': 2000,
                'input_cost': 60000,
                'yield_per_hectare': 300
            },
            'cauliflower': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam', 'Alluvial'],
                'season': ['rabi'],
                'duration': 90,
                'base_price': 2500,
                'input_cost': 70000,
                'yield_per_hectare': 200
            },
            'carrot': {
                'climate': {'min_temp': 8, 'max_temp': 25, 'rainfall': 400, 'humidity': 65},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['rabi'],
                'duration': 90,
                'base_price': 3000,
                'input_cost': 50000,
                'yield_per_hectare': 250
            },
            'radish': {
                'climate': {'min_temp': 8, 'max_temp': 25, 'rainfall': 400, 'humidity': 65},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['rabi'],
                'duration': 45,
                'base_price': 2000,
                'input_cost': 30000,
                'yield_per_hectare': 200
            },
            'spinach': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam', 'Alluvial'],
                'season': ['rabi'],
                'duration': 30,
                'base_price': 4000,
                'input_cost': 25000,
                'yield_per_hectare': 100
            },
            'cucumber': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['kharif'],
                'duration': 60,
                'base_price': 3000,
                'input_cost': 40000,
                'yield_per_hectare': 200
            },
            'bottle_gourd': {
                'climate': {'min_temp': 20, 'max_temp': 32, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['kharif'],
                'duration': 90,
                'base_price': 2500,
                'input_cost': 35000,
                'yield_per_hectare': 150
            },
            'bitter_gourd': {
                'climate': {'min_temp': 20, 'max_temp': 32, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['kharif'],
                'duration': 90,
                'base_price': 5000,
                'input_cost': 40000,
                'yield_per_hectare': 100
            },
            'ridge_gourd': {
                'climate': {'min_temp': 20, 'max_temp': 32, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['kharif'],
                'duration': 90,
                'base_price': 3000,
                'input_cost': 35000,
                'yield_per_hectare': 120
            },
            # FRUITS
            'mango': {
                'climate': {'min_temp': 20, 'max_temp': 35, 'rainfall': 800, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years to fruit
                'base_price': 8000,
                'input_cost': 150000,
                'yield_per_hectare': 150
            },
            'banana': {
                'climate': {'min_temp': 20, 'max_temp': 35, 'rainfall': 1000, 'humidity': 75},
                'soil': ['Alluvial', 'Sandy Loam', 'Clay Loam'],
                'season': ['perennial'],
                'duration': 365,
                'base_price': 2000,
                'input_cost': 80000,
                'yield_per_hectare': 400
            },
            'papaya': {
                'climate': {'min_temp': 20, 'max_temp': 35, 'rainfall': 800, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 365,
                'base_price': 3000,
                'input_cost': 60000,
                'yield_per_hectare': 200
            },
            'guava': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 600, 'humidity': 65},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['perennial'],
                'duration': 730,  # 2 years to fruit
                'base_price': 4000,
                'input_cost': 80000,
                'yield_per_hectare': 100
            },
            'pomegranate': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 500, 'humidity': 60},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years to fruit
                'base_price': 6000,
                'input_cost': 120000,
                'yield_per_hectare': 80
            },
            'citrus': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 600, 'humidity': 65},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years to fruit
                'base_price': 5000,
                'input_cost': 100000,
                'yield_per_hectare': 120
            },
            'grapes': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 500, 'humidity': 60},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 365,
                'base_price': 8000,
                'input_cost': 150000,
                'yield_per_hectare': 200
            },
            # SPICES
            'turmeric': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 1000, 'humidity': 75},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['kharif'],
                'duration': 240,
                'base_price': 10000,
                'input_cost': 80000,
                'yield_per_hectare': 25
            },
            'ginger': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 1000, 'humidity': 75},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 240,
                'base_price': 12000,
                'input_cost': 90000,
                'yield_per_hectare': 20
            },
            'chilli': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 600, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['kharif', 'rabi'],
                'duration': 120,
                'base_price': 15000,
                'input_cost': 60000,
                'yield_per_hectare': 30
            },
            'coriander': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 400, 'humidity': 65},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['rabi'],
                'duration': 90,
                'base_price': 8000,
                'input_cost': 30000,
                'yield_per_hectare': 15
            },
            'cumin': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 300, 'humidity': 60},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['rabi'],
                'duration': 120,
                'base_price': 12000,
                'input_cost': 25000,
                'yield_per_hectare': 8
            },
            'cardamom': {
                'climate': {'min_temp': 15, 'max_temp': 25, 'rainfall': 1500, 'humidity': 80},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years to harvest
                'base_price': 20000,
                'input_cost': 200000,
                'yield_per_hectare': 10
            },
            'black_pepper': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 1500, 'humidity': 80},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years to harvest
                'base_price': 15000,
                'input_cost': 150000,
                'yield_per_hectare': 12
            },
            # MEDICINAL PLANTS
            'aloe_vera': {
                'climate': {'min_temp': 20, 'max_temp': 35, 'rainfall': 300, 'humidity': 60},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 365,
                'base_price': 5000,
                'input_cost': 40000,
                'yield_per_hectare': 50
            },
            'tulsi': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['perennial'],
                'duration': 180,
                'base_price': 8000,
                'input_cost': 30000,
                'yield_per_hectare': 20
            },
            'ashwagandha': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 400, 'humidity': 60},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['rabi'],
                'duration': 180,
                'base_price': 15000,
                'input_cost': 50000,
                'yield_per_hectare': 8
            },
            # FLOWERS
            'marigold': {
                'climate': {'min_temp': 15, 'max_temp': 30, 'rainfall': 500, 'humidity': 65},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['rabi', 'kharif'],
                'duration': 90,
                'base_price': 3000,
                'input_cost': 40000,
                'yield_per_hectare': 100
            },
            'rose': {
                'climate': {'min_temp': 15, 'max_temp': 25, 'rainfall': 600, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['perennial'],
                'duration': 365,
                'base_price': 5000,
                'input_cost': 80000,
                'yield_per_hectare': 80
            },
            'jasmine': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 600, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 365,
                'base_price': 4000,
                'input_cost': 60000,
                'yield_per_hectare': 60
            },
            # ADDITIONAL CEREALS
            'barley': {
                'climate': {'min_temp': 8, 'max_temp': 22, 'rainfall': 400, 'humidity': 55},
                'soil': ['Sandy Loam', 'Loam', 'Alluvial'],
                'season': ['rabi'],
                'duration': 110,
                'base_price': 1800,
                'input_cost': 18000,
                'yield_per_hectare': 25
            },
            'sorghum': {
                'climate': {'min_temp': 18, 'max_temp': 32, 'rainfall': 500, 'humidity': 65},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['kharif'],
                'duration': 100,
                'base_price': 1600,
                'input_cost': 15000,
                'yield_per_hectare': 20
            },
            # FIBER CROPS
            'jute': {
                'climate': {'min_temp': 24, 'max_temp': 35, 'rainfall': 1000, 'humidity': 80},
                'soil': ['Alluvial', 'Clay Loam'],
                'season': ['kharif'],
                'duration': 120,
                'base_price': 4500,
                'input_cost': 25000,
                'yield_per_hectare': 30
            },
            # MISSING CEREALS
            'bajra': {
                'climate': {'min_temp': 20, 'max_temp': 32, 'rainfall': 400, 'humidity': 60},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 80,
                'base_price': 2200,
                'input_cost': 12000,
                'yield_per_hectare': 15
            },
            'jowar': {
                'climate': {'min_temp': 18, 'max_temp': 30, 'rainfall': 500, 'humidity': 65},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['kharif'],
                'duration': 90,
                'base_price': 2800,
                'input_cost': 14000,
                'yield_per_hectare': 18
            },
            'ragi': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 600, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 100,
                'base_price': 3200,
                'input_cost': 16000,
                'yield_per_hectare': 12
            },
            # MISSING PULSES
            'moong': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 500, 'humidity': 65},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 70,
                'base_price': 7755,
                'input_cost': 10000,
                'yield_per_hectare': 8
            },
            'urad': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 500, 'humidity': 65},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 75,
                'base_price': 6975,
                'input_cost': 11000,
                'yield_per_hectare': 8
            },
            'tur': {
                'climate': {'min_temp': 20, 'max_temp': 32, 'rainfall': 600, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['kharif'],
                'duration': 150,
                'base_price': 6600,
                'input_cost': 15000,
                'yield_per_hectare': 10
            },
            # MISSING OILSEEDS
            'castor': {
                'climate': {'min_temp': 20, 'max_temp': 35, 'rainfall': 500, 'humidity': 60},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['kharif'],
                'duration': 150,
                'base_price': 7000,
                'input_cost': 20000,
                'yield_per_hectare': 12
            },
            # MISSING FRUITS
            'strawberry': {
                'climate': {'min_temp': 10, 'max_temp': 25, 'rainfall': 500, 'humidity': 70},
                'soil': ['Sandy Loam', 'Loam'],
                'season': ['rabi'],
                'duration': 120,
                'base_price': 15000,
                'input_cost': 80000,
                'yield_per_hectare': 50
            },
            # MISSING CASH CROPS
            'tea': {
                'climate': {'min_temp': 15, 'max_temp': 25, 'rainfall': 1200, 'humidity': 80},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years
                'base_price': 200,
                'input_cost': 200000,
                'yield_per_hectare': 2000
            },
            'coffee': {
                'climate': {'min_temp': 15, 'max_temp': 25, 'rainfall': 1000, 'humidity': 75},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years
                'base_price': 300,
                'input_cost': 180000,
                'yield_per_hectare': 1000
            },
            'rubber': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 1200, 'humidity': 80},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 2190,  # 6 years
                'base_price': 150,
                'input_cost': 300000,
                'yield_per_hectare': 1500
            },
            # MISSING SPICES
            'cinnamon': {
                'climate': {'min_temp': 20, 'max_temp': 30, 'rainfall': 800, 'humidity': 70},
                'soil': ['Sandy Loam', 'Red Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years
                'base_price': 25000,
                'input_cost': 120000,
                'yield_per_hectare': 100
            },
            # MISSING MEDICINAL
            'neem': {
                'climate': {'min_temp': 15, 'max_temp': 35, 'rainfall': 400, 'humidity': 60},
                'soil': ['Sandy Loam', 'Red Soil', 'Black Soil'],
                'season': ['perennial'],
                'duration': 1095,  # 3 years
                'base_price': 5000,
                'input_cost': 80000,
                'yield_per_hectare': 200
            }
        }
    
    def get_comprehensive_recommendations(self, latitude, longitude, soil_type=None, season='kharif'):
        """Get comprehensive crop recommendations with real-time government data"""
        
        # 1. Fetch real-time government data
        weather_data = self.gov_service.get_real_time_weather_data(latitude, longitude)
        soil_data = self.gov_service.get_real_time_soil_data(latitude, longitude)
        fertilizer_prices = self.gov_service.get_real_time_fertilizer_prices(latitude, longitude)
        
        # Use provided soil_type or detected soil_type
        if not soil_type:
            soil_type = soil_data['soil_type']
        
        # 2. Calculate scores for each crop
        crop_scores = {}
        crop_details = {}
        
        for crop_name, crop_info in self.crop_database.items():
            # Calculate each component score
            climate_score = self._calculate_climate_suitability(crop_name, crop_info, weather_data)
            market_score = self._calculate_market_analysis(crop_name, crop_info, latitude, longitude)
            soil_score = self._calculate_soil_compatibility(crop_name, crop_info, soil_type, soil_data)
            seasonal_score = self._calculate_seasonal_timing(crop_name, crop_info, season)
            risk_score = self._calculate_risk_assessment(crop_name, crop_info, weather_data)
            profitability_score = self._calculate_profitability_analysis(crop_name, crop_info, market_score)
            
            # Calculate weighted total score
            total_score = (
                climate_score * self.weights['climate_suitability'] +
                market_score * self.weights['market_analysis'] +
                soil_score * self.weights['soil_compatibility'] +
                seasonal_score * self.weights['seasonal_timing'] +
                risk_score * self.weights['risk_assessment'] +
                profitability_score * self.weights['profitability_analysis']
            )
            
            crop_scores[crop_name] = total_score
            
            # Store detailed analysis
            crop_details[crop_name] = {
                'climate_score': climate_score,
                'market_score': market_score,
                'soil_score': soil_score,
                'seasonal_score': seasonal_score,
                'risk_score': risk_score,
                'profitability_score': profitability_score,
                'total_score': total_score,
                'expected_profit': self._calculate_expected_profit(crop_name, crop_info, market_score),
                'input_cost': crop_info['input_cost'],
                'duration_days': crop_info['duration'],
                'yield_per_hectare': crop_info['yield_per_hectare']
            }
        
        # 3. Sort crops by total score
        sorted_crops = sorted(crop_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 4. Generate recommendations
        recommendations = []
        for i, (crop_name, score) in enumerate(sorted_crops[:8]):  # Top 8 crops
            details = crop_details[crop_name]
            
            recommendation = {
                'crop_name': crop_name.title(),
                'crop': crop_name,
                'suitability_score': round(score, 3),
                'climate_suitability': round(details['climate_score'] * 100, 1),
                'market_analysis': round(details['market_score'] * 100, 1),
                'soil_compatibility': round(details['soil_score'] * 100, 1),
                'seasonal_timing': round(details['seasonal_score'] * 100, 1),
                'risk_assessment': round(details['risk_score'] * 100, 1),
                'profitability_analysis': round(details['profitability_score'] * 100, 1),
                'expected_profit': round(details['expected_profit'], 2),
                'input_cost': details['input_cost'],
                'duration_days': details['duration_days'],
                'yield_per_hectare': details['yield_per_hectare'],
                'reason': self._generate_recommendation_reason(crop_name, details, weather_data, soil_data),
                'data_sources': {
                    'weather': weather_data['source'],
                    'soil': soil_data['source'],
                    'market': 'Real-time Government Data'
                },
                'timestamp': datetime.now().isoformat()
            }
            
            recommendations.append(recommendation)
        
        return {
            'recommendations': recommendations,
            'weather_data': weather_data,
            'soil_data': soil_data,
            'fertilizer_prices': fertilizer_prices,
            'location': {'latitude': latitude, 'longitude': longitude},
            'soil_type': soil_type,
            'season': season,
            'weights_used': self.weights,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _calculate_climate_suitability(self, crop_name, crop_info, weather_data):
        """Calculate climate suitability score (30% weight) with enhanced location-specific analysis"""
        crop_climate = crop_info['climate']
        current_temp = weather_data['temperature']
        current_humidity = weather_data['humidity']
        current_rainfall = weather_data['rainfall']
        
        # Get region for location-specific climate analysis
        region = self._get_region_from_coordinates(weather_data.get('latitude', 25), weather_data.get('longitude', 80))
        
        # Enhanced temperature suitability with region-specific adjustments
        temp_score = 1.0
        if current_temp < crop_climate['min_temp']:
            temp_score = max(0.1, (current_temp + 10) / crop_climate['min_temp'])
        elif current_temp > crop_climate['max_temp']:
            temp_score = max(0.1, (crop_climate['max_temp'] + 10) / current_temp)
        
        # Region-specific temperature adjustments
        region_temp_adjustments = {
            'north': 1.0, 'central': 0.95, 'south': 0.9, 'east': 0.9, 'northeast': 0.85
        }
        temp_score *= region_temp_adjustments.get(region, 0.9)
        
        # Enhanced humidity suitability
        humidity_diff = abs(current_humidity - crop_climate['humidity'])
        humidity_score = max(0.1, 1.0 - (humidity_diff / 100))
        
        # Region-specific humidity adjustments
        region_humidity_adjustments = {
            'north': 1.0, 'central': 0.95, 'south': 0.9, 'east': 0.9, 'northeast': 0.85
        }
        humidity_score *= region_humidity_adjustments.get(region, 0.9)
        
        # Enhanced rainfall suitability with seasonal considerations
        rainfall_diff = abs(current_rainfall - crop_climate['rainfall'])
        rainfall_score = max(0.1, 1.0 - (rainfall_diff / 1000))
        
        # Region-specific rainfall adjustments
        region_rainfall_adjustments = {
            'north': 1.0, 'central': 0.95, 'south': 0.9, 'east': 0.9, 'northeast': 0.85
        }
        rainfall_score *= region_rainfall_adjustments.get(region, 0.9)
        
        # Crop-specific climate preferences
        crop_climate_preferences = {
            'rice': {'temp_weight': 0.4, 'humidity_weight': 0.4, 'rainfall_weight': 0.2},
            'wheat': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'maize': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'potato': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'onion': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'tomato': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'cotton': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            'sugarcane': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            'soybean': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'mustard': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            # Pulses
            'chickpea': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'lentil': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'black_gram': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'green_gram': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'pigeon_pea': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            # Oilseeds
            'sunflower': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'groundnut': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'sesame': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            # Vegetables
            'brinjal': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'okra': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'cabbage': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'cauliflower': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'carrot': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'radish': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'spinach': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'cucumber': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'bottle_gourd': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'bitter_gourd': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'ridge_gourd': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            # Fruits
            'mango': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            'banana': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            'papaya': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            'guava': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'pomegranate': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'citrus': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'grapes': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            # Spices
            'turmeric': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            'ginger': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            'chilli': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'coriander': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'cumin': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'cardamom': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            'black_pepper': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4},
            # Medicinal plants
            'aloe_vera': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'tulsi': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'ashwagandha': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            # Flowers
            'marigold': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'rose': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            'jasmine': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            # Additional cereals
            'barley': {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2},
            'sorghum': {'temp_weight': 0.4, 'humidity_weight': 0.3, 'rainfall_weight': 0.3},
            # Fiber crops
            'jute': {'temp_weight': 0.3, 'humidity_weight': 0.3, 'rainfall_weight': 0.4}
        }
        
        preferences = crop_climate_preferences.get(crop_name, {'temp_weight': 0.5, 'humidity_weight': 0.3, 'rainfall_weight': 0.2})
        
        # Weighted average with crop-specific preferences
        climate_score = (
            temp_score * preferences['temp_weight'] +
            humidity_score * preferences['humidity_weight'] +
            rainfall_score * preferences['rainfall_weight']
        )
        
        return min(1.0, max(0.1, climate_score))
    
    def _calculate_market_analysis(self, crop_name, crop_info, latitude, longitude):
        """Calculate market analysis score (25% weight) with location-specific pricing"""
        # Get real-time market price
        market_data = self.gov_service.get_real_time_market_prices(crop_name, latitude, longitude)
        current_price = market_data['price']
        base_price = crop_info['base_price']
        
        # Enhanced price trend analysis with location factors
        price_ratio = current_price / base_price
        
        # Location-specific price multipliers
        region = self._get_region_from_coordinates(latitude, longitude)
        region_multipliers = {
            'north': 1.1, 'central': 1.0, 'south': 0.9, 'east': 0.95, 'northeast': 0.85
        }
        region_multiplier = region_multipliers.get(region, 1.0)
        
        # Adjust price score based on region and actual price
        if price_ratio > 1.3:  # Price is 30% above base
            price_score = 0.95
        elif price_ratio > 1.1:  # Price is 10% above base
            price_score = 0.8
        elif price_ratio > 0.9:  # Price is near base
            price_score = 0.6
        elif price_ratio > 0.7:  # Price is below base
            price_score = 0.4
        else:  # Price is significantly below base
            price_score = 0.2
        
        # Apply region multiplier
        price_score *= region_multiplier
        
        # Crop-specific demand analysis
        demand_scores = {
            'rice': 0.9, 'wheat': 0.85, 'maize': 0.7, 'potato': 0.8,
            'onion': 0.75, 'tomato': 0.8, 'cotton': 0.7, 'sugarcane': 0.9,
            'soybean': 0.8, 'mustard': 0.75
        }
        demand_score = demand_scores.get(crop_name, 0.6)
        
        # Market accessibility (based on location and crop)
        if region == 'north':  # Best market access
            market_access_score = 0.9
        elif region == 'central':  # Good market access
            market_access_score = 0.8
        elif region == 'south':  # Moderate market access
            market_access_score = 0.7
        elif region == 'east':  # Moderate market access
            market_access_score = 0.7
        else:  # Limited market access
            market_access_score = 0.6
        
        # Weighted average
        market_score = (price_score * 0.5 + demand_score * 0.3 + market_access_score * 0.2)
        return min(1.0, max(0.1, market_score))
    
    def _calculate_soil_compatibility(self, crop_name, crop_info, soil_type, soil_data):
        """Calculate soil compatibility score (20% weight)"""
        suitable_soils = crop_info['soil']
        
        # Direct soil type match
        if soil_type in suitable_soils:
            soil_type_score = 1.0
        else:
            soil_type_score = 0.3
        
        # pH compatibility
        crop_ph_range = self._get_crop_ph_range(crop_name)
        current_ph = soil_data['ph']
        
        if crop_ph_range[0] <= current_ph <= crop_ph_range[1]:
            ph_score = 1.0
        else:
            ph_diff = min(abs(current_ph - crop_ph_range[0]), abs(current_ph - crop_ph_range[1]))
            ph_score = max(0.1, 1.0 - (ph_diff / 2))
        
        # Nutrient availability
        nitrogen = soil_data['nitrogen']
        phosphorus = soil_data['phosphorus']
        potassium = soil_data['potassium']
        
        nutrient_score = min(1.0, (nitrogen + phosphorus + potassium) / 1.5)
        
        # Weighted average
        soil_score = (soil_type_score * 0.4 + ph_score * 0.3 + nutrient_score * 0.3)
        return min(1.0, max(0.1, soil_score))
    
    def _calculate_seasonal_timing(self, crop_name, crop_info, season):
        """Calculate seasonal timing score (15% weight)"""
        suitable_seasons = crop_info['season']
        
        if season in suitable_seasons:
            seasonal_score = 1.0
        else:
            seasonal_score = 0.2
        
        # Duration analysis
        duration = crop_info['duration']
        if duration <= 90:  # Short duration - good for quick returns
            duration_score = 0.9
        elif duration <= 150:  # Medium duration
            duration_score = 0.7
        else:  # Long duration
            duration_score = 0.5
        
        # Weighted average
        timing_score = (seasonal_score * 0.7 + duration_score * 0.3)
        return min(1.0, max(0.1, timing_score))
    
    def _calculate_risk_assessment(self, crop_name, crop_info, weather_data):
        """Calculate risk assessment score (5% weight)"""
        # Weather risk
        temp = weather_data['temperature']
        rainfall = weather_data['rainfall']
        
        # Temperature risk
        if 15 <= temp <= 30:  # Optimal temperature range
            temp_risk = 0.1
        elif 10 <= temp <= 35:  # Acceptable range
            temp_risk = 0.3
        else:  # High risk
            temp_risk = 0.7
        
        # Rainfall risk
        if 200 <= rainfall <= 800:  # Good rainfall
            rainfall_risk = 0.1
        elif 100 <= rainfall <= 1200:  # Acceptable rainfall
            rainfall_risk = 0.3
        else:  # High risk
            rainfall_risk = 0.6
        
        # Crop-specific risk factors
        crop_risk_factors = {
            'rice': 0.2, 'wheat': 0.1, 'maize': 0.3, 'potato': 0.4,
            'onion': 0.3, 'tomato': 0.5, 'cotton': 0.4, 'sugarcane': 0.2,
            'soybean': 0.3, 'mustard': 0.2
        }
        
        crop_risk = crop_risk_factors.get(crop_name, 0.3)
        
        # Weighted average (lower risk = higher score)
        risk_score = 1.0 - (temp_risk * 0.3 + rainfall_risk * 0.3 + crop_risk * 0.4)
        return min(1.0, max(0.1, risk_score))
    
    def _calculate_profitability_analysis(self, crop_name, crop_info, market_score):
        """Calculate profitability analysis score (5% weight)"""
        base_price = crop_info['base_price']
        input_cost = crop_info['input_cost']
        yield_per_hectare = crop_info['yield_per_hectare']
        
        # Calculate expected revenue
        expected_revenue = base_price * yield_per_hectare
        
        # Calculate profit margin
        if input_cost > 0:
            profit_margin = (expected_revenue - input_cost) / input_cost
        else:
            profit_margin = 0
        
        # Profitability score based on margin
        if profit_margin > 0.5:  # >50% margin
            profitability_score = 0.9
        elif profit_margin > 0.2:  # >20% margin
            profitability_score = 0.7
        elif profit_margin > 0:  # Positive margin
            profitability_score = 0.5
        else:  # Negative margin
            profitability_score = 0.2
        
        return min(1.0, max(0.1, profitability_score))
    
    def _calculate_expected_profit(self, crop_name, crop_info, market_score):
        """Calculate expected profit per hectare"""
        base_price = crop_info['base_price']
        input_cost = crop_info['input_cost']
        yield_per_hectare = crop_info['yield_per_hectare']
        
        # Adjust price based on market score
        adjusted_price = base_price * (0.5 + market_score * 0.5)
        
        expected_revenue = adjusted_price * yield_per_hectare
        expected_profit = expected_revenue - input_cost
        
        return expected_profit
    
    def _get_crop_ph_range(self, crop_name):
        """Get optimal pH range for crop"""
        ph_ranges = {
            'rice': (5.5, 7.0), 'wheat': (6.0, 7.5), 'maize': (5.5, 7.0),
            'potato': (4.5, 6.0), 'onion': (6.0, 7.0), 'tomato': (6.0, 7.0),
            'cotton': (6.0, 8.0), 'sugarcane': (6.0, 7.5), 'soybean': (6.0, 7.0),
            'mustard': (6.0, 7.5)
        }
        return ph_ranges.get(crop_name, (6.0, 7.0))
    
    def _get_region_from_coordinates(self, latitude, longitude):
        """Get region from coordinates"""
        if 28 <= latitude <= 37 and 76 <= longitude <= 97:
            return 'north'
        elif 20 <= latitude <= 28 and 70 <= longitude <= 88:
            return 'central'
        elif 8 <= latitude <= 20 and 70 <= longitude <= 80:
            return 'south'
        elif 24 <= latitude <= 28 and 88 <= longitude <= 97:
            return 'east'
        elif 22 <= latitude <= 30 and 88 <= longitude <= 97:
            return 'northeast'
        else:
            return 'central'  # Default

    def _generate_recommendation_reason(self, crop_name, details, weather_data, soil_data):
        """Generate a reason for the crop recommendation"""
        reasons = []
        
        # Climate suitability reason
        if details.get('climate_score', 0) > 0.7:
            reasons.append(f"Excellent climate match for {crop_name}")
        elif details.get('climate_score', 0) > 0.5:
            reasons.append(f"Good climate conditions for {crop_name}")
        else:
            reasons.append(f"Moderate climate suitability for {crop_name}")
        
        # Market analysis reason
        if details.get('market_score', 0) > 0.7:
            reasons.append("High market demand and good prices")
        elif details.get('market_score', 0) > 0.5:
            reasons.append("Stable market conditions")
        else:
            reasons.append("Moderate market potential")
        
        # Soil compatibility reason
        if details.get('soil_score', 0) > 0.7:
            reasons.append("Excellent soil compatibility")
        elif details.get('soil_score', 0) > 0.5:
            reasons.append("Good soil conditions")
        else:
            reasons.append("Moderate soil suitability")
        
        # Seasonal timing reason
        if details.get('seasonal_score', 0) > 0.7:
            reasons.append("Optimal planting season")
        elif details.get('seasonal_score', 0) > 0.5:
            reasons.append("Good seasonal timing")
        else:
            reasons.append("Moderate seasonal suitability")
        
        # Profitability reason
        if details.get('profitability_score', 0) > 0.7:
            reasons.append("High profit potential")
        elif details.get('profitability_score', 0) > 0.5:
            reasons.append("Good profit margins")
        else:
            reasons.append("Moderate profitability")
        
        return "; ".join(reasons)

    def _calculate_profitability_analysis(self, crop_name, crop_info, market_score):
        """Calculate profitability analysis score (5% weight)"""
        base_price = crop_info['base_price']
        input_cost = crop_info['input_cost']
        yield_per_hectare = crop_info['yield_per_hectare']
        
        # Calculate expected revenue
        expected_revenue = base_price * yield_per_hectare
        
        # Calculate profit margin
        if input_cost > 0:
            profit_margin = (expected_revenue - input_cost) / input_cost
        else:
            profit_margin = 0
        
        # Profitability score based on margin
        if profit_margin > 0.5:  # >50% margin
            profitability_score = 0.9
        elif profit_margin > 0.2:  # >20% margin
            profitability_score = 0.7
        elif profit_margin > 0:  # Positive margin
            profitability_score = 0.5
        else:  # Negative margin
            profitability_score = 0.2
        
        return min(1.0, max(0.1, profitability_score))
    
    def _calculate_expected_profit(self, crop_name, crop_info, market_score):
        """Calculate expected profit per hectare"""
        base_price = crop_info['base_price']
        input_cost = crop_info['input_cost']
        yield_per_hectare = crop_info['yield_per_hectare']
        
        # Adjust price based on market score
        adjusted_price = base_price * (0.5 + market_score * 0.5)
        
        expected_revenue = adjusted_price * yield_per_hectare
        expected_profit = expected_revenue - input_cost
        
        return expected_profit
    
    def _get_crop_ph_range(self, crop_name):
        """Get optimal pH range for crop"""
        ph_ranges = {
            'rice': (5.5, 7.0), 'wheat': (6.0, 7.5), 'maize': (5.5, 7.0),
            'potato': (4.5, 6.0), 'onion': (6.0, 7.0), 'tomato': (6.0, 7.0),
            'cotton': (6.0, 8.0), 'sugarcane': (6.0, 7.5), 'soybean': (6.0, 7.0),
            'mustard': (6.0, 7.5)
        }
        return ph_ranges.get(crop_name, (6.0, 7.0))
    
    def _get_region_from_coordinates(self, latitude, longitude):
        """Get region from coordinates"""
        if 28 <= latitude <= 37 and 76 <= longitude <= 97:
            return 'north'
        elif 20 <= latitude <= 28 and 70 <= longitude <= 88:
            return 'central'
        elif 8 <= latitude <= 20 and 70 <= longitude <= 80:
            return 'south'
        elif 24 <= latitude <= 28 and 88 <= longitude <= 97:
            return 'east'
        elif 22 <= latitude <= 30 and 88 <= longitude <= 97:
            return 'northeast'
        else:
            return 'central'  # Default

    def _generate_recommendation_reason(self, crop_name, details, weather_data, soil_data):
        """Generate a reason for the crop recommendation"""
        reasons = []
        
        # Climate suitability reason
        if details.get('climate_score', 0) > 0.7:
            reasons.append(f"Excellent climate match for {crop_name}")
        elif details.get('climate_score', 0) > 0.5:
            reasons.append(f"Good climate conditions for {crop_name}")
        else:
            reasons.append(f"Moderate climate suitability for {crop_name}")
        
        # Market analysis reason
        if details.get('market_score', 0) > 0.7:
            reasons.append("High market demand and good prices")
        elif details.get('market_score', 0) > 0.5:
            reasons.append("Stable market conditions")
        else:
            reasons.append("Moderate market potential")
        
        # Soil compatibility reason
        if details.get('soil_score', 0) > 0.7:
            reasons.append("Excellent soil compatibility")
        elif details.get('soil_score', 0) > 0.5:
            reasons.append("Good soil conditions")
        else:
            reasons.append("Moderate soil suitability")
        
        # Seasonal timing reason
        if details.get('seasonal_score', 0) > 0.7:
            reasons.append("Optimal planting season")
        elif details.get('seasonal_score', 0) > 0.5:
            reasons.append("Good seasonal timing")
        else:
            reasons.append("Moderate seasonal suitability")
        
        # Profitability reason
        if details.get('profitability_score', 0) > 0.7:
            reasons.append("High profit potential")
        elif details.get('profitability_score', 0) > 0.5:
            reasons.append("Good profit margins")
        else:
            reasons.append("Moderate profitability")
        
        return "; ".join(reasons)

# Global instance
comprehensive_crop_system = ComprehensiveCropRecommendationSystem()
