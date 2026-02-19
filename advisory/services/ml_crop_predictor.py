#!/usr/bin/env python3
"""
ML-Enhanced Crop Recommendation System
Adds machine learning capabilities for improved accuracy and continuous learning
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os

logger = logging.getLogger(__name__)

class MLCropPredictor:
    """Machine Learning models for crop prediction"""
    
    def __init__(self):
        self.success_model = None
        self.yield_model = None
        self.profit_model = None
        self.scaler = StandardScaler()
        self.models_trained = False
        
        # Try to load pre-trained models
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models if available"""
        try:
            model_dir = os.path.join(os.path.dirname(__file__), 'ml_models')
            if os.path.exists(model_dir):
                self.success_model = joblib.load(os.path.join(model_dir, 'success_model.pkl'))
                self.yield_model = joblib.load(os.path.join(model_dir, 'yield_model.pkl'))
                self.profit_model = joblib.load(os.path.join(model_dir, 'profit_model.pkl'))
                self.scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))
                self.models_trained = True
                logger.info("✅ ML models loaded successfully")
        except Exception as e:
            logger.info(f"No pre-trained models found: {e}")
            self._initialize_models()
    
    def _initialize_models(self):
        """Initialize models with default parameters"""
        self.success_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.yield_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        self.profit_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        logger.info("ML models initialized (not yet trained)")
    
    def extract_features(self, crop_data: Dict, weather_data: Dict, 
                        location_data: Dict, soil_data: Dict) -> np.ndarray:
        """
        Extract features for ML models
        
        Features:
        - Temperature (current, avg, min, max)
        - Humidity
        - Rainfall (current, forecast)
        - Soil type (encoded)
        - Season (encoded)
        - Location (lat, lon)
        - Crop characteristics
        """
        features = []
        
        # Weather features
        temp = self._extract_temperature(weather_data)
        features.extend([
            temp.get('current', 25),
            temp.get('avg_7day', 25),
            temp.get('min_7day', 20),
            temp.get('max_7day', 30)
        ])
        
        humidity = weather_data.get('humidity', 65)
        if isinstance(humidity, str):
            humidity = float(humidity.replace('%', ''))
        features.append(humidity)
        
        # Rainfall features
        rainfall = self._extract_rainfall(weather_data)
        features.extend([
            rainfall.get('current', 0),
            rainfall.get('forecast_7day', 0)
        ])
        
        # Soil features (encoded)
        soil_type = soil_data.get('type', 'loamy').lower()
        soil_encoding = {
            'black': 1, 'red': 2, 'alluvial': 3, 
            'sandy': 4, 'clayey': 5, 'loamy': 6
        }
        features.append(soil_encoding.get(soil_type, 6))
        
        # Season features (encoded)
        season = crop_data.get('season', 'kharif').lower()
        season_encoding = {'kharif': 1, 'rabi': 2, 'zaid': 3, 'year_round': 4}
        features.append(season_encoding.get(season, 1))
        
        # Location features
        features.extend([
            location_data.get('latitude', 28.0),
            location_data.get('longitude', 77.0)
        ])
        
        # Crop characteristics
        features.extend([
            crop_data.get('duration_days', 120),
            crop_data.get('water_requirement_encoded', 2),  # 1=low, 2=moderate, 3=high
            crop_data.get('profit_per_hectare', 50000) / 100000  # Normalize
        ])
        
        return np.array(features).reshape(1, -1)
    
    def _extract_temperature(self, weather_data: Dict) -> Dict:
        """Extract temperature data"""
        current_temp = weather_data.get('temperature', '25°C')
        if isinstance(current_temp, str):
            current_temp = float(current_temp.replace('°C', ''))
        
        forecast = weather_data.get('forecast_7day', [])
        temps = [current_temp]
        
        for day in forecast:
            if 'temperature' in day:
                temp = day['temperature']
                if isinstance(temp, str):
                    temp = float(temp.replace('°C', ''))
                temps.append(temp)
        
        return {
            'current': current_temp,
            'avg_7day': np.mean(temps) if temps else current_temp,
            'min_7day': np.min(temps) if temps else current_temp - 5,
            'max_7day': np.max(temps) if temps else current_temp + 5
        }
    
    def _extract_rainfall(self, weather_data: Dict) -> Dict:
        """Extract rainfall data"""
        current_rainfall = 0
        condition = weather_data.get('condition', '').lower()
        if 'rain' in condition or 'बारिश' in condition:
            current_rainfall = 5  # mm (estimate)
        
        forecast = weather_data.get('forecast_7day', [])
        forecast_rainfall = 0
        for day in forecast:
            if 'rain' in str(day.get('condition', '')).lower():
                forecast_rainfall += 5
        
        return {
            'current': current_rainfall,
            'forecast_7day': forecast_rainfall
        }
    
    def predict_success(self, features: np.ndarray) -> float:
        """Predict crop success probability (0-1)"""
        if not self.models_trained:
            # Return default confidence if model not trained
            return 0.75
        
        try:
            features_scaled = self.scaler.transform(features)
            probability = self.success_model.predict_proba(features_scaled)[0][1]
            return float(probability)
        except Exception as e:
            logger.error(f"Error in success prediction: {e}")
            return 0.75
    
    def predict_yield(self, features: np.ndarray, base_yield: float) -> float:
        """Predict expected yield (quintals/hectare)"""
        if not self.models_trained:
            # Return base yield with small variation
            return base_yield * np.random.uniform(0.9, 1.1)
        
        try:
            features_scaled = self.scaler.transform(features)
            predicted_yield = self.yield_model.predict(features_scaled)[0]
            return max(0, float(predicted_yield))
        except Exception as e:
            logger.error(f"Error in yield prediction: {e}")
            return base_yield
    
    def predict_profit(self, features: np.ndarray, base_profit: float) -> float:
        """Predict expected profit (₹/hectare)"""
        if not self.models_trained:
            # Return base profit with market variation
            return base_profit * np.random.uniform(0.85, 1.15)
        
        try:
            features_scaled = self.scaler.transform(features)
            predicted_profit = self.profit_model.predict(features_scaled)[0]
            return max(0, float(predicted_profit))
        except Exception as e:
            logger.error(f"Error in profit prediction: {e}")
            return base_profit
    
    def train_models(self, training_data: List[Dict]):
        """
        Train ML models with historical data
        
        training_data format:
        [{
            'features': {...},
            'success': 1/0,
            'yield': float,
            'profit': float
        }, ...]
        """
        if len(training_data) < 50:
            logger.warning(f"Insufficient training data: {len(training_data)} samples (need 50+)")
            return False
        
        try:
            # Extract features and targets
            X = []
            y_success = []
            y_yield = []
            y_profit = []
            
            for sample in training_data:
                features = self.extract_features(
                    sample['crop_data'],
                    sample['weather_data'],
                    sample['location_data'],
                    sample['soil_data']
                )
                X.append(features[0])
                y_success.append(sample['success'])
                y_yield.append(sample['yield'])
                y_profit.append(sample['profit'])
            
            X = np.array(X)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train models
            self.success_model.fit(X_scaled, y_success)
            self.yield_model.fit(X_scaled, y_yield)
            self.profit_model.fit(X_scaled, y_profit)
            
            self.models_trained = True
            
            # Save models
            self._save_models()
            
            logger.info(f"✅ ML models trained successfully with {len(training_data)} samples")
            return True
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
            return False
    
    def _save_models(self):
        """Save trained models"""
        try:
            model_dir = os.path.join(os.path.dirname(__file__), 'ml_models')
            os.makedirs(model_dir, exist_ok=True)
            
            joblib.dump(self.success_model, os.path.join(model_dir, 'success_model.pkl'))
            joblib.dump(self.yield_model, os.path.join(model_dir, 'yield_model.pkl'))
            joblib.dump(self.profit_model, os.path.join(model_dir, 'profit_model.pkl'))
            joblib.dump(self.scaler, os.path.join(model_dir, 'scaler.pkl'))
            
            logger.info("✅ ML models saved successfully")
        except Exception as e:
            logger.error(f"Error saving models: {e}")
