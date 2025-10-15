#!/usr/bin/env python3
"""
Debug Intent Classification
"""

import sys
import os
sys.path.append('agri_advisory_app')

from advisory.services.deep_ai_understanding import DeepAIUnderstanding

def debug_intent_classification():
    """Debug intent classification for simple queries"""
    print("Debugging Intent Classification...")
    print("=" * 50)
    
    deep_ai = DeepAIUnderstanding()
    
    test_queries = [
        "hii",
        "hello",
        "who is avneet kaur"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        query_lower = query.lower()
        
        # Check farming patterns
        farming_patterns = {
            'crop_recommendation': ['फसल लगाएं', 'crop grow', 'what plant', 'suggest crop', 'बीज बोएं'],
            'cultivation_guide': ['खेती कैसे', 'cultivation guide', 'growing guide', 'how to grow', 'बुवाई कैसे'],
            'pest_management': ['कीट नियंत्रण', 'pest control', 'disease treatment', 'रोग का इलाज'],
            'harvesting': ['कटाई', 'harvest', 'harvesting', 'picking', 'collection'],
            'soil_management': ['मिट्टी', 'soil', 'fertility', 'testing', 'improvement'],
            'water_management': ['सिंचाई', 'irrigation', 'watering', 'drainage', 'water'],
            'price_inquiry': ['भाव', 'price', 'rate', 'cost', 'market', 'मंडी'],
            'weather_inquiry': ['मौसम', 'weather', 'forecast', 'temperature', 'rain'],
            'government_schemes': ['सरकारी योजना', 'government scheme', 'pm kisan', 'subsidy'],
            'livestock_care': ['पशु', 'animal', 'livestock', 'dairy', 'poultry', 'cattle']
        }
        
        intent_scores = {}
        for intent, patterns in farming_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            intent_scores[intent] = score
            if score > 0:
                print(f"  {intent}: {score} (matched patterns: {[p for p in patterns if p in query_lower]})")
        
        # Check general patterns
        general_patterns = {
            'factual_inquiry': ['what is', 'what are', 'क्या है', 'क्या हैं'],
            'explanation_request': ['explain', 'describe', 'tell me about', 'बताएं', 'समझाएं'],
            'comparison': ['compare', 'difference', 'versus', 'vs', 'तुलना', 'अंतर'],
            'calculation': ['calculate', 'compute', 'how much', 'total', 'गणना', 'कितना'],
            'guidance': ['how to', 'steps', 'process', 'procedure', 'कैसे', 'तरीका']
        }
        
        for intent, patterns in general_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            intent_scores[intent] = score
            if score > 0:
                print(f"  {intent}: {score} (matched patterns: {[p for p in patterns if p in query_lower]})")
        
        print(f"  Intent scores: {intent_scores}")
        
        # Determine primary intent
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            print(f"  Primary intent: {primary_intent}")
        else:
            print(f"  Primary intent: general_inquiry (default)")
        
        print("-" * 30)

if __name__ == "__main__":
    debug_intent_classification()

"""
Debug Intent Classification
"""

import sys
import os
sys.path.append('agri_advisory_app')

from advisory.services.deep_ai_understanding import DeepAIUnderstanding

def debug_intent_classification():
    """Debug intent classification for simple queries"""
    print("Debugging Intent Classification...")
    print("=" * 50)
    
    deep_ai = DeepAIUnderstanding()
    
    test_queries = [
        "hii",
        "hello",
        "who is avneet kaur"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        query_lower = query.lower()
        
        # Check farming patterns
        farming_patterns = {
            'crop_recommendation': ['फसल लगाएं', 'crop grow', 'what plant', 'suggest crop', 'बीज बोएं'],
            'cultivation_guide': ['खेती कैसे', 'cultivation guide', 'growing guide', 'how to grow', 'बुवाई कैसे'],
            'pest_management': ['कीट नियंत्रण', 'pest control', 'disease treatment', 'रोग का इलाज'],
            'harvesting': ['कटाई', 'harvest', 'harvesting', 'picking', 'collection'],
            'soil_management': ['मिट्टी', 'soil', 'fertility', 'testing', 'improvement'],
            'water_management': ['सिंचाई', 'irrigation', 'watering', 'drainage', 'water'],
            'price_inquiry': ['भाव', 'price', 'rate', 'cost', 'market', 'मंडी'],
            'weather_inquiry': ['मौसम', 'weather', 'forecast', 'temperature', 'rain'],
            'government_schemes': ['सरकारी योजना', 'government scheme', 'pm kisan', 'subsidy'],
            'livestock_care': ['पशु', 'animal', 'livestock', 'dairy', 'poultry', 'cattle']
        }
        
        intent_scores = {}
        for intent, patterns in farming_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            intent_scores[intent] = score
            if score > 0:
                print(f"  {intent}: {score} (matched patterns: {[p for p in patterns if p in query_lower]})")
        
        # Check general patterns
        general_patterns = {
            'factual_inquiry': ['what is', 'what are', 'क्या है', 'क्या हैं'],
            'explanation_request': ['explain', 'describe', 'tell me about', 'बताएं', 'समझाएं'],
            'comparison': ['compare', 'difference', 'versus', 'vs', 'तुलना', 'अंतर'],
            'calculation': ['calculate', 'compute', 'how much', 'total', 'गणना', 'कितना'],
            'guidance': ['how to', 'steps', 'process', 'procedure', 'कैसे', 'तरीका']
        }
        
        for intent, patterns in general_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            intent_scores[intent] = score
            if score > 0:
                print(f"  {intent}: {score} (matched patterns: {[p for p in patterns if p in query_lower]})")
        
        print(f"  Intent scores: {intent_scores}")
        
        # Determine primary intent
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            print(f"  Primary intent: {primary_intent}")
        else:
            print(f"  Primary intent: general_inquiry (default)")
        
        print("-" * 30)

if __name__ == "__main__":
    debug_intent_classification()
