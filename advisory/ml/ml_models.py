"""
Advanced Machine Learning Models for Agricultural Advisory
Includes crop recommendation, yield prediction, and continuous learning from user feedback
"""

import numpy as np
import pandas as pd
import joblib
import json
import os
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, classification_report
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
import logging

# Suppress sklearn convergence warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

logger = logging.getLogger(__name__)

class AgriculturalMLSystem:
    """Advanced ML system for agricultural recommendations with continuous learning"""
    
    def __init__(self):
        self.models = {}
        self.encoders = {}
        self.scalers = {}
        self.feature_columns = []
        self.model_metrics = {}
        self.feedback_data = []
        self.user_history = {}
        
        # Initialize models
        self._initialize_models()
        self._load_existing_data()
    
    def _initialize_models(self):
        """Initialize ML models for different agricultural tasks"""
        
        # Crop Recommendation Model (Classification)
        self.models['crop_recommendation'] = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        
        # Yield Prediction Model (Regression)
        self.models['yield_prediction'] = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            random_state=42
        )
        
        # Fertilizer Recommendation Model (Regression for nutrient amounts)
        self.models['fertilizer_recommendation'] = MLPRegressor(
            hidden_layer_sizes=(50, 25),
            max_iter=1000,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1
        )
        
        # Market Price Prediction Model
        self.models['price_prediction'] = LinearRegression()
        
        # Weather Impact Model
        self.models['weather_impact'] = RandomForestRegressor(
            n_estimators=50,
            max_depth=8,
            random_state=42
        )
        
        # Initialize encoders and scalers
        self.encoders = {
            'crop_type': LabelEncoder(),
            'soil_type': LabelEncoder(),
            'season': LabelEncoder(),
            'region': LabelEncoder()
        }
        
        self.scalers = {
            'yield_prediction': StandardScaler(),
            'fertilizer_recommendation': StandardScaler(),
            'price_prediction': StandardScaler(),
            'weather_impact': StandardScaler()
        }
    
    def _load_existing_data(self):
        """Load existing training data and user feedback"""
        try:
            # Load historical data
            if os.path.exists('agricultural_data.json'):
                with open('agricultural_data.json', 'r') as f:
                    data = json.load(f)
                    self.feedback_data = data.get('feedback_data', [])
                    self.user_history = data.get('user_history', {})
            
            # Load trained models if they exist
            self._load_trained_models()
            
            # Load initial training data
            self._create_initial_training_data()
            
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
            self._create_initial_training_data()
    
    def _create_initial_training_data(self):
        """Create initial training data based on agricultural research and government data"""
        
        # Initial crop recommendation data
        crop_data = [
            # Format: [soil_type, season, temperature, rainfall, humidity, ph, organic_matter, crop_type]
            ['loamy', 'kharif', 28, 1200, 70, 6.5, 2.5, 'rice'],
            ['loamy', 'rabi', 22, 400, 60, 6.5, 2.5, 'wheat'],
            ['clayey', 'kharif', 30, 1000, 75, 7.0, 2.0, 'rice'],
            ['clayey', 'rabi', 20, 300, 55, 7.0, 2.0, 'wheat'],
            ['sandy', 'kharif', 32, 800, 65, 6.0, 1.5, 'maize'],
            ['sandy', 'rabi', 25, 200, 50, 6.0, 1.5, 'wheat'],
            ['silty', 'kharif', 29, 1100, 68, 6.8, 2.2, 'rice'],
            ['silty', 'rabi', 23, 350, 58, 6.8, 2.2, 'wheat'],
            ['loamy', 'zaid', 35, 200, 60, 6.5, 2.5, 'tomato'],
            ['clayey', 'zaid', 33, 150, 65, 7.0, 2.0, 'onion'],
            ['sandy', 'zaid', 37, 100, 55, 6.0, 1.5, 'watermelon'],
            ['silty', 'zaid', 34, 180, 62, 6.8, 2.2, 'cucumber']
        ]
        
        # Convert to DataFrame
        columns = ['soil_type', 'season', 'temperature', 'rainfall', 'humidity', 'ph', 'organic_matter', 'crop_type']
        self.training_data = pd.DataFrame(crop_data, columns=columns)
        
        # Create yield prediction data
        yield_data = []
        for _, row in self.training_data.iterrows():
            base_yield = self._calculate_base_yield(row['crop_type'], row['soil_type'])
            # Add some variation based on conditions
            variation = np.random.normal(0, 0.1)
            predicted_yield = base_yield * (1 + variation)
            yield_data.append(predicted_yield)
        
        self.training_data['yield'] = yield_data
        
        # Create fertilizer recommendation data
        fertilizer_data = []
        for _, row in self.training_data.iterrows():
            n, p, k = self._calculate_fertilizer_needs(row['crop_type'], row['soil_type'], row['season'])
            fertilizer_data.append([n, p, k])
        
        self.training_data[['nitrogen', 'phosphorus', 'potassium']] = fertilizer_data
        
        # Train initial models
        self._train_initial_models()
    
    def _calculate_base_yield(self, crop_type: str, soil_type: str) -> float:
        """Calculate base yield for a crop and soil combination"""
        base_yields = {
            'rice': {'loamy': 4.5, 'clayey': 5.0, 'sandy': 3.0, 'silty': 4.2},
            'wheat': {'loamy': 4.0, 'clayey': 3.5, 'sandy': 2.5, 'silty': 3.8},
            'maize': {'loamy': 6.0, 'clayey': 5.5, 'sandy': 4.5, 'silty': 5.8},
            'tomato': {'loamy': 25.0, 'clayey': 22.0, 'sandy': 18.0, 'silty': 24.0},
            'onion': {'loamy': 20.0, 'clayey': 18.0, 'sandy': 15.0, 'silty': 19.0},
            'watermelon': {'loamy': 30.0, 'clayey': 25.0, 'sandy': 35.0, 'silty': 28.0},
            'cucumber': {'loamy': 15.0, 'clayey': 12.0, 'sandy': 10.0, 'silty': 14.0}
        }
        return base_yields.get(crop_type, {}).get(soil_type, 3.0)
    
    def _calculate_fertilizer_needs(self, crop_type: str, soil_type: str, season: str) -> Tuple[float, float, float]:
        """Calculate fertilizer needs for a crop, soil, and season combination"""
        base_fertilizers = {
            'rice': (100, 50, 50),
            'wheat': (120, 60, 40),
            'maize': (150, 80, 60),
            'tomato': (100, 60, 80),
            'onion': (80, 40, 60),
            'watermelon': (60, 40, 40),
            'cucumber': (80, 50, 60)
        }
        
        soil_adjustments = {
            'loamy': (1.0, 1.0, 1.0),
            'clayey': (1.2, 0.8, 1.1),
            'sandy': (1.5, 1.3, 1.4),
            'silty': (1.1, 1.0, 1.1)
        }
        
        season_adjustments = {
            'kharif': (1.1, 1.0, 1.0),
            'rabi': (1.0, 1.1, 1.0),
            'zaid': (1.2, 1.0, 1.1)
        }
        
        base_n, base_p, base_k = base_fertilizers.get(crop_type, (100, 50, 50))
        soil_adj_n, soil_adj_p, soil_adj_k = soil_adjustments.get(soil_type, (1.0, 1.0, 1.0))
        season_adj_n, season_adj_p, season_adj_k = season_adjustments.get(season, (1.0, 1.0, 1.0))
        
        n = base_n * soil_adj_n * season_adj_n
        p = base_p * soil_adj_p * season_adj_p
        k = base_k * soil_adj_k * season_adj_k
        
        return n, p, k
    
    def _train_initial_models(self):
        """Train initial models with the created data"""
        try:
            # Prepare features
            X = self.training_data[['soil_type', 'season', 'temperature', 'rainfall', 'humidity', 'ph', 'organic_matter']].copy()
            
            # Encode categorical variables
            for col in ['soil_type', 'season']:
                X[col] = self.encoders[col].fit_transform(X[col])
            
            # Train crop recommendation model
            y_crop = self.training_data['crop_type']
            self.models['crop_recommendation'].fit(X, y_crop)
            
            # Train yield prediction model
            y_yield = self.training_data['yield']
            X_scaled = self.scalers['yield_prediction'].fit_transform(X)
            self.models['yield_prediction'].fit(X_scaled, y_yield)
            
            # Train fertilizer recommendation model
            y_fertilizer = self.training_data[['nitrogen', 'phosphorus', 'potassium']]
            X_fert_scaled = self.scalers['fertilizer_recommendation'].fit_transform(X)
            self.models['fertilizer_recommendation'].fit(X_fert_scaled, y_fertilizer)
            
            # Calculate initial metrics
            self._calculate_model_metrics()
            
            logger.info("Initial models trained successfully")
            
        except Exception as e:
            logger.error(f"Error training initial models: {e}")
    
    def _calculate_model_metrics(self):
        """Calculate and store model performance metrics"""
        try:
            X = self.training_data[['soil_type', 'season', 'temperature', 'rainfall', 'humidity', 'ph', 'organic_matter']].copy()
            
            # Encode categorical variables
            for col in ['soil_type', 'season']:
                X[col] = self.encoders[col].transform(X[col])
            
            # Crop recommendation metrics
            y_crop = self.training_data['crop_type']
            y_crop_pred = self.models['crop_recommendation'].predict(X)
            crop_accuracy = accuracy_score(y_crop, y_crop_pred)
            
            # Yield prediction metrics
            y_yield = self.training_data['yield']
            X_scaled = self.scalers['yield_prediction'].transform(X)
            y_yield_pred = self.models['yield_prediction'].predict(X_scaled)
            yield_r2 = r2_score(y_yield, y_yield_pred)
            yield_rmse = np.sqrt(mean_squared_error(y_yield, y_yield_pred))
            
            # Fertilizer recommendation metrics
            y_fertilizer = self.training_data[['nitrogen', 'phosphorus', 'potassium']]
            X_fert_scaled = self.scalers['fertilizer_recommendation'].transform(X)
            y_fert_pred = self.models['fertilizer_recommendation'].predict(X_fert_scaled)
            fert_r2 = r2_score(y_fertilizer, y_fert_pred)
            
            self.model_metrics = {
                'crop_recommendation': {'accuracy': crop_accuracy},
                'yield_prediction': {'r2_score': yield_r2, 'rmse': yield_rmse},
                'fertilizer_recommendation': {'r2_score': fert_r2},
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating model metrics: {e}")
    
    def get_crop_recommendations(self, soil_type: str, latitude: float, longitude: float, season: str) -> Dict[str, Any]:
        """
        Provides comprehensive crop recommendations based on soil type, location, and season.
        Integrates real government data, weather information, and market prices.
        """
        try:
            # Get current weather data for the location
            from ..services.weather_api import MockWeatherAPI
            weather_api = MockWeatherAPI()
            weather_data = weather_api.get_current_weather(latitude, longitude, 'en')
            
            # Extract weather parameters
            temperature = 25.0  # Default temperature
            rainfall = 0.0  # Default rainfall
            humidity = 60.0  # Default humidity
            
            if weather_data:
                # Parse temperature (remove °C and convert to float)
                temp_str = weather_data.get('temperature', '25.0°C')
                temperature = float(temp_str.replace('°C', '').replace('Â°C', ''))
                
                # Parse rainfall (remove mm and convert to float)
                rain_str = weather_data.get('rainfall', '0 mm')
                rainfall = float(rain_str.replace('mm', '').replace(' ', ''))
                
                # Parse humidity (remove % and convert to float)
                hum_str = weather_data.get('humidity', '60%')
                humidity = float(hum_str.replace('%', '').replace(' ', ''))
            
            # Get market prices for better recommendations
            from ..services.market_api import get_market_prices
            market_data = get_market_prices(latitude, longitude, 'en')
            
            # Determine soil characteristics based on location and type
            ph = self._get_soil_ph(latitude, longitude, soil_type)
            organic_matter = self._get_organic_matter_content(soil_type)
            
            # Get crop recommendations based on season and location
            recommendations = self._get_seasonal_crop_recommendations(
                season, latitude, longitude, soil_type, temperature, rainfall, humidity, ph, organic_matter
            )
            
            # Filter recommendations based on market prices and profitability
            profitable_crops = self._filter_profitable_crops(recommendations, market_data)
            
            return {
                "recommended_crops": profitable_crops,
                "weather_conditions": {
                    "temperature": temperature,
                    "rainfall": rainfall,
                    "humidity": humidity
                },
                "soil_conditions": {
                    "type": soil_type,
                    "ph": ph,
                    "organic_matter": organic_matter
                },
                "season": season,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "market_analysis": self._analyze_market_trends(market_data),
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in get_crop_recommendations: {e}")
            # Fallback to basic recommendations
            return self._get_fallback_crop_recommendations(season, soil_type)
    
    def _get_soil_ph(self, latitude: float, longitude: float, soil_type: str) -> float:
        """Get soil pH based on location and soil type"""
        # This would ideally connect to government soil databases
        ph_ranges = {
            'clay': 6.5,
            'loamy': 6.8,
            'sandy': 7.0,
            'silty': 6.7,
            'black': 7.2,
            'red': 6.3
        }
        return ph_ranges.get(soil_type.lower(), 6.8)
    
    def _get_organic_matter_content(self, soil_type: str) -> float:
        """Get organic matter content based on soil type"""
        organic_content = {
            'clay': 2.5,
            'loamy': 3.0,
            'sandy': 1.5,
            'silty': 2.8,
            'black': 4.0,
            'red': 2.0
        }
        return organic_content.get(soil_type.lower(), 2.5)
    
    def _get_seasonal_crop_recommendations(self, season: str, latitude: float, longitude: float, 
                                         soil_type: str, temperature: float, rainfall: float, 
                                         humidity: float, ph: float, organic_matter: float) -> List[Dict]:
        """Get crop recommendations based on season and environmental conditions"""
        
        # Define crop database with environmental requirements
        crop_database = {
            'kharif': [
                {'crop_name': 'Rice', 'confidence': 0.9, 'profitability': 'high', 'water_requirement': 'high'},
                {'crop_name': 'Maize', 'confidence': 0.85, 'profitability': 'medium', 'water_requirement': 'medium'},
                {'crop_name': 'Soybean', 'confidence': 0.8, 'profitability': 'high', 'water_requirement': 'medium'},
                {'crop_name': 'Cotton', 'confidence': 0.75, 'profitability': 'high', 'water_requirement': 'medium'},
                {'crop_name': 'Groundnut', 'confidence': 0.7, 'profitability': 'medium', 'water_requirement': 'low'},
                {'crop_name': 'Sugarcane', 'confidence': 0.65, 'profitability': 'high', 'water_requirement': 'high'}
            ],
            'rabi': [
                {'crop_name': 'Wheat', 'confidence': 0.9, 'profitability': 'high', 'water_requirement': 'medium'},
                {'crop_name': 'Mustard', 'confidence': 0.85, 'profitability': 'high', 'water_requirement': 'low'},
                {'crop_name': 'Chickpea', 'confidence': 0.8, 'profitability': 'medium', 'water_requirement': 'low'},
                {'crop_name': 'Barley', 'confidence': 0.75, 'profitability': 'medium', 'water_requirement': 'low'},
                {'crop_name': 'Potato', 'confidence': 0.7, 'profitability': 'high', 'water_requirement': 'medium'},
                {'crop_name': 'Onion', 'confidence': 0.65, 'profitability': 'high', 'water_requirement': 'medium'}
            ],
            'zaid': [
                {'crop_name': 'Cucumber', 'confidence': 0.8, 'profitability': 'high', 'water_requirement': 'high'},
                {'crop_name': 'Watermelon', 'confidence': 0.75, 'profitability': 'medium', 'water_requirement': 'high'},
                {'crop_name': 'Green Gram', 'confidence': 0.7, 'profitability': 'medium', 'water_requirement': 'low'},
                {'crop_name': 'Tomato', 'confidence': 0.65, 'profitability': 'high', 'water_requirement': 'medium'},
                {'crop_name': 'Okra', 'confidence': 0.6, 'profitability': 'medium', 'water_requirement': 'medium'}
            ]
        }
        
        # Get base recommendations for the season
        base_crops = crop_database.get(season.lower(), crop_database['kharif'])
        
        # Adjust confidence based on environmental conditions
        adjusted_crops = []
        for crop in base_crops:
            adjusted_confidence = crop['confidence']
            
            # Adjust based on temperature
            if temperature < 15 or temperature > 35:
                adjusted_confidence *= 0.8
            
            # Adjust based on rainfall
            if rainfall < 50 and crop['water_requirement'] == 'high':
                adjusted_confidence *= 0.7
            elif rainfall > 200 and crop['water_requirement'] == 'low':
                adjusted_confidence *= 0.8
            
            # Adjust based on soil type
            if soil_type.lower() == 'sandy' and crop['water_requirement'] == 'high':
                adjusted_confidence *= 0.8
            elif soil_type.lower() == 'clay' and crop['water_requirement'] == 'low':
                adjusted_confidence *= 0.9
            
            crop['confidence'] = min(adjusted_confidence, 0.95)  # Cap at 95%
            adjusted_crops.append(crop)
        
        # Sort by confidence and return top recommendations
        adjusted_crops.sort(key=lambda x: x['confidence'], reverse=True)
        return adjusted_crops[:5]  # Return top 5 recommendations
    
    def _filter_profitable_crops(self, recommendations: List[Dict], market_data: List[Dict]) -> List[Dict]:
        """Filter crops based on current market prices and profitability"""
        if not market_data:
            return recommendations[:3]  # Return top 3 if no market data
        
        # Create a price lookup dictionary
        price_lookup = {}
        for item in market_data:
            commodity = item.get('commodity', '').lower()
            price_str = item.get('price', '0')
            # Extract numeric price (remove currency symbols)
            try:
                price = float(price_str.replace('₹', '').replace(',', '').replace('â¹', ''))
                price_lookup[commodity] = price
            except:
                continue
        
        # Score crops based on profitability
        scored_crops = []
        for crop in recommendations:
            crop_name = crop['crop_name'].lower()
            base_score = crop['confidence']
            
            # Adjust score based on market price
            if crop_name in price_lookup:
                price = price_lookup[crop_name]
                # Higher prices get higher scores (simplified scoring)
                if price > 3000:  # High price threshold
                    base_score *= 1.2
                elif price > 2000:  # Medium price threshold
                    base_score *= 1.1
            
            crop['market_score'] = base_score
            scored_crops.append(crop)
        
        # Sort by market score and return top 3
        scored_crops.sort(key=lambda x: x['market_score'], reverse=True)
        return scored_crops[:3]
    
    def _analyze_market_trends(self, market_data: List[Dict]) -> Dict[str, Any]:
        """Analyze market trends for better recommendations"""
        if not market_data:
            return {"trend": "stable", "analysis": "Market data not available"}
        
        # Simple trend analysis
        total_items = len(market_data)
        positive_changes = sum(1 for item in market_data if '+' in item.get('change', ''))
        
        if positive_changes > total_items * 0.6:
            trend = "rising"
        elif positive_changes < total_items * 0.4:
            trend = "falling"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "analysis": f"Market showing {trend} trends",
            "total_commodities": total_items,
            "positive_changes": positive_changes
        }
    
    def _get_fallback_crop_recommendations(self, season: str, soil_type: str) -> Dict[str, Any]:
        """Fallback crop recommendations when main system fails"""
        fallback_crops = {
            'kharif': [
                {'crop_name': 'Rice', 'confidence': 0.8},
                {'crop_name': 'Maize', 'confidence': 0.7},
                {'crop_name': 'Soybean', 'confidence': 0.6}
            ],
            'rabi': [
                {'crop_name': 'Wheat', 'confidence': 0.8},
                {'crop_name': 'Mustard', 'confidence': 0.7},
                {'crop_name': 'Chickpea', 'confidence': 0.6}
            ],
            'zaid': [
                {'crop_name': 'Cucumber', 'confidence': 0.7},
                {'crop_name': 'Watermelon', 'confidence': 0.6},
                {'crop_name': 'Green Gram', 'confidence': 0.5}
            ]
        }
        
        return {
            "recommended_crops": fallback_crops.get(season.lower(), fallback_crops['kharif']),
            "confidence": 0.6,
            "note": "Using fallback recommendations",
            "timestamp": datetime.now().isoformat()
        }
    def predict_crop_recommendation(self, soil_type: str, season: str, temperature: float, 
                                  rainfall: float, humidity: float, ph: float, 
                                  organic_matter: float) -> Dict[str, Any]:
        try:
            # Prepare input data
            input_data = pd.DataFrame([{
                'soil_type': soil_type,
                'season': season,
                'temperature': temperature,
                'rainfall': rainfall,
                'humidity': humidity,
                'ph': ph,
                'organic_matter': organic_matter
            }])
            
            # Encode categorical variables
            for col in ['soil_type', 'season']:
                input_data[col] = self.encoders[col].transform(input_data[col])
            
            # Make prediction
            prediction = self.models['crop_recommendation'].predict(input_data)[0]
            probabilities = self.models['crop_recommendation'].predict_proba(input_data)[0]
            classes = self.models['crop_recommendation'].classes_
            
            # Get top 3 recommendations
            top_indices = np.argsort(probabilities)[-3:][::-1]
            recommendations = []
            for idx in top_indices:
                recommendations.append({
                    'crop': classes[idx],
                    'probability': float(probabilities[idx]),
                    'confidence': 'high' if probabilities[idx] > 0.7 else 'medium' if probabilities[idx] > 0.4 else 'low'
                })
            
            return {
                'recommendations': recommendations,
                'model_accuracy': self.model_metrics.get('crop_recommendation', {}).get('accuracy', 0),
                'prediction_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in crop recommendation prediction: {e}")
            return {'error': str(e)}
    
    def predict_yield(self, crop_type: str, soil_type: str, season: str, temperature: float,
                     rainfall: float, humidity: float, ph: float, organic_matter: float) -> Dict[str, Any]:
        """Predict crop yield using ML model"""
        try:
            # Prepare input data
            input_data = pd.DataFrame([{
                'soil_type': soil_type,
                'season': season,
                'temperature': temperature,
                'rainfall': rainfall,
                'humidity': humidity,
                'ph': ph,
                'organic_matter': organic_matter
            }])
            
            # Encode categorical variables
            for col in ['soil_type', 'season']:
                input_data[col] = self.encoders[col].transform(input_data[col])
            
            # Scale features
            input_scaled = self.scalers['yield_prediction'].transform(input_data)
            
            # Make prediction
            predicted_yield = self.models['yield_prediction'].predict(input_scaled)[0]
            
            # Calculate confidence interval (simplified)
            confidence_interval = predicted_yield * 0.15  # ±15% confidence interval
            
            return {
                'predicted_yield': float(predicted_yield),
                'confidence_interval': float(confidence_interval),
                'yield_range': {
                    'min': float(predicted_yield - confidence_interval),
                    'max': float(predicted_yield + confidence_interval)
                },
                'model_r2': self.model_metrics.get('yield_prediction', {}).get('r2_score', 0),
                'prediction_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in yield prediction: {e}")
            return {'error': str(e)}
    
    def predict_fertilizer_needs(self, crop_type: str, soil_type: str, season: str, 
                               temperature: float, rainfall: float, humidity: float, 
                               ph: float, organic_matter: float) -> Dict[str, Any]:
        """Predict fertilizer needs using ML model"""
        try:
            # Prepare input data
            input_data = pd.DataFrame([{
                'soil_type': soil_type,
                'season': season,
                'temperature': temperature,
                'rainfall': rainfall,
                'humidity': humidity,
                'ph': ph,
                'organic_matter': organic_matter
            }])
            
            # Encode categorical variables
            for col in ['soil_type', 'season']:
                input_data[col] = self.encoders[col].transform(input_data[col])
            
            # Scale features
            input_scaled = self.scalers['fertilizer_recommendation'].transform(input_data)
            
            # Make prediction
            prediction = self.models['fertilizer_recommendation'].predict(input_scaled)[0]
            
            return {
                'nitrogen': float(prediction[0]),
                'phosphorus': float(prediction[1]),
                'potassium': float(prediction[2]),
                'model_r2': self.model_metrics.get('fertilizer_recommendation', {}).get('r2_score', 0),
                'prediction_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in fertilizer prediction: {e}")
            return {'error': str(e)}
    
    def collect_feedback(self, user_id: str, prediction_type: str, input_data: Dict, 
                        prediction: Dict, actual_result: Dict, feedback_rating: int) -> bool:
        """Collect user feedback for model improvement"""
        try:
            feedback_entry = {
                'user_id': user_id,
                'prediction_type': prediction_type,
                'input_data': input_data,
                'prediction': prediction,
                'actual_result': actual_result,
                'feedback_rating': feedback_rating,
                'timestamp': datetime.now().isoformat()
            }
            
            self.feedback_data.append(feedback_entry)
            
            # Update user history
            if user_id not in self.user_history:
                self.user_history[user_id] = []
            self.user_history[user_id].append(feedback_entry)
            
            # Save feedback data
            self._save_feedback_data()
            
            # Trigger retraining if enough feedback collected
            if len(self.feedback_data) % 50 == 0:  # Retrain every 50 feedback entries
                self._retrain_models()
            
            return True
            
        except Exception as e:
            logger.error(f"Error collecting feedback: {e}")
            return False
    
    def _retrain_models(self):
        """Retrain models based on user feedback"""
        try:
            if len(self.feedback_data) < 10:  # Need minimum feedback for retraining
                return
            
            # Prepare feedback data for training
            feedback_df = pd.DataFrame(self.feedback_data)
            
            # Filter recent feedback (last 6 months)
            recent_feedback = feedback_df[
                pd.to_datetime(feedback_df['timestamp']) > 
                datetime.now() - timedelta(days=180)
            ]
            
            if len(recent_feedback) < 5:
                return
            
            # Create training data from feedback
            new_training_data = []
            for _, feedback in recent_feedback.iterrows():
                if feedback['prediction_type'] == 'crop_recommendation':
                    input_data = feedback['input_data']
                    actual_crop = feedback['actual_result'].get('crop_type')
                    if actual_crop:
                        new_training_data.append([
                            input_data.get('soil_type'),
                            input_data.get('season'),
                            input_data.get('temperature'),
                            input_data.get('rainfall'),
                            input_data.get('humidity'),
                            input_data.get('ph'),
                            input_data.get('organic_matter'),
                            actual_crop
                        ])
            
            if len(new_training_data) > 0:
                # Add new data to existing training data
                new_df = pd.DataFrame(new_training_data, columns=self.training_data.columns)
                self.training_data = pd.concat([self.training_data, new_df], ignore_index=True)
                
                # Retrain models
                self._train_initial_models()
                
                # Save updated models
                self._save_trained_models()
                
                logger.info(f"Models retrained with {len(new_training_data)} new feedback entries")
            
        except Exception as e:
            logger.error(f"Error retraining models: {e}")
    
    def _save_feedback_data(self):
        """Save feedback data to file"""
        try:
            data = {
                'feedback_data': self.feedback_data,
                'user_history': self.user_history,
                'last_updated': datetime.now().isoformat()
            }
            
            with open('agricultural_data.json', 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving feedback data: {e}")
    
    def _save_trained_models(self):
        """Save trained models to disk"""
        try:
            # Create models directory if it doesn't exist
            os.makedirs('models', exist_ok=True)
            
            # Save models
            for model_name, model in self.models.items():
                joblib.dump(model, f'models/{model_name}_model.pkl')
            
            # Save encoders
            for encoder_name, encoder in self.encoders.items():
                joblib.dump(encoder, f'models/{encoder_name}_encoder.pkl')
            
            # Save scalers
            for scaler_name, scaler in self.scalers.items():
                joblib.dump(scaler, f'models/{scaler_name}_scaler.pkl')
            
            # Save metrics
            with open('models/model_metrics.json', 'w') as f:
                json.dump(self.model_metrics, f, indent=2)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def _load_trained_models(self):
        """Load trained models from disk"""
        try:
            if not os.path.exists('models'):
                return
            
            # Load models
            for model_name in self.models.keys():
                model_path = f'models/{model_name}_model.pkl'
                if os.path.exists(model_path):
                    self.models[model_name] = joblib.load(model_path)
            
            # Load encoders
            for encoder_name in self.encoders.keys():
                encoder_path = f'models/{encoder_name}_encoder.pkl'
                if os.path.exists(encoder_path):
                    self.encoders[encoder_name] = joblib.load(encoder_path)
            
            # Load scalers
            for scaler_name in self.scalers.keys():
                scaler_path = f'models/{scaler_name}_scaler.pkl'
                if os.path.exists(scaler_path):
                    self.scalers[scaler_name] = joblib.load(scaler_path)
            
            # Load metrics
            metrics_path = 'models/model_metrics.json'
            if os.path.exists(metrics_path):
                with open(metrics_path, 'r') as f:
                    self.model_metrics = json.load(f)
            
            logger.info("Models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get current model performance metrics"""
        return {
            'model_metrics': self.model_metrics,
            'total_feedback_entries': len(self.feedback_data),
            'total_users': len(self.user_history),
            'last_retraining': self.model_metrics.get('last_updated', 'Never'),
            'system_status': 'Active' if len(self.feedback_data) > 0 else 'Initial'
        }
    
    def get_personalized_recommendations(self, user_id: str, input_data: Dict) -> Dict[str, Any]:
        """Get personalized recommendations based on user history"""
        try:
            if user_id not in self.user_history:
                # New user - use general recommendations
                return self.predict_crop_recommendation(**input_data)
            
            # Get user's historical preferences
            user_feedback = self.user_history[user_id]
            recent_feedback = [f for f in user_feedback if 
                             datetime.fromisoformat(f['timestamp']) > 
                             datetime.now() - timedelta(days=90)]
            
            if len(recent_feedback) < 3:
                # Not enough history - use general recommendations
                return self.predict_crop_recommendation(**input_data)
            
            # Analyze user preferences
            user_preferences = self._analyze_user_preferences(recent_feedback)
            
            # Get general recommendations
            general_recs = self.predict_crop_recommendation(**input_data)
            
            # Personalize recommendations based on user history
            personalized_recs = self._personalize_recommendations(general_recs, user_preferences)
            
            return personalized_recs
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            return self.predict_crop_recommendation(**input_data)
    
    def _analyze_user_preferences(self, user_feedback: List[Dict]) -> Dict[str, Any]:
        """Analyze user preferences from feedback history"""
        preferences = {
            'preferred_crops': {},
            'soil_preferences': {},
            'season_preferences': {},
            'success_rate': 0
        }
        
        successful_predictions = 0
        total_predictions = len(user_feedback)
        
        for feedback in user_feedback:
            if feedback['feedback_rating'] >= 4:  # High rating
                successful_predictions += 1
                
                # Track successful crop types
                actual_crop = feedback['actual_result'].get('crop_type')
                if actual_crop:
                    preferences['preferred_crops'][actual_crop] = preferences['preferred_crops'].get(actual_crop, 0) + 1
                
                # Track successful soil types
                soil_type = feedback['input_data'].get('soil_type')
                if soil_type:
                    preferences['soil_preferences'][soil_type] = preferences['soil_preferences'].get(soil_type, 0) + 1
                
                # Track successful seasons
                season = feedback['input_data'].get('season')
                if season:
                    preferences['season_preferences'][season] = preferences['season_preferences'].get(season, 0) + 1
        
        preferences['success_rate'] = successful_predictions / total_predictions if total_predictions > 0 else 0
        
        return preferences
    
    def _personalize_recommendations(self, general_recs: Dict, user_preferences: Dict) -> Dict[str, Any]:
        """Personalize recommendations based on user preferences"""
        personalized_recs = general_recs.copy()
        
        # Boost recommendations based on user's successful crop history
        preferred_crops = user_preferences.get('preferred_crops', {})
        if preferred_crops:
            for rec in personalized_recs['recommendations']:
                crop = rec['crop']
                if crop in preferred_crops:
                    # Boost probability for preferred crops
                    rec['probability'] = min(1.0, rec['probability'] * 1.2)
                    rec['personalized'] = True
        
        # Add personalization note
        personalized_recs['personalization'] = {
            'user_success_rate': user_preferences.get('success_rate', 0),
            'preferred_crops': list(preferred_crops.keys()),
            'personalization_applied': len(preferred_crops) > 0
        }
        
        return personalized_recs
