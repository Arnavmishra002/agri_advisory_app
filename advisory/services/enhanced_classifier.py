#!/usr/bin/env python3
"""
Enhanced Query Classification System
Improves accuracy for general and mixed query recognition
"""

import re
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedQueryClassifier:
    """Enhanced query classification with improved accuracy"""
    
    def __init__(self):
        # Enhanced keyword patterns
        self.farming_patterns = {
            'crops': [
                'crop', 'फसल', 'crops', 'cultivation', 'खेती', 'farming', 'agriculture', 'कृषि',
                'wheat', 'गेहूं', 'rice', 'चावल', 'maize', 'मक्का', 'cotton', 'कपास',
                'sugarcane', 'गन्ना', 'potato', 'आलू', 'tomato', 'टमाटर', 'onion', 'प्याज',
                'vegetable', 'सब्जी', 'fruits', 'फल', 'pulses', 'दाल', 'oilseeds', 'तिलहन',
                'lagayein', 'लगाएं', 'lagana', 'लगाना', 'suggest', 'सुझाव', 'recommend', 'अनुशंसा',
                'kya', 'क्या', 'kaun si', 'कौन सी', 'which', 'best', 'बेस्ट', 'suitable', 'उपयुक्त',
                'mein', 'में', 'in', 'for', 'के लिए', 'grow', 'उगाना', 'plant', 'पौधा'
            ],
            'market': [
                'price', 'कीमत', 'rate', 'दर', 'market', 'बाजार', 'mandi', 'मंडी',
                'selling', 'बेचना', 'buying', 'खरीदना', 'profit', 'लाभ', 'loss', 'नुकसान',
                'msp', 'minimum support price', 'procurement', 'खरीद', 'trading', 'व्यापार'
            ],
            'weather': [
                'weather', 'मौसम', 'rain', 'बारिश', 'rainfall', 'वर्षा', 'temperature', 'तापमान',
                'humidity', 'नमी', 'wind', 'हवा', 'forecast', 'पूर्वानुमान', 'climate', 'जलवायु',
                'drought', 'सूखा', 'flood', 'बाढ़', 'storm', 'तूफान', 'season', 'मौसम'
            ],
            'pest_disease': [
                'pest', 'कीट', 'disease', 'रोग', 'insect', 'कीड़ा', 'fungus', 'फफूंद',
                'control', 'नियंत्रण', 'treatment', 'उपचार', 'medicine', 'दवा', 'spray', 'छिड़काव',
                'infection', 'संक्रमण', 'damage', 'नुकसान', 'healthy', 'स्वस्थ', 'sick', 'बीमार'
            ],
            'fertilizer': [
                'fertilizer', 'उर्वरक', 'manure', 'खाद', 'compost', 'कंपोस्ट', 'nutrient', 'पोषक',
                'npk', 'nitrogen', 'फॉस्फोरस', 'potassium', 'पोटाश', 'organic', 'जैविक',
                'chemical', 'रासायनिक', 'dose', 'मात्रा', 'application', 'प्रयोग'
            ],
            'government': [
                'scheme', 'योजना', 'subsidy', 'सब्सिडी', 'government', 'सरकार', 'pm kisan',
                'pmfby', 'soil health card', 'kisan credit card', 'pmksy', 'loan', 'कर्ज',
                'benefit', 'लाभ', 'support', 'सहायता', 'assistance', 'मदद', 'help', 'सहायता'
            ],
            'irrigation': [
                'irrigation', 'सिंचाई', 'water', 'पानी', 'watering', 'सिंचाई करना', 'drip', 'ड्रिप',
                'sprinkler', 'स्प्रिंकलर', 'pump', 'पंप', 'well', 'कुआं', 'canal', 'नहर',
                'drainage', 'जल निकासी', 'moisture', 'नमी', 'dry', 'सूखा', 'wet', 'गीला'
            ],
            'soil': [
                'soil', 'मिट्टी', 'land', 'जमीन', 'earth', 'भूमि', 'fertile', 'उपजाऊ',
                'sandy', 'रेतली', 'clayey', 'चिकनी', 'loamy', 'दोमट', 'ph', 'पीएच',
                'testing', 'जांच', 'health', 'स्वास्थ्य', 'nutrient', 'पोषक तत्व'
            ]
        }
        
        self.general_patterns = {
            'greeting': [
                'hello', 'hi', 'hey', 'namaste', 'नमस्ते', 'good morning', 'good afternoon',
                'good evening', 'how are you', 'आप कैसे हैं', 'kaise ho', 'kaise hain'
            ],
            'trivia': [
                'trivia', 'quiz', 'question', 'प्रश्न', 'fact', 'तथ्य', 'knowledge', 'ज्ञान',
                'random', 'यादृच्छिक', 'general', 'सामान्य', 'interesting', 'रोचक'
            ],
            'numbers': [
                'number', 'संख्या', 'digit', 'अंक', 'count', 'गिनती', 'math', 'गणित',
                'calculation', 'गणना', 'statistics', 'आंकड़े', 'data', 'डेटा'
            ],
            'wikipedia': [
                'what is', 'क्या है', 'who is', 'कौन है', 'when was', 'कब था', 'where is', 'कहां है',
                'why', 'क्यों', 'how', 'कैसे', 'explain', 'समझाएं', 'tell me about', 'बताएं'
            ],
            'activities': [
                'bored', 'बोर', 'activity', 'गतिविधि', 'fun', 'मजा', 'entertainment', 'मनोरंजन',
                'suggestion', 'सुझाव', 'idea', 'विचार', 'hobby', 'शौक', 'leisure', 'अवकाश'
            ],
            'general_knowledge': [
                'capital', 'राजधानी', 'country', 'देश', 'city', 'शहर', 'history', 'इतिहास',
                'science', 'विज्ञान', 'technology', 'तकनीक', 'culture', 'संस्कृति'
            ]
        }
        
        # Mixed query indicators
        self.mixed_indicators = [
            'and', 'aur', 'भी', 'also', 'bhi', 'plus', 'साथ', 'together', 'साथ में',
            'both', 'दोनों', 'along with', 'के साथ', 'including', 'सहित'
        ]
        
        # Language detection patterns
        self.hindi_patterns = [
            'क्या', 'कैसे', 'कब', 'कहां', 'कौन', 'क्यों', 'में', 'पर', 'से', 'को',
            'है', 'हैं', 'था', 'थे', 'थी', 'होगा', 'होगी', 'होंगे', 'कर', 'करना'
        ]
        
        self.english_patterns = [
            'what', 'how', 'when', 'where', 'who', 'why', 'is', 'are', 'was', 'were',
            'will', 'would', 'can', 'could', 'should', 'may', 'might', 'do', 'does', 'did'
        ]
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """Enhanced query classification with improved accuracy"""
        
        query_lower = query.lower().strip()
        
        # Detect language
        language = self._detect_language(query_lower)
        
        # Check for mixed queries first
        is_mixed = self._is_mixed_query(query_lower)
        
        # Classify query type with enhanced priority for farming queries
        if is_mixed:
            query_type = 'mixed'
            confidence = self._calculate_mixed_confidence(query_lower)
        else:
            farming_score = self._calculate_farming_score(query_lower)
            general_score = self._calculate_general_score(query_lower)
            
            # Check for specific crop recommendation patterns
            crop_recommendation_patterns = ['fasal', 'फसल', 'lagayein', 'लगाएं', 'suggest', 'सुझाव', 'recommend', 'कौन सी', 'kya']
            has_crop_keywords = any(pattern in query_lower for pattern in crop_recommendation_patterns)
            
            # Prioritize farming if crop-related keywords are found
            if has_crop_keywords and farming_score > 0:
                query_type = 'farming'
                confidence = max(farming_score, 0.8)  # Boost confidence for crop queries
            elif farming_score > general_score:
                query_type = 'farming'
                confidence = farming_score
            else:
                query_type = 'general'
                confidence = general_score
        
        # Extract entities
        entities = self._extract_entities(query_lower, query_type)
        
        # Determine subcategory
        subcategory = self._determine_subcategory(query_lower, query_type)
        
        return {
            'query_type': query_type,
            'subcategory': subcategory,
            'language': language,
            'confidence': confidence,
            'entities': entities,
            'is_mixed': is_mixed,
            'classification_details': {
                'farming_score': self._calculate_farming_score(query_lower),
                'general_score': self._calculate_general_score(query_lower),
                'mixed_score': self._calculate_mixed_confidence(query_lower) if is_mixed else 0
            }
        }
    
    def _detect_language(self, query: str) -> str:
        """Enhanced language detection"""
        hindi_count = sum(1 for pattern in self.hindi_patterns if pattern in query)
        english_count = sum(1 for pattern in self.english_patterns if pattern in query)
        
        # Check for Devanagari script
        devanagari_count = len(re.findall(r'[\u0900-\u097F]', query))
        
        if devanagari_count > 0:
            return 'hi'
        elif hindi_count > english_count:
            return 'hinglish'
        else:
            return 'en'
    
    def _is_mixed_query(self, query: str) -> bool:
        """Detect mixed queries (farming + general)"""
        mixed_indicators_found = any(indicator in query for indicator in self.mixed_indicators)
        
        if not mixed_indicators_found:
            return False
        
        # Check if query contains both farming and general elements
        farming_elements = sum(1 for category in self.farming_patterns.values() 
                             for keyword in category if keyword in query)
        general_elements = sum(1 for category in self.general_patterns.values() 
                             for keyword in category if keyword in query)
        
        return farming_elements > 0 and general_elements > 0
    
    def _calculate_farming_score(self, query: str) -> float:
        """Calculate farming relevance score"""
        total_score = 0
        total_weight = 0
        
        for category, keywords in self.farming_patterns.items():
            category_score = sum(1 for keyword in keywords if keyword in query)
            weight = len(keywords)
            
            if category_score > 0:
                total_score += (category_score / weight) * 100
                total_weight += 100
        
        return min(total_score / total_weight, 1.0) if total_weight > 0 else 0.0
    
    def _calculate_general_score(self, query: str) -> float:
        """Calculate general query relevance score"""
        total_score = 0
        total_weight = 0
        
        for category, keywords in self.general_patterns.items():
            category_score = sum(1 for keyword in keywords if keyword in query)
            weight = len(keywords)
            
            if category_score > 0:
                total_score += (category_score / weight) * 100
                total_weight += 100
        
        return min(total_score / total_weight, 1.0) if total_weight > 0 else 0.0
    
    def _calculate_mixed_confidence(self, query: str) -> float:
        """Calculate confidence for mixed queries"""
        farming_score = self._calculate_farming_score(query)
        general_score = self._calculate_general_score(query)
        
        # Mixed queries should have both elements
        if farming_score > 0.3 and general_score > 0.3:
            return (farming_score + general_score) / 2
        else:
            return max(farming_score, general_score)
    
    def _extract_entities(self, query: str, query_type: str) -> Dict[str, Any]:
        """Extract entities from query"""
        entities = {
            'crops': [],
            'locations': [],
            'numbers': [],
            'keywords': []
        }
        
        # Extract crop names
        for crop in self.farming_patterns['crops']:
            if crop in query:
                entities['crops'].append(crop)
        
        # Extract locations (simple pattern matching)
        location_patterns = [
            r'\b(delhi|mumbai|bangalore|chennai|kolkata|hyderabad|pune|ahmedabad|jaipur|lucknow|kanpur|nagpur|indore|thane|bhopal|visakhapatnam|pimpri|patna|vadodara|ghaziabad|ludhiana|agra|nashik|faridabad|meerut|rajkot|kalyan|vasai|varanasi|srinagar|aurangabad|noida|solapur|howrah|coimbatore|raipur|jabalpur|gwalior|madurai|guwahati|chandigarh|tiruchirappalli|mysore|bhubaneswar|kochi|bhavnagar|salem|warangal|guntur|bhiwandi|amravati|nanded|kolhapur|sangli|malegaon|ulhasnagar|jalgaon|akola|latur|ahmadnagar|dhule|ichalkaranji|parbhani|jalna|bhusawal|panvel|satara|beed|yavatmal|kamptee|gondia|bhandara|udaipur|tirupur|mangalore|erode|belgaum|tumkur|davangere|bellary|bijapur|gulbarga|hubli|shimoga|udupi|hassan|mandya|chitradurga|kolar|chikmagalur|hampi|badami|pattadakal|aihole|halebidu|shravanabelagola|srirangapatna|melkote|talakad|somanathapura|belur|chennakeshava|hoysaleswara|ishvara|lakshmi|narayana|virupaksha|hampi|vijayanagara|bidar|raichur|kurnool|anantapur|kadapa|chittoor|nellore|prakasam|guntur|krishna|west godavari|east godavari|visakhapatnam|vizianagaram|srikakulam|adilabad|karimnagar|warangal|khammam|nalgonda|mahbubnagar|rangareddy|medak|nizamabad|hyderabad|secunderabad)\b',
            r'\b(uttar pradesh|maharashtra|karnataka|tamil nadu|west bengal|gujarat|rajasthan|madhya pradesh|andhra pradesh|telangana|bihar|odisha|kerala|assam|punjab|haryana|chhattisgarh|jharkhand|uttarakhand|himachal pradesh|tripura|meghalaya|manipur|nagaland|goa|arunachal pradesh|mizoram|sikkim|delhi|chandigarh|puducherry|andaman|nicobar|lakshadweep|daman|diu|dadra|nagar haveli)\b'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities['locations'].extend(matches)
        
        # Extract numbers
        numbers = re.findall(r'\d+', query)
        entities['numbers'] = numbers
        
        # Extract key keywords
        all_keywords = []
        for category in self.farming_patterns.values():
            all_keywords.extend(category)
        for category in self.general_patterns.values():
            all_keywords.extend(category)
        
        entities['keywords'] = [kw for kw in all_keywords if kw in query]
        
        return entities
    
    def _determine_subcategory(self, query: str, query_type: str) -> str:
        """Determine specific subcategory"""
        if query_type == 'farming':
            for category, keywords in self.farming_patterns.items():
                if any(keyword in query for keyword in keywords):
                    return category
            return 'general_farming'
        
        elif query_type == 'general':
            for category, keywords in self.general_patterns.items():
                if any(keyword in query for keyword in keywords):
                    return category
            return 'general_knowledge'
        
        else:  # mixed
            return 'mixed_query'
    
    def get_classification_explanation(self, classification: Dict[str, Any]) -> str:
        """Get human-readable explanation of classification"""
        query_type = classification['query_type']
        confidence = classification['confidence']
        subcategory = classification['subcategory']
        
        if query_type == 'farming':
            return f"🌾 Farming Query ({subcategory}) - Confidence: {confidence:.2f}"
        elif query_type == 'general':
            return f"🌍 General Query ({subcategory}) - Confidence: {confidence:.2f}"
        else:
            return f"🔄 Mixed Query ({subcategory}) - Confidence: {confidence:.2f}"

# Create global instance
enhanced_classifier = EnhancedQueryClassifier()
