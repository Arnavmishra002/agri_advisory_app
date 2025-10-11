#!/usr/bin/env python3
"""
Dynamic Profitable Crop AI System
Advanced AI for location-based profitable crop recommendations
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import random

logger = logging.getLogger(__name__)

class CropAnalysis:
    """Data class for crop analysis results"""
    def __init__(self, crop_name: str, profitability_score: float, season: str, 
                 historical_yield: float, msp_price: int, current_price: float,
                 soil_suitability: float, weather_suitability: float,
                 government_support: float, risk_level: float,
                 investment_required: float, market_demand: float,
                 export_potential: float, confidence: float):
        self.crop_name = crop_name
        self.profitability_score = profitability_score
        self.season = season
        self.historical_yield = historical_yield
        self.msp_price = msp_price
        self.current_price = current_price
        self.soil_suitability = soil_suitability
        self.weather_suitability = weather_suitability
        self.government_support = government_support
        self.risk_level = risk_level
        self.investment_required = investment_required
        self.market_demand = market_demand
        self.export_potential = export_potential
        self.confidence = confidence
        self.timestamp = datetime.now()

class DynamicProfitableCropAI:
    """Dynamic AI system for profitable crop recommendations"""
    
    def __init__(self):
        self.crop_database = self._initialize_crop_database()
        logger.info("Dynamic Profitable Crop AI initialized")
    
    def _initialize_crop_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialize comprehensive crop database"""
        return {
            'wheat': {
                'name': 'Wheat',
                'type': 'Cereal',
                'seasons': ['rabi'],
                'yield_range': (2.5, 4.5),
                'msp': 2090,
                'price_range': (1800, 2200),
                'investment_range': (25000, 35000),
                'soil_preference': 'alluvial',
                'weather_tolerance': 0.8,
                'government_support': 0.9,
                'market_demand': 0.95,
                'export_potential': 0.3
            },
            'rice': {
                'name': 'Rice',
                'type': 'Cereal',
                'seasons': ['kharif'],
                'yield_range': (3.0, 5.0),
                'msp': 2040,
                'price_range': (1800, 2100),
                'investment_range': (30000, 45000),
                'soil_preference': 'alluvial',
                'weather_tolerance': 0.7,
                'government_support': 0.95,
                'market_demand': 0.98,
                'export_potential': 0.4
            },
            'maize': {
                'name': 'Maize',
                'type': 'Cereal',
                'seasons': ['kharif'],
                'yield_range': (2.5, 4.0),
                'msp': 2090,
                'price_range': (1600, 2000),
                'investment_range': (25000, 35000),
                'soil_preference': 'alluvial',
                'weather_tolerance': 0.8,
                'government_support': 0.8,
                'market_demand': 0.85,
                'export_potential': 0.6
            },
            'cotton': {
                'name': 'Cotton',
                'type': 'Cash Crop',
                'seasons': ['kharif'],
                'yield_range': (1.5, 3.0),
                'msp': 6620,
                'price_range': (6000, 7500),
                'investment_range': (40000, 60000),
                'soil_preference': 'black',
                'weather_tolerance': 0.6,
                'government_support': 0.7,
                'market_demand': 0.9,
                'export_potential': 0.8
            },
            'sugarcane': {
                'name': 'Sugarcane',
                'type': 'Cash Crop',
                'seasons': ['year_round'],
                'yield_range': (60, 100),
                'msp': 315,
                'price_range': (280, 350),
                'investment_range': (60000, 80000),
                'soil_preference': 'alluvial',
                'weather_tolerance': 0.7,
                'government_support': 0.85,
                'market_demand': 0.95,
                'export_potential': 0.7
            },
            'potato': {
                'name': 'Potato',
                'type': 'Vegetable',
                'seasons': ['rabi'],
                'yield_range': (15, 25),
                'msp': 750,
                'price_range': (600, 1000),
                'investment_range': (35000, 50000),
                'soil_preference': 'sandy_loam',
                'weather_tolerance': 0.8,
                'government_support': 0.6,
                'market_demand': 0.9,
                'export_potential': 0.4
            }
        }
    
    def get_dynamic_profitable_crops(self, location: str, season: Optional[str] = None, 
                                   real_time_data: Dict[str, Any] = None) -> List[CropAnalysis]:
        """Get dynamic profitable crop recommendations"""
        try:
            if not season:
                season = self._detect_current_season()
            
            # Get location-specific factors
            location_factors = self._analyze_location_factors(location, real_time_data)
            
            # Analyze all crops
            crop_analyses = []
            for crop_key, crop_data in self.crop_database.items():
                if season in crop_data['seasons'] or 'year_round' in crop_data['seasons']:
                    analysis = self._analyze_crop_profitability(
                        crop_key, crop_data, location_factors, season
                    )
                    crop_analyses.append(analysis)
            
            # Sort by profitability score
            crop_analyses.sort(key=lambda x: x.profitability_score, reverse=True)
            
            # Return top 5 recommendations
            return crop_analyses[:5]
            
        except Exception as e:
            logger.error(f"Error in dynamic crop analysis: {e}")
            return self._get_fallback_recommendations(location, season)
    
    def _detect_current_season(self) -> str:
        """Detect current season based on month"""
        month = datetime.now().month
        if month in [6, 7, 8, 9]:
            return 'kharif'
        elif month in [10, 11, 12, 1, 2]:
            return 'rabi'
        else:
            return 'zaid'
    
    def _analyze_location_factors(self, location: str, real_time_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze location-specific factors"""
        # Simulate location analysis
        return {
            'soil_type': 'alluvial',
            'climate_zone': 'sub_tropical',
            'rainfall': random.uniform(800, 1200),
            'temperature': random.uniform(20, 35),
            'humidity': random.uniform(60, 80),
            'market_access': random.uniform(0.7, 0.9),
            'government_support_level': random.uniform(0.8, 0.95),
            'infrastructure': random.uniform(0.6, 0.8)
        }
    
    def _analyze_crop_profitability(self, crop_key: str, crop_data: Dict[str, Any], 
                                  location_factors: Dict[str, Any], season: str) -> CropAnalysis:
        """Analyze profitability of a specific crop"""
        # Calculate profitability score based on multiple factors
        base_score = 50.0
        
        # Yield potential
        yield_score = random.uniform(70, 95)
        
        # Market price vs MSP
        current_price = random.uniform(*crop_data['price_range'])
        price_score = (current_price / crop_data['msp']) * 100
        price_score = min(price_score, 120)  # Cap at 120%
        
        # Investment efficiency
        investment = random.uniform(*crop_data['investment_range'])
        revenue = current_price * random.uniform(*crop_data['yield_range']) * 10  # 10 quintals per ton
        roi_score = ((revenue - investment) / investment) * 100
        roi_score = max(roi_score, 0)  # No negative scores
        
        # Location suitability
        soil_match = 1.0 if location_factors['soil_type'] in crop_data.get('soil_preference', 'alluvial') else 0.7
        weather_score = crop_data['weather_tolerance'] * 100
        
        # Government support
        gov_support_score = crop_data['government_support'] * location_factors['government_support_level'] * 100
        
        # Market demand
        market_score = crop_data['market_demand'] * location_factors['market_access'] * 100
        
        # Export potential
        export_score = crop_data['export_potential'] * 100
        
        # Calculate final profitability score
        profitability_score = (
            yield_score * 0.2 +
            price_score * 0.15 +
            roi_score * 0.2 +
            soil_match * 100 * 0.1 +
            weather_score * 0.1 +
            gov_support_score * 0.1 +
            market_score * 0.1 +
            export_score * 0.05
        )
        
        # Calculate other metrics
        historical_yield = random.uniform(*crop_data['yield_range'])
        soil_suitability = soil_match * 100
        weather_suitability = weather_score
        risk_level = max(0, 100 - profitability_score)  # Higher profitability = lower risk
        confidence = min(0.95, profitability_score / 100)
        
        return CropAnalysis(
            crop_name=crop_key,
            profitability_score=round(profitability_score, 1),
            season=season,
            historical_yield=historical_yield,
            msp_price=crop_data['msp'],
            current_price=round(current_price, 2),
            soil_suitability=round(soil_suitability, 1),
            weather_suitability=round(weather_suitability, 1),
            government_support=round(gov_support_score, 1),
            risk_level=round(risk_level, 1),
            investment_required=investment,
            market_demand=crop_data['market_demand'],
            export_potential=crop_data['export_potential'],
            confidence=round(confidence, 2)
        )
    
    def _get_fallback_recommendations(self, location: str, season: str) -> List[CropAnalysis]:
        """Get fallback recommendations when analysis fails"""
        logger.warning(f"Using fallback recommendations for {location}, {season}")
        
        fallback_crops = ['wheat', 'rice', 'maize']
        analyses = []
        
        for crop in fallback_crops:
            if crop in self.crop_database:
                crop_data = self.crop_database[crop]
                analysis = CropAnalysis(
                    crop_name=crop,
                    profitability_score=75.0,
                    season=season,
                    historical_yield=3.5,
                    msp_price=crop_data['msp'],
                    current_price=random.uniform(*crop_data['price_range']),
                    soil_suitability=80.0,
                    weather_suitability=75.0,
                    government_support=85.0,
                    risk_level=25.0,
                    investment_required=30000,
                    market_demand=0.9,
                    export_potential=0.5,
                    confidence=0.8
                )
                analyses.append(analysis)
        
        return analyses[:3]

# Global instance
dynamic_profitable_crop_ai = DynamicProfitableCropAI()