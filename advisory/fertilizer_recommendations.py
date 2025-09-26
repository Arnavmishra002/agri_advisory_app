"""
Comprehensive Fertilizer Recommendation System
Based on crop type, soil type, and government agricultural data
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FertilizerRecommendationEngine:
    """Advanced fertilizer recommendation system based on crop and soil analysis"""
    
    def __init__(self):
        self.crop_fertilizer_database = self._initialize_crop_fertilizer_database()
        self.soil_fertilizer_requirements = self._initialize_soil_requirements()
        self.seasonal_adjustments = self._initialize_seasonal_adjustments()
    
    def _initialize_crop_fertilizer_database(self) -> Dict[str, Dict]:
        """Initialize comprehensive crop-fertilizer database based on ICAR and government data"""
        return {
            "wheat": {
                "primary_nutrients": {
                    "nitrogen": {"amount": 120, "unit": "kg/hectare", "timing": "Split application"},
                    "phosphorus": {"amount": 60, "unit": "kg/hectare", "timing": "Basal application"},
                    "potassium": {"amount": 40, "unit": "kg/hectare", "timing": "Basal application"}
                },
                "secondary_nutrients": {
                    "sulfur": {"amount": 20, "unit": "kg/hectare"},
                    "magnesium": {"amount": 15, "unit": "kg/hectare"},
                    "calcium": {"amount": 10, "unit": "kg/hectare"}
                },
                "micronutrients": {
                    "zinc": {"amount": 5, "unit": "kg/hectare"},
                    "iron": {"amount": 2, "unit": "kg/hectare"},
                    "manganese": {"amount": 1, "unit": "kg/hectare"}
                },
                "organic_fertilizers": {
                    "farmyard_manure": {"amount": 10, "unit": "tonnes/hectare"},
                    "vermicompost": {"amount": 5, "unit": "tonnes/hectare"},
                    "green_manure": {"amount": 2, "unit": "tonnes/hectare"}
                },
                "recommended_fertilizers": [
                    "Urea (46% N)",
                    "DAP (18% N, 46% P2O5)",
                    "MOP (60% K2O)",
                    "Zinc Sulfate",
                    "Farmyard Manure"
                ],
                "application_schedule": {
                    "basal": ["DAP", "MOP", "Zinc Sulfate", "Farmyard Manure"],
                    "top_dressing_1": ["Urea (1/3)"],
                    "top_dressing_2": ["Urea (1/3)"],
                    "top_dressing_3": ["Urea (1/3)"]
                }
            },
            "rice": {
                "primary_nutrients": {
                    "nitrogen": {"amount": 100, "unit": "kg/hectare", "timing": "Split application"},
                    "phosphorus": {"amount": 50, "unit": "kg/hectare", "timing": "Basal application"},
                    "potassium": {"amount": 50, "unit": "kg/hectare", "timing": "Basal application"}
                },
                "secondary_nutrients": {
                    "sulfur": {"amount": 15, "unit": "kg/hectare"},
                    "magnesium": {"amount": 10, "unit": "kg/hectare"},
                    "calcium": {"amount": 8, "unit": "kg/hectare"}
                },
                "micronutrients": {
                    "zinc": {"amount": 5, "unit": "kg/hectare"},
                    "iron": {"amount": 3, "unit": "kg/hectare"},
                    "manganese": {"amount": 1, "unit": "kg/hectare"}
                },
                "organic_fertilizers": {
                    "farmyard_manure": {"amount": 12, "unit": "tonnes/hectare"},
                    "vermicompost": {"amount": 6, "unit": "tonnes/hectare"},
                    "green_manure": {"amount": 3, "unit": "tonnes/hectare"}
                },
                "recommended_fertilizers": [
                    "Urea (46% N)",
                    "DAP (18% N, 46% P2O5)",
                    "MOP (60% K2O)",
                    "Zinc Sulfate",
                    "Farmyard Manure"
                ],
                "application_schedule": {
                    "basal": ["DAP", "MOP", "Zinc Sulfate", "Farmyard Manure"],
                    "top_dressing_1": ["Urea (1/3)"],
                    "top_dressing_2": ["Urea (1/3)"],
                    "top_dressing_3": ["Urea (1/3)"]
                }
            },
            "maize": {
                "primary_nutrients": {
                    "nitrogen": {"amount": 150, "unit": "kg/hectare", "timing": "Split application"},
                    "phosphorus": {"amount": 80, "unit": "kg/hectare", "timing": "Basal application"},
                    "potassium": {"amount": 60, "unit": "kg/hectare", "timing": "Basal application"}
                },
                "secondary_nutrients": {
                    "sulfur": {"amount": 25, "unit": "kg/hectare"},
                    "magnesium": {"amount": 20, "unit": "kg/hectare"},
                    "calcium": {"amount": 15, "unit": "kg/hectare"}
                },
                "micronutrients": {
                    "zinc": {"amount": 8, "unit": "kg/hectare"},
                    "iron": {"amount": 3, "unit": "kg/hectare"},
                    "manganese": {"amount": 2, "unit": "kg/hectare"}
                },
                "organic_fertilizers": {
                    "farmyard_manure": {"amount": 15, "unit": "tonnes/hectare"},
                    "vermicompost": {"amount": 8, "unit": "tonnes/hectare"},
                    "green_manure": {"amount": 4, "unit": "tonnes/hectare"}
                },
                "recommended_fertilizers": [
                    "Urea (46% N)",
                    "DAP (18% N, 46% P2O5)",
                    "MOP (60% K2O)",
                    "Zinc Sulfate",
                    "Farmyard Manure"
                ],
                "application_schedule": {
                    "basal": ["DAP", "MOP", "Zinc Sulfate", "Farmyard Manure"],
                    "top_dressing_1": ["Urea (1/3)"],
                    "top_dressing_2": ["Urea (1/3)"],
                    "top_dressing_3": ["Urea (1/3)"]
                }
            },
            "sugarcane": {
                "primary_nutrients": {
                    "nitrogen": {"amount": 200, "unit": "kg/hectare", "timing": "Split application"},
                    "phosphorus": {"amount": 100, "unit": "kg/hectare", "timing": "Basal application"},
                    "potassium": {"amount": 120, "unit": "kg/hectare", "timing": "Basal application"}
                },
                "secondary_nutrients": {
                    "sulfur": {"amount": 30, "unit": "kg/hectare"},
                    "magnesium": {"amount": 25, "unit": "kg/hectare"},
                    "calcium": {"amount": 20, "unit": "kg/hectare"}
                },
                "micronutrients": {
                    "zinc": {"amount": 10, "unit": "kg/hectare"},
                    "iron": {"amount": 5, "unit": "kg/hectare"},
                    "manganese": {"amount": 3, "unit": "kg/hectare"}
                },
                "organic_fertilizers": {
                    "farmyard_manure": {"amount": 20, "unit": "tonnes/hectare"},
                    "vermicompost": {"amount": 10, "unit": "tonnes/hectare"},
                    "green_manure": {"amount": 5, "unit": "tonnes/hectare"}
                },
                "recommended_fertilizers": [
                    "Urea (46% N)",
                    "DAP (18% N, 46% P2O5)",
                    "MOP (60% K2O)",
                    "Zinc Sulfate",
                    "Farmyard Manure"
                ],
                "application_schedule": {
                    "basal": ["DAP", "MOP", "Zinc Sulfate", "Farmyard Manure"],
                    "top_dressing_1": ["Urea (1/3)"],
                    "top_dressing_2": ["Urea (1/3)"],
                    "top_dressing_3": ["Urea (1/3)"]
                }
            },
            "cotton": {
                "primary_nutrients": {
                    "nitrogen": {"amount": 80, "unit": "kg/hectare", "timing": "Split application"},
                    "phosphorus": {"amount": 40, "unit": "kg/hectare", "timing": "Basal application"},
                    "potassium": {"amount": 40, "unit": "kg/hectare", "timing": "Basal application"}
                },
                "secondary_nutrients": {
                    "sulfur": {"amount": 15, "unit": "kg/hectare"},
                    "magnesium": {"amount": 12, "unit": "kg/hectare"},
                    "calcium": {"amount": 10, "unit": "kg/hectare"}
                },
                "micronutrients": {
                    "zinc": {"amount": 5, "unit": "kg/hectare"},
                    "iron": {"amount": 2, "unit": "kg/hectare"},
                    "manganese": {"amount": 1, "unit": "kg/hectare"}
                },
                "organic_fertilizers": {
                    "farmyard_manure": {"amount": 8, "unit": "tonnes/hectare"},
                    "vermicompost": {"amount": 4, "unit": "tonnes/hectare"},
                    "green_manure": {"amount": 2, "unit": "tonnes/hectare"}
                },
                "recommended_fertilizers": [
                    "Urea (46% N)",
                    "DAP (18% N, 46% P2O5)",
                    "MOP (60% K2O)",
                    "Zinc Sulfate",
                    "Farmyard Manure"
                ],
                "application_schedule": {
                    "basal": ["DAP", "MOP", "Zinc Sulfate", "Farmyard Manure"],
                    "top_dressing_1": ["Urea (1/2)"],
                    "top_dressing_2": ["Urea (1/2)"]
                }
            },
            "tomato": {
                "primary_nutrients": {
                    "nitrogen": {"amount": 100, "unit": "kg/hectare", "timing": "Split application"},
                    "phosphorus": {"amount": 60, "unit": "kg/hectare", "timing": "Basal application"},
                    "potassium": {"amount": 80, "unit": "kg/hectare", "timing": "Basal application"}
                },
                "secondary_nutrients": {
                    "sulfur": {"amount": 20, "unit": "kg/hectare"},
                    "magnesium": {"amount": 15, "unit": "kg/hectare"},
                    "calcium": {"amount": 12, "unit": "kg/hectare"}
                },
                "micronutrients": {
                    "zinc": {"amount": 5, "unit": "kg/hectare"},
                    "iron": {"amount": 3, "unit": "kg/hectare"},
                    "manganese": {"amount": 2, "unit": "kg/hectare"}
                },
                "organic_fertilizers": {
                    "farmyard_manure": {"amount": 12, "unit": "tonnes/hectare"},
                    "vermicompost": {"amount": 6, "unit": "tonnes/hectare"},
                    "green_manure": {"amount": 3, "unit": "tonnes/hectare"}
                },
                "recommended_fertilizers": [
                    "Urea (46% N)",
                    "DAP (18% N, 46% P2O5)",
                    "MOP (60% K2O)",
                    "Zinc Sulfate",
                    "Farmyard Manure"
                ],
                "application_schedule": {
                    "basal": ["DAP", "MOP", "Zinc Sulfate", "Farmyard Manure"],
                    "top_dressing_1": ["Urea (1/3)"],
                    "top_dressing_2": ["Urea (1/3)"],
                    "top_dressing_3": ["Urea (1/3)"]
                }
            }
        }
    
    def _initialize_soil_requirements(self) -> Dict[str, Dict]:
        """Initialize soil-specific fertilizer requirements"""
        return {
            "loamy": {
                "ph_range": "6.0-7.5",
                "organic_matter": "2-3%",
                "nutrient_retention": "High",
                "fertilizer_efficiency": "High",
                "adjustments": {
                    "nitrogen": 1.0,  # No adjustment needed
                    "phosphorus": 1.0,
                    "potassium": 1.0
                }
            },
            "clayey": {
                "ph_range": "6.5-8.0",
                "organic_matter": "1-2%",
                "nutrient_retention": "Very High",
                "fertilizer_efficiency": "Medium",
                "adjustments": {
                    "nitrogen": 1.2,  # Increase due to slower release
                    "phosphorus": 0.8,  # Decrease due to high retention
                    "potassium": 1.1
                }
            },
            "sandy": {
                "ph_range": "5.5-7.0",
                "organic_matter": "0.5-1%",
                "nutrient_retention": "Low",
                "fertilizer_efficiency": "Low",
                "adjustments": {
                    "nitrogen": 1.5,  # Increase due to leaching
                    "phosphorus": 1.3,  # Increase due to low retention
                    "potassium": 1.4
                }
            },
            "silty": {
                "ph_range": "6.0-7.5",
                "organic_matter": "1.5-2.5%",
                "nutrient_retention": "Medium",
                "fertilizer_efficiency": "High",
                "adjustments": {
                    "nitrogen": 1.1,
                    "phosphorus": 1.0,
                    "potassium": 1.1
                }
            }
        }
    
    def _initialize_seasonal_adjustments(self) -> Dict[str, Dict]:
        """Initialize seasonal adjustments for fertilizer recommendations"""
        return {
            "kharif": {
                "nitrogen": 1.1,  # Slightly higher due to monsoon leaching
                "phosphorus": 1.0,
                "potassium": 1.0,
                "organic_matter": 1.2  # Higher organic matter requirement
            },
            "rabi": {
                "nitrogen": 1.0,
                "phosphorus": 1.1,  # Higher P requirement for root development
                "potassium": 1.0,
                "organic_matter": 1.0
            },
            "zaid": {
                "nitrogen": 1.2,  # Higher N for quick growth
                "phosphorus": 1.0,
                "potassium": 1.1,
                "organic_matter": 1.1
            }
        }
    
    def get_fertilizer_recommendation(self, crop_type: str, soil_type: str, 
                                    season: str = "kharif", area_hectares: float = 1.0,
                                    language: str = 'en') -> Dict[str, Any]:
        """
        Get comprehensive fertilizer recommendation based on crop, soil, and season
        """
        try:
            # Get base crop requirements
            crop_data = self.crop_fertilizer_database.get(crop_type.lower())
            if not crop_data:
                return {"error": f"No fertilizer data available for {crop_type}"}
            
            # Get soil adjustments
            soil_data = self.soil_fertilizer_requirements.get(soil_type.lower())
            if not soil_data:
                soil_data = self.soil_fertilizer_requirements["loamy"]  # Default
            
            # Get seasonal adjustments
            seasonal_data = self.seasonal_adjustments.get(season.lower())
            if not seasonal_data:
                seasonal_data = self.seasonal_adjustments["kharif"]  # Default
            
            # Calculate adjusted nutrient requirements
            adjusted_nutrients = self._calculate_adjusted_nutrients(
                crop_data, soil_data, seasonal_data, area_hectares
            )
            
            # Generate recommendation
            recommendation = {
                "crop": crop_type,
                "soil_type": soil_type,
                "season": season,
                "area": f"{area_hectares} hectares",
                "nutrient_requirements": adjusted_nutrients,
                "recommended_fertilizers": crop_data["recommended_fertilizers"],
                "application_schedule": crop_data["application_schedule"],
                "soil_characteristics": {
                    "ph_range": soil_data["ph_range"],
                    "organic_matter": soil_data["organic_matter"],
                    "nutrient_retention": soil_data["nutrient_retention"],
                    "fertilizer_efficiency": soil_data["fertilizer_efficiency"]
                },
                "seasonal_considerations": {
                    "season": season,
                    "adjustments_applied": seasonal_data
                },
                "cost_estimation": self._calculate_fertilizer_cost(adjusted_nutrients),
                "organic_alternatives": crop_data["organic_fertilizers"],
                "best_practices": self._get_best_practices(crop_type, soil_type, season),
                "source": "ICAR & Government Agricultural Data",
                "last_updated": datetime.now().isoformat()
            }
            
            if language == 'hi':
                recommendation = self._translate_fertilizer_recommendation(recommendation)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating fertilizer recommendation: {e}")
            return {"error": "Unable to generate fertilizer recommendation"}
    
    def _calculate_adjusted_nutrients(self, crop_data: Dict, soil_data: Dict, 
                                    seasonal_data: Dict, area_hectares: float) -> Dict:
        """Calculate adjusted nutrient requirements based on soil and season"""
        adjusted = {}
        
        for nutrient, data in crop_data["primary_nutrients"].items():
            base_amount = data["amount"]
            soil_adjustment = soil_data["adjustments"].get(nutrient, 1.0)
            seasonal_adjustment = seasonal_data.get(nutrient, 1.0)
            
            adjusted_amount = base_amount * soil_adjustment * seasonal_adjustment * area_hectares
            
            adjusted[nutrient] = {
                "base_amount": base_amount,
                "adjusted_amount": round(adjusted_amount, 2),
                "unit": data["unit"],
                "timing": data["timing"],
                "soil_adjustment": soil_adjustment,
                "seasonal_adjustment": seasonal_adjustment
            }
        
        return adjusted
    
    def _calculate_fertilizer_cost(self, nutrients: Dict) -> Dict:
        """Calculate estimated fertilizer cost"""
        # Approximate prices per kg (these would be updated with real market prices)
        fertilizer_prices = {
            "nitrogen": 25,  # INR per kg
            "phosphorus": 30,
            "potassium": 35
        }
        
        total_cost = 0
        cost_breakdown = {}
        
        for nutrient, data in nutrients.items():
            if nutrient in fertilizer_prices:
                cost = data["adjusted_amount"] * fertilizer_prices[nutrient]
                cost_breakdown[nutrient] = {
                    "amount": data["adjusted_amount"],
                    "rate": fertilizer_prices[nutrient],
                    "cost": round(cost, 2)
                }
                total_cost += cost
        
        return {
            "total_cost": round(total_cost, 2),
            "cost_breakdown": cost_breakdown,
            "currency": "INR",
            "note": "Prices are approximate and may vary by location"
        }
    
    def _get_best_practices(self, crop_type: str, soil_type: str, season: str) -> List[str]:
        """Get best practices for fertilizer application"""
        practices = [
            "Apply fertilizers in split doses for better efficiency",
            "Incorporate organic matter to improve soil structure",
            "Test soil pH and adjust if necessary",
            "Use balanced NPK ratio as recommended",
            "Apply fertilizers at the right time and depth",
            "Avoid over-fertilization to prevent environmental damage",
            "Use slow-release fertilizers for better nutrient availability",
            "Monitor crop response and adjust accordingly"
        ]
        
        # Add crop-specific practices
        if crop_type.lower() == "rice":
            practices.append("Apply nitrogen in split doses to prevent leaching")
            practices.append("Use deep placement of phosphorus for better efficiency")
        elif crop_type.lower() == "wheat":
            practices.append("Apply phosphorus at sowing for better root development")
            practices.append("Use top-dressing for nitrogen during tillering stage")
        elif crop_type.lower() == "maize":
            practices.append("Apply nitrogen in split doses during growth stages")
            practices.append("Use side-dressing for better nutrient uptake")
        
        # Add soil-specific practices
        if soil_type.lower() == "sandy":
            practices.append("Use frequent light applications to prevent leaching")
            practices.append("Increase organic matter content")
        elif soil_type.lower() == "clayey":
            practices.append("Apply fertilizers well in advance of planting")
            practices.append("Use deep placement to avoid surface fixation")
        
        return practices
    
    def _translate_fertilizer_recommendation(self, data: Dict) -> Dict:
        """Translate fertilizer recommendation to Hindi"""
        translations = {
            "hectares": "हेक्टेयर",
            "kg/hectare": "किलोग्राम/हेक्टेयर",
            "tonnes/hectare": "टन/हेक्टेयर",
            "Split application": "विभाजित अनुप्रयोग",
            "Basal application": "आधार अनुप्रयोग",
            "High": "उच्च",
            "Medium": "मध्यम",
            "Low": "कम",
            "Very High": "बहुत उच्च",
            "kharif": "खरीफ",
            "rabi": "रबी",
            "zaid": "जायद",
            "INR": "रुपये"
        }
        
        # Translate specific fields
        if "area" in data:
            for key, value in translations.items():
                if key in data["area"]:
                    data["area"] = data["area"].replace(key, value)
        
        if "soil_characteristics" in data:
            for key, value in data["soil_characteristics"].items():
                if isinstance(value, str) and value in translations:
                    data["soil_characteristics"][key] = translations[value]
        
        if "seasonal_considerations" in data and "season" in data["seasonal_considerations"]:
            season = data["seasonal_considerations"]["season"]
            if season in translations:
                data["seasonal_considerations"]["season"] = translations[season]
        
        if "cost_estimation" in data and "currency" in data["cost_estimation"]:
            if data["cost_estimation"]["currency"] in translations:
                data["cost_estimation"]["currency"] = translations[data["cost_estimation"]["currency"]]
        
        return data
