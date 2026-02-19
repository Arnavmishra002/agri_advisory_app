#!/usr/bin/env python3
"""
Weather Forecast Integration for Crop Recommendations
Analyzes 7-day forecast to improve recommendation accuracy
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class WeatherForecastAnalyzer:
    """Analyze weather forecast for crop suitability"""
    
    def __init__(self):
        # Crop water requirements
        self.water_requirements = {
            'high': ['rice', 'sugarcane', 'jute', 'banana'],
            'moderate': ['wheat', 'maize', 'cotton', 'soybean'],
            'low': ['bajra', 'jowar', 'groundnut', 'mustard']
        }
        
        # Temperature preferences (°C)
        self.temp_preferences = {
            'wheat': {'min': 10, 'max': 25, 'optimal': 20},
            'rice': {'min': 20, 'max': 35, 'optimal': 28},
            'maize': {'min': 18, 'max': 32, 'optimal': 25},
            'cotton': {'min': 21, 'max': 35, 'optimal': 28},
            'sugarcane': {'min': 20, 'max': 35, 'optimal': 28},
            'potato': {'min': 15, 'max': 25, 'optimal': 20},
            'onion': {'min': 13, 'max': 27, 'optimal': 20},
            'tomato': {'min': 18, 'max': 27, 'optimal': 23}
        }
    
    def analyze_forecast(self, weather_data: Dict, crop_name: str) -> Dict[str, Any]:
        """
        Analyze 7-day forecast for crop suitability
        
        Returns:
        - suitability_score: 0-20 points
        - warnings: List of weather-related warnings
        - recommendations: Timing recommendations
        """
        try:
            forecast = weather_data.get('forecast_7day', [])
            
            if not forecast:
                return {
                    'suitability_score': 10,  # Neutral score
                    'warnings': [],
                    'recommendations': ['Weather forecast unavailable'],
                    'confidence': 0.5
                }
            
            # Analyze temperature suitability
            temp_score = self._analyze_temperature(forecast, crop_name)
            
            # Analyze rainfall suitability
            rainfall_score = self._analyze_rainfall(forecast, crop_name)
            
            # Check for extreme weather
            warnings = self._check_extreme_weather(forecast)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                forecast, crop_name, temp_score, rainfall_score
            )
            
            # Calculate total score (0-20 points)
            total_score = (temp_score['score'] + rainfall_score['score']) / 2
            
            return {
                'suitability_score': round(total_score, 1),
                'temperature_analysis': temp_score,
                'rainfall_analysis': rainfall_score,
                'warnings': warnings,
                'recommendations': recommendations,
                'confidence': 0.85 if len(forecast) >= 5 else 0.65
            }
            
        except Exception as e:
            logger.error(f"Error analyzing forecast: {e}")
            return {
                'suitability_score': 10,
                'warnings': [],
                'recommendations': [],
                'confidence': 0.5
            }
    
    def _analyze_temperature(self, forecast: List[Dict], crop_name: str) -> Dict:
        """Analyze temperature suitability"""
        temps = []
        
        for day in forecast:
            temp_str = day.get('temperature', '25°C')
            if isinstance(temp_str, str):
                temp = float(temp_str.replace('°C', '').strip())
            else:
                temp = float(temp_str)
            temps.append(temp)
        
        if not temps:
            return {'score': 10, 'status': 'unknown'}
        
        avg_temp = sum(temps) / len(temps)
        min_temp = min(temps)
        max_temp = max(temps)
        
        # Get crop preferences
        prefs = self.temp_preferences.get(crop_name, {
            'min': 15, 'max': 30, 'optimal': 23
        })
        
        # Calculate score based on temperature range
        if prefs['min'] <= avg_temp <= prefs['max']:
            # Within acceptable range
            deviation = abs(avg_temp - prefs['optimal'])
            score = 20 - (deviation * 2)  # Lose 2 points per degree deviation
            score = max(10, min(20, score))
            status = 'optimal' if score >= 18 else 'suitable'
        elif avg_temp < prefs['min']:
            score = max(0, 10 - (prefs['min'] - avg_temp) * 3)
            status = 'too_cold'
        else:
            score = max(0, 10 - (avg_temp - prefs['max']) * 3)
            status = 'too_hot'
        
        return {
            'score': round(score, 1),
            'avg_temp': round(avg_temp, 1),
            'min_temp': round(min_temp, 1),
            'max_temp': round(max_temp, 1),
            'optimal_temp': prefs['optimal'],
            'status': status
        }
    
    def _analyze_rainfall(self, forecast: List[Dict], crop_name: str) -> Dict:
        """Analyze rainfall suitability"""
        rainy_days = 0
        
        for day in forecast:
            condition = str(day.get('condition', '')).lower()
            if 'rain' in condition or 'बारिश' in condition or 'shower' in condition:
                rainy_days += 1
        
        # Determine crop water requirement
        water_req = 'moderate'
        for req_level, crops in self.water_requirements.items():
            if crop_name in crops:
                water_req = req_level
                break
        
        # Score based on water requirement match
        if water_req == 'high':
            # Needs lots of water
            if rainy_days >= 4:
                score = 20
                status = 'excellent'
            elif rainy_days >= 2:
                score = 15
                status = 'good'
            else:
                score = 8
                status = 'needs_irrigation'
        elif water_req == 'moderate':
            # Moderate water needs
            if 2 <= rainy_days <= 4:
                score = 20
                status = 'optimal'
            elif rainy_days >= 5:
                score = 12
                status = 'excess_rain_risk'
            else:
                score = 14
                status = 'acceptable'
        else:  # low water requirement
            # Drought resistant
            if rainy_days <= 2:
                score = 20
                status = 'excellent'
            elif rainy_days <= 4:
                score = 15
                status = 'acceptable'
            else:
                score = 10
                status = 'excess_moisture'
        
        return {
            'score': score,
            'rainy_days': rainy_days,
            'water_requirement': water_req,
            'status': status
        }
    
    def _check_extreme_weather(self, forecast: List[Dict]) -> List[str]:
        """Check for extreme weather conditions"""
        warnings = []
        
        for day in forecast:
            condition = str(day.get('condition', '')).lower()
            
            # Check for storms
            if 'storm' in condition or 'तूफान' in condition or 'thunderstorm' in condition:
                warnings.append('⚠️ Storm predicted - may damage crops')
            
            # Check for extreme heat
            temp_str = day.get('temperature', '25°C')
            if isinstance(temp_str, str):
                temp = float(temp_str.replace('°C', '').strip())
            else:
                temp = float(temp_str)
            
            if temp > 40:
                warnings.append('🌡️ Extreme heat predicted - ensure adequate irrigation')
            elif temp < 5:
                warnings.append('❄️ Frost risk - protect sensitive crops')
            
            # Check for heavy rain
            if 'heavy' in condition or 'भारी' in condition:
                warnings.append('🌧️ Heavy rainfall predicted - ensure drainage')
        
        return list(set(warnings))  # Remove duplicates
    
    def _generate_recommendations(self, forecast: List[Dict], crop_name: str,
                                  temp_analysis: Dict, rainfall_analysis: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Temperature-based recommendations
        if temp_analysis['status'] == 'too_cold':
            recommendations.append(f"🌡️ Temperature below optimal - consider delaying sowing")
        elif temp_analysis['status'] == 'too_hot':
            recommendations.append(f"🌡️ High temperatures expected - ensure irrigation")
        elif temp_analysis['status'] == 'optimal':
            recommendations.append(f"✅ Temperature conditions optimal for {crop_name}")
        
        # Rainfall-based recommendations
        if rainfall_analysis['status'] == 'needs_irrigation':
            recommendations.append(f"💧 Low rainfall predicted - arrange irrigation")
        elif rainfall_analysis['status'] == 'excess_rain_risk':
            recommendations.append(f"🌧️ Heavy rainfall expected - ensure proper drainage")
        elif rainfall_analysis['status'] in ['excellent', 'optimal']:
            recommendations.append(f"✅ Rainfall conditions favorable for {crop_name}")
        
        # Timing recommendations
        if temp_analysis['score'] >= 15 and rainfall_analysis['score'] >= 15:
            recommendations.append(f"🌱 Excellent time to sow {crop_name}")
        elif temp_analysis['score'] < 10 or rainfall_analysis['score'] < 10:
            recommendations.append(f"⏳ Consider waiting for better conditions")
        
        return recommendations
