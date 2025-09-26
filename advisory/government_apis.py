"""
Government API Integration Module
Integrates with official Indian government agricultural data sources
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class IMDWeatherAPI:
    """Integration with IMD (India Meteorological Department) Weather Data Portal"""
    
    def __init__(self):
        self.base_url = "https://mausam.imd.gov.in"
        self.api_key = None  # API key would be obtained from IMD portal
        
    def get_current_weather(self, latitude: float, longitude: float, language: str = 'en') -> Dict[str, Any]:
        """
        Get current weather data from IMD
        Note: This is a mock implementation. Real implementation would require IMD API access
        """
        try:
            # Mock data based on IMD format - in real implementation, this would be actual API call
            weather_data = {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": self._get_city_from_coordinates(latitude, longitude)
                },
                "current": {
                    "temperature": {
                        "current": 28.5,
                        "min": 22.0,
                        "max": 32.0,
                        "unit": "celsius"
                    },
                    "humidity": 65,
                    "wind_speed": 12.5,
                    "wind_direction": "NW",
                    "pressure": 1013.25,
                    "visibility": 10.0,
                    "uv_index": 6,
                    "condition": "Partly Cloudy",
                    "description": "Partly cloudy with moderate humidity"
                },
                "forecast": {
                    "today": {
                        "high": 32.0,
                        "low": 22.0,
                        "condition": "Partly Cloudy",
                        "rain_probability": 20
                    },
                    "tomorrow": {
                        "high": 30.0,
                        "low": 21.0,
                        "condition": "Light Rain",
                        "rain_probability": 60
                    }
                },
                "agricultural_advisory": {
                    "soil_moisture": "Moderate",
                    "irrigation_need": "Low",
                    "crop_condition": "Good",
                    "pest_risk": "Low"
                },
                "source": "IMD Weather Data Portal",
                "last_updated": datetime.now().isoformat()
            }
            
            if language == 'hi':
                weather_data = self._translate_weather_data(weather_data)
                
            return weather_data
            
        except Exception as e:
            logger.error(f"Error fetching IMD weather data: {e}")
            return {"error": "Unable to fetch weather data from IMD"}
    
    def _get_city_from_coordinates(self, lat: float, lon: float) -> str:
        """Get city name from coordinates - simplified implementation"""
        # In real implementation, this would use reverse geocoding
        return "Agricultural Region"
    
    def _translate_weather_data(self, data: Dict) -> Dict:
        """Translate weather data to Hindi"""
        translations = {
            "Partly Cloudy": "आंशिक रूप से बादल",
            "Light Rain": "हल्की बारिश",
            "Moderate": "मध्यम",
            "Low": "कम",
            "Good": "अच्छा"
        }
        
        # Apply translations
        if "current" in data and "condition" in data["current"]:
            data["current"]["condition"] = translations.get(data["current"]["condition"], data["current"]["condition"])
        
        return data

class AgmarknetAPI:
    """Integration with Agmarknet for Mandi Prices"""
    
    def __init__(self):
        self.base_url = "https://agmarknet.gov.in"
        
    def get_market_prices(self, commodity: str = None, state: str = None, 
                         district: str = None, language: str = 'en') -> Dict[str, Any]:
        """
        Get market prices from Agmarknet
        Note: This is a mock implementation. Real implementation would require Agmarknet API access
        """
        try:
            # Mock data based on Agmarknet format
            commodities_data = {
                "wheat": {
                    "price_per_quintal": 2200,
                    "price_unit": "INR",
                    "market": "Delhi Mandi",
                    "state": "Delhi",
                    "district": "New Delhi",
                    "arrival_quantity": 1500,
                    "arrival_unit": "quintals",
                    "price_trend": "stable",
                    "last_updated": datetime.now().isoformat()
                },
                "rice": {
                    "price_per_quintal": 3500,
                    "price_unit": "INR", 
                    "market": "Kolkata Mandi",
                    "state": "West Bengal",
                    "district": "Kolkata",
                    "arrival_quantity": 2000,
                    "arrival_unit": "quintals",
                    "price_trend": "increasing",
                    "last_updated": datetime.now().isoformat()
                },
                "maize": {
                    "price_per_quintal": 1800,
                    "price_unit": "INR",
                    "market": "Mumbai Mandi", 
                    "state": "Maharashtra",
                    "district": "Mumbai",
                    "arrival_quantity": 1200,
                    "arrival_unit": "quintals",
                    "price_trend": "stable",
                    "last_updated": datetime.now().isoformat()
                },
                "sugarcane": {
                    "price_per_quintal": 320,
                    "price_unit": "INR",
                    "market": "Pune Mandi",
                    "state": "Maharashtra", 
                    "district": "Pune",
                    "arrival_quantity": 5000,
                    "arrival_unit": "quintals",
                    "price_trend": "increasing",
                    "last_updated": datetime.now().isoformat()
                },
                "cotton": {
                    "price_per_quintal": 6500,
                    "price_unit": "INR",
                    "market": "Ahmedabad Mandi",
                    "state": "Gujarat",
                    "district": "Ahmedabad", 
                    "arrival_quantity": 800,
                    "arrival_unit": "quintals",
                    "price_trend": "stable",
                    "last_updated": datetime.now().isoformat()
                }
            }
            
            if commodity and commodity.lower() in commodities_data:
                result = commodities_data[commodity.lower()]
                result["source"] = "Agmarknet"
                if language == 'hi':
                    result = self._translate_price_data(result)
                return result
            else:
                # Return all commodities
                result = {
                    "commodities": commodities_data,
                    "source": "Agmarknet",
                    "last_updated": datetime.now().isoformat()
                }
                if language == 'hi':
                    result = self._translate_all_prices_data(result)
                return result
                
        except Exception as e:
            logger.error(f"Error fetching Agmarknet data: {e}")
            return {"error": "Unable to fetch market prices from Agmarknet"}
    
    def _translate_price_data(self, data: Dict) -> Dict:
        """Translate price data to Hindi"""
        translations = {
            "stable": "स्थिर",
            "increasing": "बढ़ रहा",
            "decreasing": "घट रहा"
        }
        
        if "price_trend" in data:
            data["price_trend"] = translations.get(data["price_trend"], data["price_trend"])
        
        return data
    
    def _translate_all_prices_data(self, data: Dict) -> Dict:
        """Translate all prices data to Hindi"""
        for commodity, price_data in data["commodities"].items():
            data["commodities"][commodity] = self._translate_price_data(price_data)
        return data

class ENAMAPIClient:
    """Integration with e-NAM (National Agricultural Market)"""
    
    def __init__(self):
        self.base_url = "https://enam.gov.in"
        
    def get_trending_crops(self, state: str = None, language: str = 'en') -> Dict[str, Any]:
        """
        Get trending crops data from e-NAM
        Note: This is a mock implementation. Real implementation would require e-NAM API access
        """
        try:
            # Mock data based on e-NAM format
            trending_data = {
                "state": state or "National",
                "trending_crops": [
                    {
                        "crop_name": "Tomato",
                        "price_trend": "increasing",
                        "demand_level": "high",
                        "average_price": 45,
                        "price_unit": "INR/kg",
                        "market_activity": "active",
                        "recommendation": "Good time to sell"
                    },
                    {
                        "crop_name": "Onion", 
                        "price_trend": "stable",
                        "demand_level": "medium",
                        "average_price": 35,
                        "price_unit": "INR/kg",
                        "market_activity": "moderate",
                        "recommendation": "Stable market conditions"
                    },
                    {
                        "crop_name": "Potato",
                        "price_trend": "increasing", 
                        "demand_level": "high",
                        "average_price": 25,
                        "price_unit": "INR/kg",
                        "market_activity": "very_active",
                        "recommendation": "High demand, consider planting"
                    },
                    {
                        "crop_name": "Maize",
                        "price_trend": "stable",
                        "demand_level": "medium", 
                        "average_price": 18,
                        "price_unit": "INR/kg",
                        "market_activity": "moderate",
                        "recommendation": "Steady market"
                    }
                ],
                "market_insights": {
                    "total_trading_volume": "2.5 lakh quintals",
                    "active_markets": 1250,
                    "price_volatility": "low",
                    "market_sentiment": "positive"
                },
                "source": "e-NAM",
                "last_updated": datetime.now().isoformat()
            }
            
            if language == 'hi':
                trending_data = self._translate_trending_data(trending_data)
                
            return trending_data
            
        except Exception as e:
            logger.error(f"Error fetching e-NAM data: {e}")
            return {"error": "Unable to fetch trending crops data from e-NAM"}
    
    def _translate_trending_data(self, data: Dict) -> Dict:
        """Translate trending data to Hindi"""
        translations = {
            "increasing": "बढ़ रहा",
            "stable": "स्थिर", 
            "decreasing": "घट रहा",
            "high": "उच्च",
            "medium": "मध्यम",
            "low": "कम",
            "active": "सक्रिय",
            "moderate": "मध्यम",
            "very_active": "बहुत सक्रिय",
            "Good time to sell": "बेचने का अच्छा समय",
            "Stable market conditions": "स्थिर बाजार स्थिति",
            "High demand, consider planting": "उच्च मांग, रोपण पर विचार करें",
            "Steady market": "स्थिर बाजार",
            "low": "कम",
            "positive": "सकारात्मक"
        }
        
        for crop in data["trending_crops"]:
            for key, value in crop.items():
                if isinstance(value, str) and value in translations:
                    crop[key] = translations[value]
        
        # Translate market insights
        if "market_insights" in data:
            for key, value in data["market_insights"].items():
                if isinstance(value, str) and value in translations:
                    data["market_insights"][key] = translations[value]
        
        return data

class ICARDataIntegration:
    """Integration with ICAR (Indian Council of Agricultural Research) data"""
    
    def __init__(self):
        self.base_url = "https://icar.org.in"
        
    def get_crop_recommendations(self, soil_type: str, climate_zone: str, 
                               season: str, language: str = 'en') -> Dict[str, Any]:
        """
        Get crop recommendations based on ICAR research data
        """
        try:
            # ICAR-based crop recommendations
            icar_recommendations = {
                "loamy": {
                    "kharif": ["Rice", "Maize", "Cotton", "Sugarcane", "Groundnut"],
                    "rabi": ["Wheat", "Barley", "Mustard", "Potato", "Onion"],
                    "zaid": ["Cucumber", "Watermelon", "Muskmelon", "Bitter Gourd"]
                },
                "clayey": {
                    "kharif": ["Rice", "Sugarcane", "Jute", "Cotton"],
                    "rabi": ["Wheat", "Barley", "Mustard", "Potato"],
                    "zaid": ["Rice", "Maize", "Vegetables"]
                },
                "sandy": {
                    "kharif": ["Groundnut", "Sunflower", "Maize", "Cotton"],
                    "rabi": ["Wheat", "Barley", "Mustard", "Potato"],
                    "zaid": ["Watermelon", "Muskmelon", "Cucumber"]
                },
                "silty": {
                    "kharif": ["Rice", "Maize", "Cotton", "Sugarcane"],
                    "rabi": ["Wheat", "Barley", "Mustard", "Potato"],
                    "zaid": ["Vegetables", "Rice", "Maize"]
                }
            }
            
            soil_crops = icar_recommendations.get(soil_type.lower(), icar_recommendations["loamy"])
            recommended_crops = soil_crops.get(season.lower(), soil_crops["kharif"])
            
            result = {
                "soil_type": soil_type,
                "season": season,
                "climate_zone": climate_zone,
                "recommended_crops": recommended_crops,
                "icar_insights": {
                    "yield_potential": "High" if soil_type.lower() == "loamy" else "Medium",
                    "water_requirement": "Moderate",
                    "fertilizer_needs": "Balanced NPK",
                    "pest_resistance": "Good"
                },
                "source": "ICAR Research Data",
                "last_updated": datetime.now().isoformat()
            }
            
            if language == 'hi':
                result = self._translate_icar_data(result)
                
            return result
            
        except Exception as e:
            logger.error(f"Error fetching ICAR data: {e}")
            return {"error": "Unable to fetch ICAR recommendations"}
    
    def _translate_icar_data(self, data: Dict) -> Dict:
        """Translate ICAR data to Hindi"""
        translations = {
            "High": "उच्च",
            "Medium": "मध्यम", 
            "Low": "कम",
            "Moderate": "मध्यम",
            "Balanced NPK": "संतुलित एनपीके",
            "Good": "अच्छा"
        }
        
        if "icar_insights" in data:
            for key, value in data["icar_insights"].items():
                if isinstance(value, str) and value in translations:
                    data["icar_insights"][key] = translations[value]
        
        return data

class NABARDInsights:
    """NABARD Report 2022 insights and statistics"""
    
    @staticmethod
    def get_farmer_statistics() -> Dict[str, Any]:
        """Get NABARD 2022 farmer statistics"""
        return {
            "small_marginal_farmers": {
                "percentage": 86,
                "description": "86% of Indian farmers are small/marginal",
                "implications": "Need for cost-effective, accessible agricultural solutions"
            },
            "ict_advisory_impact": {
                "yield_improvement": "20-30%",
                "source": "FAO & ICAR studies",
                "description": "ICT advisories improve yield by 20-30%"
            },
            "recommendations": [
                "Focus on small and marginal farmers",
                "Provide affordable technology solutions",
                "Ensure multilingual support",
                "Integrate traditional knowledge with modern technology"
            ]
        }
