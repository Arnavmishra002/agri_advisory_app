#!/usr/bin/env python3
"""
Consolidated Crop Service
Combines all crop-related functionality into a single, well-organized service
Replaces: ai_ml_crop_recommendation.py, comprehensive_crop_system.py, 
          pest_detection.py, fertilizer_recommendations.py
"""

import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, mean_squared_error
import joblib
import os

logger = logging.getLogger(__name__)


class ConsolidatedCropService:
    """
    Consolidated Crop Service that handles all crop-related functionality:
    - Crop recommendations using ML models
    - Pest and disease detection
    - Fertilizer recommendations
    - Yield predictions
    - Crop analysis and insights
    """
    
    def __init__(self):
        """Initialize the consolidated crop service"""
        self.models = {}
        self.encoders = {}
        self.scalers = {}
        self.crop_database = self._initialize_crop_database()
        self.pest_database = self._initialize_pest_database()
        self.fertilizer_database = self._initialize_fertilizer_database()
        
        # Load or initialize ML models
        self._initialize_ml_models()
    
    def _initialize_crop_database(self) -> Dict[str, Any]:
        """Initialize comprehensive crop database"""
        return {
            'cereals': {
                'wheat': {
                    'name': 'Wheat',
                    'hindi_name': 'गेहूं',
                    'season': 'rabi',
                    'duration_days': 120,
                    'temperature_range': (15, 25),
                    'rainfall_range': (400, 800),
                    'soil_types': ['loamy', 'clayey'],
                    'profitability_score': 85,
                    'market_demand': 'high',
                    'msp_price': 2015
                },
                'rice': {
                    'name': 'Rice',
                    'hindi_name': 'चावल',
                    'season': 'kharif',
                    'duration_days': 150,
                    'temperature_range': (20, 35),
                    'rainfall_range': (1000, 1500),
                    'soil_types': ['clayey', 'loamy'],
                    'profitability_score': 80,
                    'market_demand': 'high',
                    'msp_price': 1940
                },
                'maize': {
                    'name': 'Maize',
                    'hindi_name': 'मक्का',
                    'season': 'kharif',
                    'duration_days': 90,
                    'temperature_range': (18, 30),
                    'rainfall_range': (600, 1000),
                    'soil_types': ['loamy', 'sandy'],
                    'profitability_score': 75,
                    'market_demand': 'medium',
                    'msp_price': 1850
                }
            },
            'pulses': {
                'chickpea': {
                    'name': 'Chickpea',
                    'hindi_name': 'चना',
                    'season': 'rabi',
                    'duration_days': 100,
                    'temperature_range': (15, 25),
                    'rainfall_range': (400, 600),
                    'soil_types': ['loamy', 'sandy'],
                    'profitability_score': 90,
                    'market_demand': 'high',
                    'msp_price': 5440
                },
                'green_gram': {
                    'name': 'Green Gram',
                    'hindi_name': 'मूंग',
                    'season': 'kharif',
                    'duration_days': 70,
                    'temperature_range': (20, 30),
                    'rainfall_range': (500, 800),
                    'soil_types': ['loamy', 'sandy'],
                    'profitability_score': 85,
                    'market_demand': 'high',
                    'msp_price': 7275
                }
            },
            'vegetables': {
                'tomato': {
                    'name': 'Tomato',
                    'hindi_name': 'टमाटर',
                    'season': 'year_round',
                    'duration_days': 90,
                    'temperature_range': (20, 30),
                    'rainfall_range': (600, 800),
                    'soil_types': ['loamy', 'sandy'],
                    'profitability_score': 95,
                    'market_demand': 'very_high',
                    'msp_price': 0  # No MSP for vegetables
                },
                'onion': {
                    'name': 'Onion',
                    'hindi_name': 'प्याज',
                    'season': 'year_round',
                    'duration_days': 120,
                    'temperature_range': (15, 25),
                    'rainfall_range': (500, 700),
                    'soil_types': ['loamy', 'sandy'],
                    'profitability_score': 90,
                    'market_demand': 'very_high',
                    'msp_price': 0
                }
            }
        }
    
    def _initialize_pest_database(self) -> Dict[str, Any]:
        """Initialize pest and disease database"""
        return {
            'wheat': {
                'rust': {
                    'name': 'Rust',
                    'hindi_name': 'रस्ट',
                    'symptoms': ['Yellow-orange pustules', 'Reduced yield'],
                    'treatment': ['Fungicide spray', 'Resistant varieties'],
                    'prevention': ['Crop rotation', 'Proper spacing']
                },
                'aphids': {
                    'name': 'Aphids',
                    'hindi_name': 'एफिड्स',
                    'symptoms': ['Sticky leaves', 'Yellowing', 'Stunted growth'],
                    'treatment': ['Insecticide spray', 'Natural predators'],
                    'prevention': ['Healthy soil', 'Proper irrigation']
                }
            },
            'rice': {
                'blast': {
                    'name': 'Blast',
                    'hindi_name': 'ब्लास्ट',
                    'symptoms': ['Spindle-shaped lesions', 'Node rot'],
                    'treatment': ['Fungicide treatment', 'Resistant varieties'],
                    'prevention': ['Proper spacing', 'Water management']
                }
            }
        }
    
    def _initialize_fertilizer_database(self) -> Dict[str, Any]:
        """Initialize fertilizer recommendations database"""
        return {
            'npk_ratios': {
                'wheat': {'N': 120, 'P': 60, 'K': 40},
                'rice': {'N': 100, 'P': 50, 'K': 30},
                'maize': {'N': 150, 'P': 75, 'K': 50},
                'tomato': {'N': 80, 'P': 60, 'K': 100}
            },
            'organic_alternatives': {
                'compost': {'N': 2, 'P': 1, 'K': 2},
                'farmyard_manure': {'N': 0.5, 'P': 0.2, 'K': 0.5},
                'vermicompost': {'N': 1.5, 'P': 1, 'K': 1.5}
            }
        }
    
    def _initialize_ml_models(self):
        """Initialize or load ML models for crop recommendations"""
        try:
            # Try to load existing models
            models_dir = os.path.join(os.path.dirname(__file__), '../../models')
            
            if os.path.exists(os.path.join(models_dir, 'crop_recommendation_model.pkl')):
                self.models['crop_recommendation'] = joblib.load(
                    os.path.join(models_dir, 'crop_recommendation_model.pkl')
                )
            else:
                # Initialize new model
                self.models['crop_recommendation'] = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                )
            
            if os.path.exists(os.path.join(models_dir, 'yield_prediction_model.pkl')):
                self.models['yield_prediction'] = joblib.load(
                    os.path.join(models_dir, 'yield_prediction_model.pkl')
                )
            else:
                # Initialize new model
                self.models['yield_prediction'] = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=15,
                    random_state=42
                )
            
            # Initialize encoders and scalers
            self.encoders['crop_type'] = LabelEncoder()
            self.encoders['soil_type'] = LabelEncoder()
            self.scalers['yield_prediction'] = StandardScaler()
            
            logger.info("ML models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ML models: {e}")
            # Initialize basic models as fallback
            self.models['crop_recommendation'] = RandomForestClassifier(
                n_estimators=50, random_state=42
            )
            self.models['yield_prediction'] = RandomForestRegressor(
                n_estimators=50, random_state=42
            )
    
    def get_crop_recommendations(self, location: str, season: str = None, 
                               soil_type: str = None, preferences: Dict = None) -> Dict[str, Any]:
        """
        Get crop recommendations for a location
        
        Args:
            location: Location name
            season: Growing season (kharif, rabi, zaid)
            soil_type: Type of soil
            preferences: User preferences (profitability, market_demand, etc.)
            
        Returns:
            Dictionary containing crop recommendations
        """
        try:
            recommendations = []
            all_crops = []
            
            # Collect all crops from database
            for category, crops in self.crop_database.items():
                for crop_id, crop_data in crops.items():
                    crop_info = crop_data.copy()
                    crop_info['category'] = category
                    crop_info['crop_id'] = crop_id
                    all_crops.append(crop_info)
            
            # Filter by season if specified
            if season:
                all_crops = [
                    crop for crop in all_crops 
                    if crop['season'] == season or crop['season'] == 'year_round'
                ]
            
            # Filter by soil type if specified
            if soil_type:
                all_crops = [
                    crop for crop in all_crops 
                    if soil_type in crop['soil_types']
                ]
            
            # Score and rank crops
            for crop in all_crops:
                score = self._calculate_crop_score(crop, preferences)
                crop['recommendation_score'] = score
                recommendations.append(crop)
            
            # Sort by recommendation score
            recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
            
            # Return top 5 recommendations
            top_recommendations = recommendations[:5]
            
            return {
                'location': location,
                'season': season,
                'soil_type': soil_type,
                'total_crops_analyzed': len(recommendations),
                'recommendations': top_recommendations,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting crop recommendations: {e}")
            return {
                'error': 'Failed to get crop recommendations',
                'details': str(e),
                'location': location
            }
    
    def _calculate_crop_score(self, crop: Dict[str, Any], preferences: Dict = None) -> float:
        """Calculate recommendation score for a crop"""
        try:
            base_score = crop.get('profitability_score', 50)
            
            # Adjust based on market demand
            demand_multiplier = {
                'very_high': 1.2,
                'high': 1.1,
                'medium': 1.0,
                'low': 0.8
            }
            base_score *= demand_multiplier.get(crop.get('market_demand', 'medium'), 1.0)
            
            # Apply user preferences
            if preferences:
                if preferences.get('prioritize_profitability', False):
                    base_score *= 1.1
                
                if preferences.get('prioritize_market_demand', False):
                    base_score *= 1.05
                
                if preferences.get('organic_farming', False) and crop.get('organic_friendly', True):
                    base_score *= 1.05
            
            return round(base_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating crop score: {e}")
            return 50.0
    
    def predict_yield(self, crop_type: str, area_hectares: float, 
                     soil_data: Dict = None, weather_data: Dict = None) -> Dict[str, Any]:
        """
        Predict crop yield using ML models
        
        Args:
            crop_type: Type of crop
            area_hectares: Area in hectares
            soil_data: Soil characteristics
            weather_data: Weather conditions
            
        Returns:
            Yield prediction dictionary
        """
        try:
            # Prepare features for ML model
            features = self._prepare_yield_features(crop_type, area_hectares, soil_data, weather_data)
            
            # Make prediction using trained model
            if self.models.get('yield_prediction') and hasattr(self.models['yield_prediction'], 'predict'):
                try:
                    yield_per_hectare = self.models['yield_prediction'].predict([features])[0]
                    total_yield = yield_per_hectare * area_hectares
                except AttributeError as e:
                    logger.warning(f"Model prediction failed: {e}. Using fallback prediction.")
                    # Fallback to rule-based prediction
                    yield_per_hectare = self._get_fallback_yield(crop_type)
                    total_yield = yield_per_hectare * area_hectares
                
                return {
                    'crop_type': crop_type,
                    'area_hectares': area_hectares,
                    'yield_per_hectare_kg': round(yield_per_hectare, 2),
                    'total_yield_kg': round(total_yield, 2),
                    'confidence': 0.85,  # Placeholder confidence score
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Fallback to rule-based prediction
                return self._rule_based_yield_prediction(crop_type, area_hectares, soil_data, weather_data)
                
        except Exception as e:
            logger.error(f"Error predicting yield: {e}")
            return {
                'error': 'Failed to predict yield',
                'details': str(e),
                'crop_type': crop_type
            }
    
    def _get_fallback_yield(self, crop_type: str) -> float:
        """
        Get fallback yield prediction based on crop type
        """
        fallback_yields = {
            'wheat': 4500,  # kg per hectare
            'rice': 4000,
            'maize': 7000,
            'sugarcane': 80000,
            'cotton': 500,
            'tomato': 25000,
            'potato': 20000,
            'onion': 15000,
            'chickpea': 1200,
            'mustard': 1200
        }
        return fallback_yields.get(crop_type.lower(), 3000)
    
    def _prepare_yield_features(self, crop_type: str, area: float, 
                              soil_data: Dict, weather_data: Dict) -> List[float]:
        """Prepare features for yield prediction model"""
        # Default feature values
        features = [
            area,  # Area in hectares
            soil_data.get('ph', 6.5) if soil_data else 6.5,
            soil_data.get('organic_matter', 2.0) if soil_data else 2.0,
            soil_data.get('nitrogen', 100) if soil_data else 100,
            soil_data.get('phosphorus', 50) if soil_data else 50,
            soil_data.get('potassium', 100) if soil_data else 100,
            weather_data.get('temperature', 25.0) if weather_data else 25.0,
            weather_data.get('rainfall', 800) if weather_data else 800,
            weather_data.get('humidity', 60) if weather_data else 60
        ]
        
        return features
    
    def _rule_based_yield_prediction(self, crop_type: str, area: float, 
                                   soil_data: Dict, weather_data: Dict) -> Dict[str, Any]:
        """Fallback rule-based yield prediction"""
        # Base yield per hectare for different crops (in kg)
        base_yields = {
            'wheat': 3000,
            'rice': 4000,
            'maize': 3500,
            'tomato': 25000,
            'onion': 15000,
            'chickpea': 1500
        }
        
        base_yield = base_yields.get(crop_type.lower(), 2000)
        
        # Adjust based on soil quality
        soil_multiplier = 1.0
        if soil_data:
            ph = soil_data.get('ph', 6.5)
            if 6.0 <= ph <= 7.5:
                soil_multiplier = 1.1
            elif 5.5 <= ph < 6.0 or 7.5 < ph <= 8.0:
                soil_multiplier = 0.9
            else:
                soil_multiplier = 0.7
        
        # Adjust based on weather
        weather_multiplier = 1.0
        if weather_data:
            temp = weather_data.get('temperature', 25)
            rainfall = weather_data.get('rainfall', 800)
            
            # Temperature adjustment
            if 20 <= temp <= 30:
                weather_multiplier *= 1.1
            elif 15 <= temp < 20 or 30 < temp <= 35:
                weather_multiplier *= 0.9
            else:
                weather_multiplier *= 0.7
            
            # Rainfall adjustment
            if 600 <= rainfall <= 1200:
                weather_multiplier *= 1.1
            elif 400 <= rainfall < 600 or 1200 < rainfall <= 1500:
                weather_multiplier *= 0.9
            else:
                weather_multiplier *= 0.7
        
        yield_per_hectare = base_yield * soil_multiplier * weather_multiplier
        total_yield = yield_per_hectare * area
        
        return {
            'crop_type': crop_type,
            'area_hectares': area,
            'yield_per_hectare_kg': round(yield_per_hectare, 2),
            'total_yield_kg': round(total_yield, 2),
            'confidence': 0.70,  # Lower confidence for rule-based prediction
            'prediction_method': 'rule_based',
            'timestamp': datetime.now().isoformat()
        }
    
    def detect_pest_disease(self, crop_type: str, symptoms: List[str], 
                          image_data: str = None) -> Dict[str, Any]:
        """
        Detect pest or disease based on symptoms or image
        
        Args:
            crop_type: Type of crop
            symptoms: List of observed symptoms
            image_data: Base64 encoded image data (optional)
            
        Returns:
            Pest/disease detection results
        """
        try:
            crop_pests = self.pest_database.get(crop_type.lower(), {})
            matches = []
            
            # Simple symptom-based matching
            for pest_id, pest_info in crop_pests.items():
                pest_symptoms = pest_info.get('symptoms', [])
                symptom_matches = 0
                
                for symptom in symptoms:
                    for pest_symptom in pest_symptoms:
                        if symptom.lower() in pest_symptom.lower() or pest_symptom.lower() in symptom.lower():
                            symptom_matches += 1
                
                if symptom_matches > 0:
                    match_score = symptom_matches / len(pest_symptoms)
                    matches.append({
                        'pest_id': pest_id,
                        'name': pest_info['name'],
                        'hindi_name': pest_info['hindi_name'],
                        'match_score': match_score,
                        'symptoms': pest_symptoms,
                        'treatment': pest_info.get('treatment', []),
                        'prevention': pest_info.get('prevention', [])
                    })
            
            # Sort by match score
            matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            return {
                'crop_type': crop_type,
                'symptoms_provided': symptoms,
                'matches_found': len(matches),
                'top_matches': matches[:3],  # Top 3 matches
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error detecting pest/disease: {e}")
            return {
                'error': 'Failed to detect pest/disease',
                'details': str(e),
                'crop_type': crop_type
            }
    
    def get_fertilizer_recommendations(self, crop_type: str, soil_data: Dict, 
                                     area_hectares: float, organic_preference: bool = False) -> Dict[str, Any]:
        """
        Get fertilizer recommendations for a crop
        
        Args:
            crop_type: Type of crop
            soil_data: Soil characteristics
            area_hectares: Area in hectares
            organic_preference: Whether to recommend organic fertilizers
            
        Returns:
            Fertilizer recommendations
        """
        try:
            crop_npk = self.fertilizer_database['npk_ratios'].get(crop_type.lower())
            
            if not crop_npk:
                return {
                    'error': f'No fertilizer data available for {crop_type}',
                    'crop_type': crop_type
                }
            
            # Calculate required nutrients
            required_n = crop_npk['N'] * area_hectares
            required_p = crop_npk['P'] * area_hectares
            required_k = crop_npk['K'] * area_hectares
            
            # Adjust based on soil content
            if soil_data:
                soil_n = soil_data.get('nitrogen', 0)
                soil_p = soil_data.get('phosphorus', 0)
                soil_k = soil_data.get('potassium', 0)
                
                required_n = max(0, required_n - soil_n)
                required_p = max(0, required_p - soil_p)
                required_k = max(0, required_k - soil_k)
            
            recommendations = []
            
            if organic_preference:
                # Organic fertilizer recommendations
                organic_data = self.fertilizer_database['organic_alternatives']
                
                for organic_type, npk_content in organic_data.items():
                    amount_needed = max(
                        required_n / npk_content['N'] if npk_content['N'] > 0 else 0,
                        required_p / npk_content['P'] if npk_content['P'] > 0 else 0,
                        required_k / npk_content['K'] if npk_content['K'] > 0 else 0
                    )
                    
                    if amount_needed > 0:
                        recommendations.append({
                            'type': organic_type,
                            'amount_kg': round(amount_needed, 2),
                            'npk_content': npk_content,
                            'application_method': 'Mix with soil before planting'
                        })
            else:
                # Chemical fertilizer recommendations
                if required_n > 0:
                    recommendations.append({
                        'type': 'Urea (46-0-0)',
                        'amount_kg': round(required_n / 0.46, 2),
                        'application_method': 'Split application - 1/3 at sowing, 2/3 at tillering'
                    })
                
                if required_p > 0:
                    recommendations.append({
                        'type': 'DAP (18-46-0)',
                        'amount_kg': round(required_p / 0.46, 2),
                        'application_method': 'Apply at sowing time'
                    })
                
                if required_k > 0:
                    recommendations.append({
                        'type': 'MOP (0-0-60)',
                        'amount_kg': round(required_k / 0.60, 2),
                        'application_method': 'Apply at sowing or before flowering'
                    })
            
            return {
                'crop_type': crop_type,
                'area_hectares': area_hectares,
                'soil_analysis': soil_data,
                'required_nutrients': {
                    'nitrogen_kg': round(required_n, 2),
                    'phosphorus_kg': round(required_p, 2),
                    'potassium_kg': round(required_k, 2)
                },
                'recommendations': recommendations,
                'organic_preference': organic_preference,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting fertilizer recommendations: {e}")
            return {
                'error': 'Failed to get fertilizer recommendations',
                'details': str(e),
                'crop_type': crop_type
            }
    
    def get_crop_analysis(self, crop_type: str, location: str = None) -> Dict[str, Any]:
        """
        Get comprehensive crop analysis
        
        Args:
            crop_type: Type of crop
            location: Location for analysis
            
        Returns:
            Comprehensive crop analysis
        """
        try:
            # Find crop in database
            crop_data = None
            crop_category = None
            
            for category, crops in self.crop_database.items():
                if crop_type.lower() in crops:
                    crop_data = crops[crop_type.lower()]
                    crop_category = category
                    break
            
            if not crop_data:
                return {
                    'error': f'Crop {crop_type} not found in database',
                    'crop_type': crop_type
                }
            
            # Get related pests and diseases
            pests_diseases = self.pest_database.get(crop_type.lower(), {})
            
            # Get fertilizer requirements
            fertilizer_req = self.fertilizer_database['npk_ratios'].get(crop_type.lower(), {})
            
            # Calculate profitability insights
            profitability_insights = self._calculate_profitability_insights(crop_data)
            
            return {
                'crop_info': {
                    'name': crop_data['name'],
                    'hindi_name': crop_data['hindi_name'],
                    'category': crop_category,
                    'season': crop_data['season'],
                    'duration_days': crop_data['duration_days'],
                    'profitability_score': crop_data['profitability_score'],
                    'market_demand': crop_data['market_demand']
                },
                'growing_conditions': {
                    'temperature_range': crop_data['temperature_range'],
                    'rainfall_range': crop_data['rainfall_range'],
                    'soil_types': crop_data['soil_types']
                },
                'pests_diseases': {
                    'count': len(pests_diseases),
                    'common_issues': list(pests_diseases.keys())
                },
                'fertilizer_requirements': fertilizer_req,
                'profitability_insights': profitability_insights,
                'market_info': {
                    'msp_price': crop_data.get('msp_price', 0),
                    'market_demand': crop_data['market_demand']
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting crop analysis: {e}")
            return {
                'error': 'Failed to get crop analysis',
                'details': str(e),
                'crop_type': crop_type
            }
    
    def _calculate_profitability_insights(self, crop_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate profitability insights for a crop"""
        try:
            base_score = crop_data.get('profitability_score', 50)
            
            insights = {
                'profitability_rating': 'high' if base_score >= 80 else 'medium' if base_score >= 60 else 'low',
                'market_potential': crop_data.get('market_demand', 'medium'),
                'investment_risk': 'low' if base_score >= 80 else 'medium' if base_score >= 60 else 'high',
                'recommended_for': []
            }
            
            # Add recommendations based on score
            if base_score >= 85:
                insights['recommended_for'].extend(['commercial_farming', 'export', 'high_value_markets'])
            elif base_score >= 70:
                insights['recommended_for'].extend(['commercial_farming', 'local_markets'])
            else:
                insights['recommended_for'].append('subsistence_farming')
            
            return insights
            
        except Exception as e:
            logger.error(f"Error calculating profitability insights: {e}")
            return {'error': 'Failed to calculate insights'}


# Convenience functions for backward compatibility
def get_crop_recommendations(location: str, season: str = None, soil_type: str = None) -> Dict[str, Any]:
    """Convenience function to get crop recommendations"""
    crop_service = ConsolidatedCropService()
    return crop_service.get_crop_recommendations(location, season, soil_type)

def predict_yield(crop_type: str, area_hectares: float, soil_data: Dict = None) -> Dict[str, Any]:
    """Convenience function to predict yield"""
    crop_service = ConsolidatedCropService()
    return crop_service.predict_yield(crop_type, area_hectares, soil_data)

def detect_pest_disease(crop_type: str, symptoms: List[str]) -> Dict[str, Any]:
    """Convenience function to detect pests/diseases"""
    crop_service = ConsolidatedCropService()
    return crop_service.detect_pest_disease(crop_type, symptoms)
